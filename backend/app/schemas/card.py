from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, computed_field

from app.models.base import CardType, Position, Rarity
from app.schemas.common import ORMModel


class TeamBrief(ORMModel):
    id: int
    slug: str
    title: str
    short_title: str | None = None
    country: str | None = None
    image_url: str | None = None
    photo_path: str | None = None
    color: str | None = None
    ovr: int = 0
    rank: int | None = None

    @computed_field
    @property
    def logo_url(self) -> str | None:
        """Generated crest — GoFuture publishes no team badges."""
        return f"/media/{self.photo_path}" if self.photo_path else self.image_url


class PlayerBrief(ORMModel):
    id: int
    slug: str
    nickname: str
    first_name: str | None = None
    last_name: str | None = None
    country: str | None = None
    position: Position
    jersey_number: int | None = None
    date_of_birth: date | None = None
    image_url: str | None = None
    photo_path: str | None = None
    team: TeamBrief | None = None

    ovr: int = 0
    rank: int | None = None
    attributes: dict[str, int] = {}
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    best_round: int = 0

    @computed_field
    @property
    def photo_url(self) -> str | None:
        """Locally mirrored photo; the upstream link expires within a day."""
        return f"/media/{self.photo_path}" if self.photo_path else self.image_url

    @computed_field
    @property
    def age(self) -> int | None:
        if self.date_of_birth is None:
            return None
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )


class CardTemplateOut(BaseModel):
    id: int
    card_type: CardType
    rarity: Rarity
    base_price: int
    image_url: str | None = None
    name: str
    subtitle: str | None = None
    position: Position | None = None
    ovr: int = 0
    rank: int | None = None
    attributes: dict[str, int] = {}
    player: PlayerBrief | None = None
    team: TeamBrief | None = None


class UserCardOut(BaseModel):
    id: str
    card_type: CardType
    card_template_id: int
    acquired_at: datetime
    source: str
    locked_by_trade: bool = False
    in_squad: bool = False
    is_permanent: bool = False
    tournaments_used: int = 0
    runs_left: int | None = None
    template: CardTemplateOut


class CollectionStats(BaseModel):
    total_cards: int
    unique_templates: int
    by_rarity: dict[str, int]
    player_cards: int
    team_cards: int
    templates_total: int
    best_ovr: int = 0
    average_ovr: float = 0.0


class RankingRow(BaseModel):
    rank: int
    ovr: int
    player: PlayerBrief
    rarities: list[Rarity]
    owned: int = 0


class PackOut(ORMModel):
    id: int
    name: str
    description: str | None = None
    price: int
    contents_json: dict[str, int]
    team_card_chance: int
    grants_permanent: bool = False
    guarantees_goalkeeper: bool = False


class OpenPackRequest(BaseModel):
    pack_id: int


class OpenPackResult(BaseModel):
    opening_id: str
    pack_id: int
    coins_spent: int
    coins_left: int
    cards: list[UserCardOut]
