from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Position, str_enum
from app.models.rating_columns import RatingMixin


class Player(Base, RatingMixin):
    """A real athlete. Position comes from the GoFuture athlete endpoint
    (`Goalkeeper` / `Field player`) — phygital football only has those two."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    nickname: Mapped[str] = mapped_column(String(128), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    country: Mapped[str | None] = mapped_column(String(128))
    position: Mapped[Position] = mapped_column(
        str_enum(Position, "position"), default=Position.FIELD, nullable=False
    )
    jersey_number: Mapped[int | None] = mapped_column(Integer)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    # GoFuture serves presigned S3 links that expire in 24h — refreshed on every sync
    image_url: Mapped[str | None] = mapped_column(String(2048))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    # local copy of the GoFuture photo, served from /media so cards survive
    # the 24h expiry of the upstream presigned link
    photo_path: Mapped[str | None] = mapped_column(String(255))

    team = relationship("Team", back_populates="players", lazy="selectin")

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.first_name, self.last_name) if p) or self.nickname
