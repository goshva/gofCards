from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import PAYMENTS
from app.core.exceptions import AlreadyExists, NotAllowed, NotFound
from app.models import Pack, Payment, PaymentStatus, User
from app.models.base import utcnow
from app.services.card_service import CardService

PRODUCTS: dict[str, dict[str, Any]] = {p["sku"]: p for p in PAYMENTS["products"]}


class PaymentService:
    """A sandbox checkout.

    It reproduces the lifecycle of a real integration — create an intent, let
    the provider settle it, deliver the goods exactly once — but nothing is
    charged and no card data is accepted or stored. Swapping in a real provider
    means replacing `confirm` with a webhook handler; everything else stands.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def catalogue() -> list[dict[str, Any]]:
        return [
            {**product, "currency": PAYMENTS["currency"], "provider": PAYMENTS["provider"]}
            for product in PAYMENTS["products"]
        ]

    async def create_checkout(self, user: User, sku: str) -> Payment:
        product = PRODUCTS.get(sku)
        if product is None:
            raise NotFound(f"Неизвестный товар: {sku}")

        payment = Payment(
            user_id=user.id,
            sku=sku,
            title=product["title"],
            amount=int(product["price"]),
            currency=PAYMENTS["currency"],
            provider=PAYMENTS["provider"],
            status=PaymentStatus.PENDING,
            reference=f"sbx_{secrets.token_hex(6)}",
        )
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def _deliver(self, user: User, product: dict[str, Any]) -> dict[str, Any]:
        """Hand over what was bought: coins, booster openings, or both."""
        delivered: dict[str, Any] = {"coins": 0, "cards": []}

        coins = int(product.get("coins") or 0)
        if coins:
            user.coins += coins
            delivered["coins"] = coins

        pack_id = product.get("packId")
        if pack_id:
            pack = await self.db.get(Pack, int(pack_id))
            if pack is None:
                raise NotFound("Бустер недоступен")
            service = CardService(self.db)
            for _ in range(int(product.get("quantity") or 1)):
                # the purchase already paid for it, so the coin price is waived
                user.coins += pack.price
                _, cards = await service.open_pack(user, pack)
                delivered["cards"].extend(
                    {
                        "id": card.id,
                        "template_id": card.card_template_id,
                        "is_permanent": card.is_permanent,
                    }
                    for card in cards
                )
        return delivered

    async def confirm(self, payment_id: str, user: User, outcome: str = "success") -> Payment:
        payment = await self.db.get(Payment, payment_id)
        if payment is None:
            raise NotFound("Платёж не найден")
        if payment.user_id != user.id:
            raise NotAllowed("Это не ваш платёж")
        if payment.status != PaymentStatus.PENDING:
            raise AlreadyExists(f"Платёж уже обработан: {payment.status.value}")

        if outcome != "success":
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = "Тестовый отказ платежа"
            payment.completed_at = utcnow()
            await self.db.commit()
            await self.db.refresh(payment)
            return payment

        product = PRODUCTS.get(payment.sku)
        if product is None:
            raise NotFound("Товар больше не доступен")

        payment.delivered_json = await self._deliver(user, product)
        payment.status = PaymentStatus.SUCCEEDED
        payment.completed_at = utcnow()
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def history(self, user: User, limit: int = 20) -> list[Payment]:
        rows = await self.db.scalars(
            select(Payment)
            .where(Payment.user_id == user.id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
        )
        return list(rows)
