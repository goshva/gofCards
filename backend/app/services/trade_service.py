from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AlreadyExists,
    CardLocked,
    InsufficientFunds,
    NotAllowed,
    NotFound,
    NotOwner,
)
from app.models import SquadEntry, TradeOffer, TradeStatus, User, UserCard
from app.schemas.trade import TradeOfferOut
from app.schemas.user import UserPublic
from app.services import catalog


class TradeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _assert_owns(self, user_id: str, card_ids: list[str]) -> list[UserCard]:
        if not card_ids:
            return []
        cards = list(await self.db.scalars(select(UserCard).where(UserCard.id.in_(card_ids))))
        found = {c.id for c in cards}
        missing = set(card_ids) - found
        if missing:
            raise NotFound(f"Карточки не найдены: {', '.join(sorted(missing))}")
        for card in cards:
            if card.user_id != user_id:
                raise NotOwner(f"Карточка {card.id} принадлежит другому пользователю")
        return cards

    async def _assert_not_locked(self, card_ids: list[str], exclude_offer_id: str | None = None) -> None:
        """A card may sit in at most one pending offer, otherwise accepting two
        offers in a row would move the same card twice."""
        if not card_ids:
            return
        offers = await self.db.scalars(
            select(TradeOffer).where(TradeOffer.status == TradeStatus.PENDING)
        )
        wanted = set(card_ids)
        for offer in offers:
            if exclude_offer_id and offer.id == exclude_offer_id:
                continue
            busy = wanted & (set(offer.sender_cards or []) | set(offer.receiver_cards or []))
            if busy:
                raise CardLocked(
                    f"Карточки уже в активном обмене: {', '.join(sorted(busy))}"
                )

    async def create_offer(
        self,
        sender: User,
        receiver_id: str,
        sender_cards: list[str],
        receiver_cards: list[str],
        sender_coins: int = 0,
        message: str | None = None,
        counter_of_id: str | None = None,
    ) -> TradeOffer:
        if receiver_id == sender.id:
            raise NotAllowed("Нельзя обмениваться с самим собой")
        receiver = await self.db.get(User, receiver_id)
        if receiver is None or not receiver.is_active:
            raise NotFound("Получатель не найден")
        if sender_coins > sender.coins:
            raise InsufficientFunds("Недостаточно монет для этого предложения")

        await self._assert_owns(sender.id, sender_cards)
        await self._assert_owns(receiver_id, receiver_cards)
        await self._assert_not_locked(sender_cards + receiver_cards)

        offer = TradeOffer(
            sender_id=sender.id,
            receiver_id=receiver_id,
            sender_cards=sender_cards,
            receiver_cards=receiver_cards,
            sender_coins=sender_coins,
            message=message,
            counter_of_id=counter_of_id,
            status=TradeStatus.PENDING,
        )
        self.db.add(offer)
        await self.db.commit()
        await self.db.refresh(offer)
        return offer

    async def _get_open_offer(self, trade_id: str) -> TradeOffer:
        offer = await self.db.get(TradeOffer, trade_id)
        if offer is None:
            raise NotFound("Предложение обмена не найдено")
        if offer.status != TradeStatus.PENDING:
            raise AlreadyExists(f"Предложение уже обработано: {offer.status.value}")
        return offer

    async def accept_offer(self, trade_id: str, user: User) -> TradeOffer:
        offer = await self._get_open_offer(trade_id)
        if offer.receiver_id != user.id:
            raise NotAllowed("Принять предложение может только получатель")

        sender = await self.db.get(User, offer.sender_id)
        if sender is None:
            raise NotFound("Отправитель не найден")

        # Ownership is re-checked at accept time: cards may have moved since the
        # offer was created.
        await self._assert_owns(offer.sender_id, offer.sender_cards or [])
        await self._assert_owns(offer.receiver_id, offer.receiver_cards or [])
        if offer.sender_coins > sender.coins:
            raise InsufficientFunds("У отправителя больше нет нужной суммы")

        moved_ids = list(offer.sender_cards or []) + list(offer.receiver_cards or [])

        for card_id in offer.sender_cards or []:
            card = await self.db.get(UserCard, card_id)
            card.user_id = offer.receiver_id
            card.source = "trade"
        for card_id in offer.receiver_cards or []:
            card = await self.db.get(UserCard, card_id)
            card.user_id = offer.sender_id
            card.source = "trade"

        if offer.sender_coins:
            sender.coins -= offer.sender_coins
            user.coins += offer.sender_coins

        # A traded card cannot stay in the previous owner squad.
        entries = await self.db.scalars(
            select(SquadEntry).where(SquadEntry.user_card_id.in_(moved_ids))
        )
        for entry in entries:
            await self.db.delete(entry)

        offer.status = TradeStatus.ACCEPTED
        await self.db.commit()
        await self.db.refresh(offer)
        return offer

    async def decline_offer(self, trade_id: str, user: User) -> TradeOffer:
        offer = await self._get_open_offer(trade_id)
        if offer.receiver_id != user.id:
            raise NotAllowed("Отклонить предложение может только получатель")
        offer.status = TradeStatus.DECLINED
        await self.db.commit()
        await self.db.refresh(offer)
        return offer

    async def cancel_offer(self, trade_id: str, user: User) -> TradeOffer:
        offer = await self._get_open_offer(trade_id)
        if offer.sender_id != user.id:
            raise NotAllowed("Отменить предложение может только отправитель")
        offer.status = TradeStatus.CANCELLED
        await self.db.commit()
        await self.db.refresh(offer)
        return offer

    async def counter_offer(
        self,
        trade_id: str,
        user: User,
        sender_cards: list[str],
        receiver_cards: list[str],
        sender_coins: int = 0,
        message: str | None = None,
    ) -> TradeOffer:
        """The receiver closes the original offer and opens a mirrored one, so the
        cards it locked are released before the new one claims them."""
        offer = await self._get_open_offer(trade_id)
        if offer.receiver_id != user.id:
            raise NotAllowed("Встречное предложение делает получатель")

        offer.status = TradeStatus.COUNTERED
        await self.db.commit()

        return await self.create_offer(
            sender=user,
            receiver_id=offer.sender_id,
            sender_cards=sender_cards,
            receiver_cards=receiver_cards,
            sender_coins=sender_coins,
            message=message,
            counter_of_id=offer.id,
        )

    async def serialize(self, offer: TradeOffer) -> TradeOfferOut:
        all_ids = list(offer.sender_cards or []) + list(offer.receiver_cards or [])
        cards = {
            c.id: c
            for c in await self.db.scalars(select(UserCard).where(UserCard.id.in_(all_ids)))
        }
        sender_cards = [cards[i] for i in (offer.sender_cards or []) if i in cards]
        receiver_cards = [cards[i] for i in (offer.receiver_cards or []) if i in cards]
        return TradeOfferOut(
            id=offer.id,
            status=offer.status,
            sender=UserPublic.model_validate(offer.sender),
            receiver=UserPublic.model_validate(offer.receiver),
            sender_cards=await catalog.serialize_cards(self.db, sender_cards),
            receiver_cards=await catalog.serialize_cards(self.db, receiver_cards),
            sender_coins=offer.sender_coins,
            message=offer.message,
            counter_of_id=offer.counter_of_id,
            created_at=offer.created_at,
            updated_at=offer.updated_at,
        )
