from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.rating_columns import RatingMixin


class Team(Base, RatingMixin):
    """A real GoFuture team, mirrored from the public API."""

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    short_title: Mapped[str | None] = mapped_column(String(64))
    country: Mapped[str | None] = mapped_column(String(128))
    city: Mapped[str | None] = mapped_column(String(128))
    image_url: Mapped[str | None] = mapped_column(String(2048))
    photo_path: Mapped[str | None] = mapped_column(String(255))
    # GoFuture ships no team badges, so the UI paints a monogram in this colour
    color: Mapped[str | None] = mapped_column(String(7))

    players = relationship("Player", back_populates="team", lazy="selectin")
