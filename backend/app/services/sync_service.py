from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import Match, MatchStatus, Player, Position, SyncState, Team
from app.models.base import utcnow

logger = logging.getLogger(__name__)

# GoFuture status values seen on the public endpoint
STATUS_MAP = {
    "completed": MatchStatus.COMPLETED,
    "finished": MatchStatus.COMPLETED,
    "live": MatchStatus.LIVE,
    "in_progress": MatchStatus.LIVE,
    "started": MatchStatus.LIVE,
    "scheduled": MatchStatus.SCHEDULED,
    "upcoming": MatchStatus.SCHEDULED,
    "not_started": MatchStatus.SCHEDULED,
    "cancelled": MatchStatus.CANCELLED,
    "canceled": MatchStatus.CANCELLED,
}


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def parse_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def map_position(raw: str | None) -> Position:
    """The athlete endpoint only ever returns Goalkeeper or Field player."""
    if raw and "goal" in raw.lower():
        return Position.GOALKEEPER
    return Position.FIELD


class GoFutureSyncService:
    def __init__(self, db: AsyncSession, client: httpx.AsyncClient | None = None) -> None:
        self.db = db
        self.base_url = settings.gofuture_base_url.rstrip("/")
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "GoFutureSyncService":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Sync service used outside its async context")
        return self._client

    async def _get(self, path: str, params: dict | None = None) -> Any:
        resp = await self.client.get(f"{self.base_url}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    async def fetch_matches(self) -> list[dict]:
        data = await self._get(
            f"/events/{settings.gofuture_event_slug}/matches/",
            params={"tournament_slug": settings.gofuture_tournament_slug, "limit": 1000},
        )
        if isinstance(data, dict):
            return data.get("items") or []
        return data or []

    async def fetch_athlete(self, slug: str) -> dict | None:
        try:
            return await self._get(f"/athletes/{slug}/")
        except httpx.HTTPError as exc:
            logger.warning("athlete %s failed: %s", slug, exc)
            return None

    async def _upsert_team(self, payload: dict) -> Team | None:
        external_id = payload.get("id")
        slug = payload.get("slug")
        if not external_id or not slug:
            return None
        team = await self.db.scalar(select(Team).where(Team.external_id == external_id))
        if team is None:
            team = Team(external_id=external_id, slug=slug)
            self.db.add(team)
        team.slug = slug
        team.title = payload.get("title") or slug
        team.short_title = payload.get("short_title")
        team.country = payload.get("country")
        team.city = payload.get("city")
        if payload.get("image_url"):
            team.image_url = payload["image_url"]
        await self.db.flush()
        return team

    async def _upsert_player(self, payload: dict, team: Team | None, detail: dict | None) -> Player | None:
        external_id = payload.get("id")
        slug = payload.get("slug")
        if not external_id or not slug:
            return None
        player = await self.db.scalar(select(Player).where(Player.external_id == external_id))
        if player is None:
            player = Player(external_id=external_id, slug=slug)
            self.db.add(player)
        player.slug = slug
        player.nickname = payload.get("nickname") or payload.get("first_name") or slug
        player.first_name = payload.get("first_name")
        player.last_name = payload.get("last_name")
        player.country = payload.get("country")
        if payload.get("image_url"):
            player.image_url = payload["image_url"]
        if team is not None:
            player.team_id = team.id

        if detail:
            player.position = map_position(detail.get("position"))
            info = detail.get("info") or {}
            player.jersey_number = parse_int(info.get("number"))
            dob = info.get("date_of_birth")
            if dob:
                try:
                    player.date_of_birth = datetime.fromisoformat(dob).date()
                except ValueError:
                    pass
            if detail.get("image_url"):
                player.image_url = detail["image_url"]
        await self.db.flush()
        return player

    async def _upsert_match(self, payload: dict, teams: dict[str, Team]) -> Match | None:
        external_id = payload.get("id")
        slug = payload.get("slug")
        if not external_id or not slug:
            return None
        match = await self.db.scalar(select(Match).where(Match.external_id == external_id))
        if match is None:
            match = Match(external_id=external_id, slug=slug)
            self.db.add(match)

        match.slug = slug
        match.tournament_slug = settings.gofuture_tournament_slug
        match.round = parse_int(payload.get("number_auto")) or parse_int(payload.get("number"))
        match.round_label = payload.get("rounds") or payload.get("round_repr")
        match.venue = payload.get("venue")
        match.start_time = parse_dt(payload.get("start_time"))

        previous_status = match.status
        match.status = STATUS_MAP.get((payload.get("status") or "").lower(), MatchStatus.SCHEDULED)
        if previous_status == MatchStatus.COMPLETED and match.status != MatchStatus.COMPLETED:
            match.points_calculated = False

        home = teams.get(payload.get("team1_id") or "")
        away = teams.get(payload.get("team2_id") or "")
        if home:
            match.home_team_id = home.id
        if away:
            match.away_team_id = away.id

        results = payload.get("results") or {}

        def leg(name: str, side: str) -> int:
            return parse_int((results.get(name) or {}).get(side)) or 0

        match.home_score = leg("total", "team1")
        match.away_score = leg("total", "team2")
        match.home_digital = leg("digital", "team1")
        match.away_digital = leg("digital", "team2")
        match.home_physical = leg("physical", "team1")
        match.away_physical = leg("physical", "team2")
        match.home_shootouts = leg("shootouts", "team1")
        match.away_shootouts = leg("shootouts", "team2")

        winner_external = payload.get("w_id")
        winner = teams.get(winner_external or "")
        match.winner_team_id = winner.id if winner else None
        match.stats_json = payload.get("statistic")

        # The API ships these keys but leaves them empty for this tournament.
        # Only overwrite when it actually delivers something, so admin-entered
        # lineups are never wiped by a sync.
        api_home = payload.get("starting_lineup_team1") or []
        api_away = payload.get("starting_lineup_team2") or []
        if api_home or api_away:
            match.home_lineup_json = [a.get("id") for a in api_home if isinstance(a, dict) and a.get("id")]
            match.away_lineup_json = [a.get("id") for a in api_away if isinstance(a, dict) and a.get("id")]
            match.lineups_source = "api"

        await self.db.flush()
        return match

    async def sync_all(self, fetch_athlete_details: bool = True) -> dict:
        """One pass over the tournament.

        Teams and athletes ride along inside the matches payload, so a single
        call covers all three entities; athlete detail is fetched per slug only
        because position and jersey number live there.
        """
        payloads = await self.fetch_matches()

        raw_teams: dict[str, dict] = {}
        for item in payloads:
            for key in ("team1", "team2", "team3", "team4"):
                team = item.get(key)
                if isinstance(team, dict) and team.get("id"):
                    raw_teams[team["id"]] = team

        teams: dict[str, Team] = {}
        players_seen = 0
        for external_id, payload in raw_teams.items():
            team = await self._upsert_team(payload)
            if team is None:
                continue
            teams[external_id] = team
            for athlete in payload.get("athletes") or []:
                detail = None
                if fetch_athlete_details and athlete.get("slug"):
                    existing = await self.db.scalar(
                        select(Player).where(Player.external_id == athlete.get("id"))
                    )
                    # position never changes, so detail is fetched once per athlete
                    if existing is None or existing.jersey_number is None:
                        detail = await self.fetch_athlete(athlete["slug"])
                if await self._upsert_player(athlete, team, detail) is not None:
                    players_seen += 1

        matches_seen = 0
        for item in payloads:
            if await self._upsert_match(item, teams) is not None:
                matches_seen += 1

        await self.db.commit()
        return {"teams": len(teams), "players": players_seen, "matches": matches_seen}

    async def record_state(self, result: dict, error: str | None = None, templates: int = 0) -> SyncState:
        state = await self.db.scalar(select(SyncState).limit(1))
        if state is None:
            state = SyncState()
            self.db.add(state)
        state.last_run_at = utcnow()
        state.last_status = "error" if error else "ok"
        state.last_error = error
        state.teams_synced = result.get("teams", 0)
        state.players_synced = result.get("players", 0)
        state.matches_synced = result.get("matches", 0)
        state.templates_created = templates
        await self.db.commit()
        return state


async def run_sync_once(fetch_athlete_details: bool = True) -> dict:
    """Full pipeline: pull data, mint any missing card templates, settle points."""
    from app.services.card_service import CardService
    from app.services.media import MediaService
    from app.services.ratings import RatingService
    from app.services.scoring import ScoringService

    async with SessionLocal() as db:
        async with GoFutureSyncService(db) as sync:
            try:
                result = await sync.sync_all(fetch_athlete_details=fetch_athlete_details)
            except Exception as exc:
                logger.exception("GoFuture sync failed")
                await sync.record_state({}, error=str(exc)[:1000])
                return {"status": "error", "error": str(exc)}

            # ratings first: template rarity depends on the ranking
            ratings = await RatingService(db).recompute()
            media = MediaService(db)
            photos = await media.sync_player_photos()
            crests = await media.sync_team_crests()

            cards = CardService(db)
            created = await cards.ensure_templates()
            await cards.refresh_template_images()
            settled = await ScoringService(db).settle_pending()
            await sync.record_state(result, templates=created)
            return {
                "status": "ok",
                **result,
                "ratings": ratings,
                "photos": photos,
                "crests": crests,
                "templates_created": created,
                "scoring": settled,
            }


async def sync_loop(interval_seconds: int) -> None:
    while True:
        try:
            await run_sync_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("sync loop iteration failed")
        await asyncio.sleep(interval_seconds)
