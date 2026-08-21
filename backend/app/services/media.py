from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import DATA_DIR, settings
from app.models import Player, Team
from app.services.crests import crest_color, crest_svg

logger = logging.getLogger(__name__)

# photos and badges are downloaded once and must survive a redeploy, so they
# sit on the persistent volume next to the database
MEDIA_ROOT = DATA_DIR / "media"
PLAYER_DIR = MEDIA_ROOT / "players"
TEAM_DIR = MEDIA_ROOT / "teams"

EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}
MAX_BYTES = 4 * 1024 * 1024


class MediaService:
    """Mirrors athlete photos and club logos locally.

    Images are not referenced by any JSON field — `image_url` is a stale
    presigned S3 link that expired long ago, and teams carry no field at all.
    They are served by their own path endpoints instead, which the results site
    itself uses:

        GET /api/v1.0/athlete/{uuid}/image/   ->  image/webp
        GET /api/v1.0/team/{uuid}/image/      ->  image/png

    Note the singular noun and the uuid: the detail endpoints of the same
    entities take a slug. Those paths are tried first; the bare S3 object and
    the signed link remain as fallbacks.
    """

    def __init__(self, db: AsyncSession, concurrency: int = 6) -> None:
        self.db = db
        self.semaphore = asyncio.Semaphore(concurrency)

    @staticmethod
    def candidate_urls(url: str) -> list[str]:
        parts = urlsplit(url)
        bare = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        return [bare, url] if bare != url else [url]

    @staticmethod
    def api_image_url(kind: str, external_id: str) -> str:
        """`kind` is the singular noun the image route expects: athlete or team."""
        base = settings.gofuture_base_url.rstrip("/")
        return f"{base}/{kind}/{external_id}/image/"

    @staticmethod
    async def _fetch_one(client: httpx.AsyncClient, url: str) -> httpx.Response | None:
        try:
            resp = await client.get(url, follow_redirects=True)
        except httpx.HTTPError as exc:
            logger.debug("image fetch failed for %s: %s", url, exc)
            return None
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
            return resp
        return None

    async def _download(self, client: httpx.AsyncClient, player: Player) -> str | None:
        sources = [self.api_image_url("athlete", player.external_id)]
        if player.image_url:
            sources.extend(self.candidate_urls(player.image_url))

        async with self.semaphore:
            resp = None
            for source in sources:
                resp = await self._fetch_one(client, source)
                if resp is not None:
                    break
        if resp is None:
            logger.warning("no reachable photo for %s", player.slug)
            return None

        if len(resp.content) > MAX_BYTES:
            logger.warning("photo for %s too large: %d bytes", player.slug, len(resp.content))
            return None

        suffix = EXTENSIONS.get(resp.headers.get("content-type", "").split(";")[0].strip(), ".jpg")
        # content hash in the name means a replaced photo lands on a new URL and
        # never gets served from a stale browser cache
        digest = hashlib.sha1(resp.content).hexdigest()[:12]
        name = f"{player.slug}-{digest}{suffix}"

        PLAYER_DIR.mkdir(parents=True, exist_ok=True)
        target = PLAYER_DIR / name
        if not target.exists():
            target.write_bytes(resp.content)
            for old in PLAYER_DIR.glob(f"{player.slug}-*"):
                if old.name != name:
                    old.unlink(missing_ok=True)
        return f"players/{name}"

    async def sync_player_photos(self, force: bool = False) -> dict:
        players = list(await self.db.scalars(select(Player)))
        pending = [
            p
            for p in players
            if p.image_url and (force or not p.photo_path or not (MEDIA_ROOT / p.photo_path).exists())
        ]
        if not pending:
            return {"downloaded": 0, "skipped": len(players), "total": len(players)}

        async with httpx.AsyncClient(timeout=45.0) as client:
            results = await asyncio.gather(
                *(self._download(client, p) for p in pending), return_exceptions=True
            )

        downloaded = 0
        for player, result in zip(pending, results):
            if isinstance(result, str):
                player.photo_path = result
                downloaded += 1

        await self.db.commit()
        return {
            "downloaded": downloaded,
            "failed": len(pending) - downloaded,
            "skipped": len(players) - len(pending),
            "total": len(players),
        }

    async def _download_team_logo(self, client: httpx.AsyncClient, team: Team) -> str | None:
        async with self.semaphore:
            resp = await self._fetch_one(client, self.api_image_url("team", team.external_id))
        if resp is None or len(resp.content) > MAX_BYTES:
            return None

        suffix = EXTENSIONS.get(resp.headers.get("content-type", "").split(";")[0].strip(), ".png")
        digest = hashlib.sha1(resp.content).hexdigest()[:12]
        name = f"{team.slug}-{digest}{suffix}"

        TEAM_DIR.mkdir(parents=True, exist_ok=True)
        target = TEAM_DIR / name
        if not target.exists():
            target.write_bytes(resp.content)
            for old_file in TEAM_DIR.glob(f"{team.slug}-*"):
                if old_file.name != name:
                    old_file.unlink(missing_ok=True)
        return f"teams/{name}"

    async def sync_team_crests(self, force: bool = False) -> dict:
        """Fetch the real club badge, and draw a crest only if there is none.

        The badge lives behind /team/{uuid}/image/ rather than in any JSON
        field, which is why it looked absent at first.
        """
        teams = list(await self.db.scalars(select(Team)))
        TEAM_DIR.mkdir(parents=True, exist_ok=True)

        real = 0
        generated = 0
        async with httpx.AsyncClient(timeout=45.0) as client:
            results = await asyncio.gather(
                *(self._download_team_logo(client, t) for t in teams), return_exceptions=True
            )

        for team, result in zip(teams, results):
            if isinstance(result, str):
                team.photo_path = result
                real += 1
            else:
                # keep the club identifiable even if the badge is unreachable
                name = f"{team.slug}-crest.svg"
                (TEAM_DIR / name).write_text(
                    crest_svg(team.title, team.external_id), encoding="utf-8"
                )
                team.photo_path = f"teams/{name}"
                generated += 1
            team.color = crest_color(team.external_id)

        await self.db.commit()
        return {"teams": len(teams), "real_logos": real, "generated_crests": generated}
