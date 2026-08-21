from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SQUAD_RULES
from app.core.exceptions import InvalidSquad, NotFound, NotOwner, SquadLocked
from app.models import (
    CardType,
    Match,
    MatchStatus,
    Player,
    Position,
    PositionSlot,
    SquadEntry,
    User,
    UserCard,
)
from app.schemas.card import PlayerBrief
from app.schemas.squad import (
    PerfectFiveComparison,
    SquadEntryOut,
    SquadOut,
    ValidationIssue,
    ValidationResult,
)
from app.services import catalog

STARTING_SLOTS = [PositionSlot(s) for s in SQUAD_RULES["startingSlots"]]
BENCH_SLOTS = [PositionSlot(s) for s in SQUAD_RULES["benchSlots"]]


class SquadService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_entries(self, user_id: str, match_id: int | None = None) -> list[SquadEntry]:
        rows = await self.db.scalars(
            select(SquadEntry).where(
                SquadEntry.user_id == user_id,
                SquadEntry.match_id.is_(None) if match_id is None else SquadEntry.match_id == match_id,
            )
        )
        entries = list(rows)
        order = {slot: i for i, slot in enumerate(STARTING_SLOTS + BENCH_SLOTS)}
        entries.sort(key=lambda e: order.get(e.position_slot, 99))
        return entries

    async def _assert_match_open(self, match_id: int | None) -> Match | None:
        if match_id is None:
            return None
        match = await self.db.get(Match, match_id)
        if match is None:
            raise NotFound("Матч не найден")
        if match.status != MatchStatus.SCHEDULED:
            raise SquadLocked("Матч уже начался или завершён")
        if match.start_time and match.start_time.astimezone(timezone.utc) <= datetime.now(timezone.utc):
            raise SquadLocked("Дедлайн на изменение состава прошёл")
        return match

    async def select_player(
        self, user: User, user_card_id: str, slot: PositionSlot, match_id: int | None = None
    ) -> SquadEntry:
        await self._assert_match_open(match_id)

        card = await self.db.get(UserCard, user_card_id)
        if card is None:
            raise NotFound("Карточка не найдена")
        if card.user_id != user.id:
            raise NotOwner()
        if card.card_type != CardType.PLAYER:
            raise InvalidSquad("Карточки команд нельзя ставить в состав")

        template = (await catalog.load_templates(self.db, [(card.card_type, card.card_template_id)])).get(
            (card.card_type, card.card_template_id)
        )
        if template is None or template.player is None:
            raise NotFound("Шаблон карточки не найден")
        player_id = template.player.id
        position = template.player.position

        if slot == PositionSlot.GK and position != Position.GOALKEEPER:
            raise InvalidSquad("В слот GK можно поставить только вратаря")
        if slot in (PositionSlot.F1, PositionSlot.F2, PositionSlot.F3, PositionSlot.F4) and position != Position.FIELD:
            raise InvalidSquad("В полевые слоты можно ставить только полевых игроков")

        existing = await self.get_entries(user.id, match_id)
        for entry in existing:
            if entry.player_id == player_id and entry.position_slot != slot:
                raise InvalidSquad("Этот игрок уже есть в составе")

        was_captain = False
        was_vice = False
        for entry in existing:
            if entry.position_slot == slot:
                was_captain, was_vice = entry.is_captain, entry.is_vice_captain
                await self.db.delete(entry)
        await self.db.flush()

        created = SquadEntry(
            user_id=user.id,
            match_id=match_id,
            player_id=player_id,
            user_card_id=card.id,
            position_slot=slot,
            is_captain=was_captain,
            is_vice_captain=was_vice,
        )
        self.db.add(created)
        await self.db.commit()
        await self.db.refresh(created)
        return created

    async def remove_slot(self, user: User, slot: PositionSlot, match_id: int | None = None) -> None:
        await self._assert_match_open(match_id)
        for entry in await self.get_entries(user.id, match_id):
            if entry.position_slot == slot:
                await self.db.delete(entry)
        await self.db.commit()

    async def set_captain(
        self, user: User, entry_id: str, vice: bool = False, match_id: int | None = None
    ) -> list[SquadEntry]:
        await self._assert_match_open(match_id)
        entries = await self.get_entries(user.id, match_id)
        target = next((e for e in entries if e.id == entry_id), None)
        if target is None:
            raise NotFound("Игрок не найден в составе")
        if not target.is_starter:
            raise InvalidSquad("Капитаном может быть только игрок стартовой пятёрки")

        for entry in entries:
            if vice:
                entry.is_vice_captain = entry.id == entry_id
                if entry.id == entry_id:
                    entry.is_captain = False
            else:
                entry.is_captain = entry.id == entry_id
                if entry.id == entry_id:
                    entry.is_vice_captain = False
        await self.db.commit()
        return await self.get_entries(user.id, match_id)

    async def validate(self, user: User, match_id: int | None = None) -> ValidationResult:
        entries = await self.get_entries(user.id, match_id)
        issues: list[ValidationIssue] = []
        starters = [e for e in entries if e.is_starter]

        filled = {e.position_slot for e in starters}
        for slot in STARTING_SLOTS:
            if slot not in filled:
                issues.append(ValidationIssue(code="empty_slot", message=f"Слот {slot.value} не заполнен"))

        owned = {
            c.id
            for c in await self.db.scalars(
                select(UserCard).where(
                    UserCard.user_id == user.id,
                    UserCard.id.in_([e.user_card_id for e in entries] or [""]),
                )
            )
        }
        for entry in entries:
            if entry.user_card_id not in owned:
                name = entry.player.nickname if entry.player else entry.player_id
                issues.append(
                    ValidationIssue(code="not_owned", message=f"Нет карточки для {name}")
                )

        gk_count = sum(
            1 for e in starters if e.player and e.player.position == Position.GOALKEEPER
        )
        if gk_count != SQUAD_RULES["requiredGoalkeepers"]:
            issues.append(
                ValidationIssue(code="goalkeepers", message=f"Вратарей в стартовой пятёрке: {gk_count}, нужен 1")
            )

        if SQUAD_RULES["captainRequired"] and not any(e.is_captain for e in starters):
            issues.append(ValidationIssue(code="no_captain", message="Не назначен капитан"))

        if len(entries) - len(starters) > SQUAD_RULES["maxBench"]:
            issues.append(ValidationIssue(code="bench", message="Слишком много запасных"))

        perfect = PerfectFiveComparison(match_id=match_id or 0, available=False, message="")
        if match_id is not None and not issues:
            perfect = await self.compare_perfect_five(user, match_id)

        if issues:
            return ValidationResult(valid=False, message=issues[0].message, issues=issues)

        message = "Состав валиден"
        if perfect.is_perfect:
            message = "Состав валиден и совпадает с реальной пятёркой команды"
        return ValidationResult(
            valid=True,
            message=message,
            issues=[],
            is_perfect_five=perfect.is_perfect,
            perfect_five_team=perfect.matched_team,
        )

    async def compare_perfect_five(self, user: User, match_id: int) -> PerfectFiveComparison:
        """Perfect Five: the five starters exactly equal one team real starting five.

        GoFuture returns empty lineups for phygital-football-2026, so this only
        resolves once an admin fills them in.
        """
        match = await self.db.get(Match, match_id)
        if match is None:
            raise NotFound("Матч не найден")

        entries = await self.get_entries(user.id, match_id)
        if not entries:
            entries = await self.get_entries(user.id, None)
        user_ids = [e.player_id for e in entries if e.is_starter]

        if not match.home_lineup_json and not match.away_lineup_json:
            return PerfectFiveComparison(
                match_id=match_id,
                available=False,
                message="Реальные составы на этот матч пока не заведены",
                user_player_ids=user_ids,
            )

        home_ids = await self._lineup_to_player_ids(match.home_lineup_json or [])
        away_ids = await self._lineup_to_player_ids(match.away_lineup_json or [])

        user_set = set(user_ids)
        is_home = bool(home_ids) and user_set == set(home_ids)
        is_away = bool(away_ids) and user_set == set(away_ids)
        matched = None
        if is_home and match.home_team:
            matched = match.home_team.title
        elif is_away and match.away_team:
            matched = match.away_team.title

        return PerfectFiveComparison(
            match_id=match_id,
            available=True,
            message="Полное совпадение" if (is_home or is_away) else "Совпадение неполное",
            is_perfect=is_home or is_away,
            matched_team=matched,
            home_matches=sorted(user_set & set(home_ids)),
            away_matches=sorted(user_set & set(away_ids)),
            user_player_ids=user_ids,
        )

    async def _lineup_to_player_ids(self, lineup: list) -> list[int]:
        """Lineups are stored as GoFuture athlete external ids; ints are accepted
        too so an admin can post local player ids."""
        if not lineup:
            return []
        externals = [x for x in lineup if isinstance(x, str)]
        ids = [int(x) for x in lineup if isinstance(x, int)]
        if externals:
            rows = await self.db.scalars(
                select(Player.id).where(Player.external_id.in_(externals))
            )
            ids.extend(rows)
        return ids

    async def lock_for_match(self, user: User, match_id: int) -> list[SquadEntry]:
        """Snapshot the draft squad against a match so later collection changes do
        not rewrite what was fielded."""
        match = await self._assert_match_open(match_id)
        assert match is not None
        draft = await self.get_entries(user.id, None)
        if not draft:
            raise InvalidSquad("Черновой состав пуст")

        for entry in await self.get_entries(user.id, match_id):
            await self.db.delete(entry)
        await self.db.flush()

        snapshot: list[SquadEntry] = []
        for entry in draft:
            copy = SquadEntry(
                user_id=user.id,
                match_id=match_id,
                player_id=entry.player_id,
                user_card_id=entry.user_card_id,
                position_slot=entry.position_slot,
                is_captain=entry.is_captain,
                is_vice_captain=entry.is_vice_captain,
            )
            self.db.add(copy)
            snapshot.append(copy)
        await self.db.commit()
        return await self.get_entries(user.id, match_id)

    async def serialize(self, user: User, match_id: int | None = None) -> SquadOut:
        entries = await self.get_entries(user.id, match_id)
        cards = {
            c.id: c
            for c in await self.db.scalars(
                select(UserCard).where(UserCard.id.in_([e.user_card_id for e in entries] or [""]))
            )
        }
        serialized = {
            out.id: out
            for out in await catalog.serialize_cards(self.db, list(cards.values()))
        }
        locked = False
        if match_id is not None:
            match = await self.db.get(Match, match_id)
            locked = match is not None and match.status != MatchStatus.SCHEDULED

        out_entries: list[SquadEntryOut] = []
        for entry in entries:
            card_out = serialized.get(entry.user_card_id)
            if card_out is None or entry.player is None:
                continue
            out_entries.append(
                SquadEntryOut(
                    id=entry.id,
                    position_slot=entry.position_slot,
                    is_captain=entry.is_captain,
                    is_vice_captain=entry.is_vice_captain,
                    player=PlayerBrief.model_validate(entry.player),
                    card=card_out,
                )
            )
        return SquadOut(
            match_id=match_id,
            locked=locked,
            entries=out_entries,
            filled_slots=sum(1 for e in entries if e.is_starter),
            required_slots=SQUAD_RULES["starters"],
        )
