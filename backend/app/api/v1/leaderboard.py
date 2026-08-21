from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models import Match, PointsHistory, User, UserCard
from app.schemas.leaderboard import (
    LeaderboardMe,
    LeaderboardRow,
    PointsHistoryOut,
)

router = APIRouter(tags=["leaderboard"])


async def _rows(db: DbSession, users: list[User], start_rank: int) -> list[LeaderboardRow]:
    ids = [u.id for u in users]
    if not ids:
        return []
    card_counts = dict(
        (
            await db.execute(
                select(UserCard.user_id, func.count())
                .where(UserCard.user_id.in_(ids))
                .group_by(UserCard.user_id)
            )
        ).all()
    )
    perfect_counts = dict(
        (
            await db.execute(
                select(PointsHistory.user_id, func.count())
                .where(PointsHistory.user_id.in_(ids), PointsHistory.is_perfect_xi.is_(True))
                .group_by(PointsHistory.user_id)
            )
        ).all()
    )
    return [
        LeaderboardRow(
            rank=start_rank + i,
            user_id=u.id,
            username=u.username,
            total_points=u.total_points,
            cards_owned=card_counts.get(u.id, 0),
            perfect_fives=perfect_counts.get(u.id, 0),
        )
        for i, u in enumerate(users)
    ]


@router.get("/leaderboard", response_model=list[LeaderboardRow])
async def leaderboard(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[LeaderboardRow]:
    users = list(
        await db.scalars(
            select(User)
            .where(User.is_active.is_(True))
            .order_by(User.total_points.desc(), User.created_at)
            .limit(limit)
            .offset(offset)
        )
    )
    return await _rows(db, users, offset + 1)


@router.get("/leaderboard/me", response_model=LeaderboardMe)
async def leaderboard_me(db: DbSession, user: CurrentUser) -> LeaderboardMe:
    total_users = await db.scalar(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    ) or 0
    ahead = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.is_active.is_(True), User.total_points > user.total_points)
    ) or 0
    rows = await _rows(db, [user], ahead + 1)
    return LeaderboardMe(rank=ahead + 1, total_users=total_users, row=rows[0] if rows else None)


@router.get("/leaderboard/me/history", response_model=list[PointsHistoryOut])
async def my_history(db: DbSession, user: CurrentUser) -> list[PointsHistoryOut]:
    rows = (
        await db.execute(
            select(PointsHistory, Match.slug)
            .join(Match, Match.id == PointsHistory.match_id)
            .where(PointsHistory.user_id == user.id)
            .order_by(PointsHistory.created_at.desc())
        )
    ).all()
    return [
        PointsHistoryOut(
            match_id=ph.match_id,
            match_slug=slug,
            points=ph.points,
            is_perfect_xi=ph.is_perfect_xi,
            breakdown=ph.breakdown,
            created_at=ph.created_at,
        )
        for ph, slug in rows
    ]
