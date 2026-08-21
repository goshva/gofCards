from __future__ import annotations

import secrets
from datetime import timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import QUESTS
from app.core.exceptions import AlreadyExists, NotAllowed, NotFound
from app.models import QuestProgress, Referral, User
from app.models.base import utcnow

CATALOGUE: dict[str, dict[str, Any]] = {q["key"]: q for q in QUESTS["items"]}
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no look-alike characters


def aware(value):
    """sqlite hands timestamps back naive; pin them to UTC before comparing."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class QuestService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- referral code ----------

    async def ensure_code(self, user: User) -> str:
        if user.referral_code:
            return user.referral_code
        for _ in range(12):
            code = "".join(secrets.choice(ALPHABET) for _ in range(6))
            taken = await self.db.scalar(select(User).where(User.referral_code == code))
            if taken is None:
                user.referral_code = code
                await self.db.commit()
                return code
        raise AlreadyExists("Не удалось выдать реферальный код")

    async def register_referral(self, invitee: User, code: str) -> Referral | None:
        """Called right after a new account is created.

        Both sides are paid at once: the reward is the whole point of the quest,
        and delaying it would make the invite feel broken.
        """
        code = (code or "").strip().upper()
        if not code:
            return None

        inviter = await self.db.scalar(select(User).where(User.referral_code == code))
        if inviter is None or inviter.id == invitee.id:
            return None

        already = await self.db.scalar(select(Referral).where(Referral.invitee_id == invitee.id))
        if already is not None:
            return None

        inviter_reward = int(QUESTS["referralReward"])
        invitee_reward = int(QUESTS["referralFriendBonus"])
        inviter.coins += inviter_reward
        invitee.coins += invitee_reward

        progress = await self._progress(inviter, "INVITE_FRIEND")
        progress.times_claimed += 1
        progress.coins_earned += inviter_reward
        progress.last_claimed_at = utcnow()

        referral = Referral(
            inviter_id=inviter.id,
            invitee_id=invitee.id,
            code=code,
            inviter_reward=inviter_reward,
            invitee_reward=invitee_reward,
        )
        self.db.add(referral)
        await self.db.commit()
        await self.db.refresh(referral)
        return referral

    # ---------- quest progress ----------

    async def _progress(self, user: User, key: str) -> QuestProgress:
        row = await self.db.scalar(
            select(QuestProgress).where(
                QuestProgress.user_id == user.id, QuestProgress.quest_key == key
            )
        )
        if row is None:
            row = QuestProgress(user_id=user.id, quest_key=key)
            self.db.add(row)
            await self.db.flush()
        return row

    @staticmethod
    def _cooldown_left(quest: dict[str, Any], progress: QuestProgress) -> int:
        hours = int(quest.get("cooldownHours") or 0)
        last = aware(progress.last_claimed_at)
        if not hours or last is None:
            return 0
        ready = last + timedelta(hours=hours)
        return max(0, int((ready - utcnow()).total_seconds()))

    def _state(self, quest: dict[str, Any], progress: QuestProgress | None) -> dict[str, Any]:
        claimed = progress.times_claimed if progress else 0
        cooldown = self._cooldown_left(quest, progress) if progress else 0
        repeatable = bool(quest.get("repeatable"))

        if quest.get("referral"):
            status = "referral"
        elif not repeatable and claimed:
            status = "done"
        elif cooldown:
            status = "cooldown"
        elif quest.get("url") and (progress is None or progress.started_at is None):
            status = "action_required"
        else:
            status = "available"

        return {
            **quest,
            "status": status,
            "times_claimed": claimed,
            "coins_earned": progress.coins_earned if progress else 0,
            "cooldown_seconds": cooldown,
            "started": bool(progress and progress.started_at),
        }

    async def list_quests(self, user: User) -> dict[str, Any]:
        rows = {
            r.quest_key: r
            for r in await self.db.scalars(
                select(QuestProgress).where(QuestProgress.user_id == user.id)
            )
        }
        invited = await self.db.scalar(
            select(func.count()).select_from(Referral).where(Referral.inviter_id == user.id)
        )
        return {
            "quests": [self._state(q, rows.get(q["key"])) for q in QUESTS["items"]],
            "referral_code": await self.ensure_code(user),
            "referral_reward": int(QUESTS["referralReward"]),
            "referral_friend_bonus": int(QUESTS["referralFriendBonus"]),
            "friends_invited": invited or 0,
            "total_earned": sum(r.coins_earned for r in rows.values()),
        }

    async def start(self, user: User, key: str) -> dict[str, Any]:
        """Marks that the user followed the link, which unlocks the claim."""
        quest = CATALOGUE.get(key)
        if quest is None:
            raise NotFound("Квест не найден")
        progress = await self._progress(user, key)
        progress.started_at = utcnow()
        await self.db.commit()
        return self._state(quest, progress)

    async def claim(self, user: User, key: str) -> dict[str, Any]:
        quest = CATALOGUE.get(key)
        if quest is None:
            raise NotFound("Квест не найден")
        if quest.get("referral"):
            raise NotAllowed("Награда за друга начисляется автоматически при его регистрации")

        progress = await self._progress(user, key)
        state = self._state(quest, progress)

        if state["status"] == "done":
            raise AlreadyExists("Квест уже выполнен")
        if state["status"] == "cooldown":
            minutes = state["cooldown_seconds"] // 60 + 1
            raise AlreadyExists(f"Следующая награда через {minutes} мин")
        if state["status"] == "action_required":
            raise NotAllowed("Сначала откройте ссылку из квеста")

        reward = int(quest["reward"])
        user.coins += reward
        progress.times_claimed += 1
        progress.coins_earned += reward
        progress.last_claimed_at = utcnow()
        progress.started_at = None
        await self.db.commit()

        return {
            "quest": self._state(quest, progress),
            "reward": reward,
            "coins": user.coins,
        }
