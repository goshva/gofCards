from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at_col, uuid_pk


class PointsHistory(Base):
    __tablename__ = "points_history"
    __table_args__ = (UniqueConstraint("user_id", "match_id", name="uq_points_user_match"),)

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_perfect_xi: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = created_at_col()


class SyncState(Base):
    """Single-row bookkeeping for the GoFuture sync loop."""

    __tablename__ = "sync_state"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str] = mapped_column(String(32), default="never", nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(1024))
    teams_synced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    players_synced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matches_synced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    templates_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
