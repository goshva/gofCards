from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DbSession
from app.models import TradeOffer, TradeStatus, User
from app.schemas.trade import TradeCounter, TradeCreate, TradeOfferOut
from app.schemas.user import UserPublic
from app.services.trade_service import TradeService

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("/users", response_model=list[UserPublic])
async def search_users(
    db: DbSession,
    user: CurrentUser,
    q: Annotated[str, Query(min_length=1, max_length=32)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[UserPublic]:
    rows = await db.scalars(
        select(User)
        .where(User.username.ilike(f"%{q}%"), User.id != user.id, User.is_active.is_(True))
        .limit(limit)
    )
    return [UserPublic.model_validate(u) for u in rows]


@router.get("/users/{user_id}/cards", response_model=list)
async def user_cards(db: DbSession, user: CurrentUser, user_id: str) -> list:
    """Another player collection, so an offer can name the cards it asks for."""
    from app.models import UserCard
    from app.services import catalog

    cards = list(await db.scalars(select(UserCard).where(UserCard.user_id == user_id)))
    locked = await catalog.locked_card_ids(db, user_id)
    return await catalog.serialize_cards(db, cards, locked=locked)


@router.post("/offer", response_model=TradeOfferOut)
async def create_offer(payload: TradeCreate, db: DbSession, user: CurrentUser) -> TradeOfferOut:
    service = TradeService(db)
    offer = await service.create_offer(
        sender=user,
        receiver_id=payload.receiver_id,
        sender_cards=payload.sender_cards,
        receiver_cards=payload.receiver_cards,
        sender_coins=payload.sender_coins,
        message=payload.message,
    )
    return await service.serialize(offer)


async def _list_offers(db: DbSession, *conditions, status: TradeStatus | None) -> list[TradeOfferOut]:
    stmt = select(TradeOffer).where(*conditions)
    if status:
        stmt = stmt.where(TradeOffer.status == status)
    rows = await db.scalars(stmt.order_by(TradeOffer.created_at.desc()))
    service = TradeService(db)
    return [await service.serialize(o) for o in rows]


@router.get("/incoming", response_model=list[TradeOfferOut])
async def incoming(
    db: DbSession, user: CurrentUser, status: TradeStatus | None = None
) -> list[TradeOfferOut]:
    return await _list_offers(db, TradeOffer.receiver_id == user.id, status=status)


@router.get("/outgoing", response_model=list[TradeOfferOut])
async def outgoing(
    db: DbSession, user: CurrentUser, status: TradeStatus | None = None
) -> list[TradeOfferOut]:
    return await _list_offers(db, TradeOffer.sender_id == user.id, status=status)


@router.get("/history", response_model=list[TradeOfferOut])
async def history(db: DbSession, user: CurrentUser) -> list[TradeOfferOut]:
    return await _list_offers(
        db,
        or_(TradeOffer.sender_id == user.id, TradeOffer.receiver_id == user.id),
        TradeOffer.status != TradeStatus.PENDING,
        status=None,
    )


@router.post("/{trade_id}/accept", response_model=TradeOfferOut)
async def accept(trade_id: str, db: DbSession, user: CurrentUser) -> TradeOfferOut:
    service = TradeService(db)
    return await service.serialize(await service.accept_offer(trade_id, user))


@router.post("/{trade_id}/decline", response_model=TradeOfferOut)
async def decline(trade_id: str, db: DbSession, user: CurrentUser) -> TradeOfferOut:
    service = TradeService(db)
    return await service.serialize(await service.decline_offer(trade_id, user))


@router.post("/{trade_id}/cancel", response_model=TradeOfferOut)
async def cancel(trade_id: str, db: DbSession, user: CurrentUser) -> TradeOfferOut:
    service = TradeService(db)
    return await service.serialize(await service.cancel_offer(trade_id, user))


@router.post("/{trade_id}/counter", response_model=TradeOfferOut)
async def counter(
    trade_id: str, payload: TradeCounter, db: DbSession, user: CurrentUser
) -> TradeOfferOut:
    service = TradeService(db)
    offer = await service.counter_offer(
        trade_id,
        user,
        sender_cards=payload.sender_cards,
        receiver_cards=payload.receiver_cards,
        sender_coins=payload.sender_coins,
        message=payload.message,
    )
    return await service.serialize(offer)
