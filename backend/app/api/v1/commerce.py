from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.core.constants import PAYMENTS
from app.models import Payment
from app.schemas.commerce import (
    CheckoutOut,
    CheckoutRequest,
    ClaimResult,
    ConfirmRequest,
    PaymentOut,
    ProductOut,
    QuestBoard,
)
from app.services.payment_service import PaymentService
from app.services.quest_service import QuestService

router = APIRouter(tags=["store"])

SANDBOX_NOTICE = (
    "Тестовый режим. Оплата имитируется на стороне приложения, "
    "деньги не списываются, данные карты не принимаются и не хранятся."
)


def _payment_out(payment: Payment) -> PaymentOut:
    return PaymentOut(
        id=payment.id,
        sku=payment.sku,
        title=payment.title,
        amount=payment.amount,
        currency=payment.currency,
        provider=payment.provider,
        status=payment.status,
        reference=payment.reference,
        failure_reason=payment.failure_reason,
        delivered=payment.delivered_json,
        created_at=payment.created_at,
        completed_at=payment.completed_at,
    )


@router.get("/store/products", response_model=list[ProductOut])
async def products() -> list[ProductOut]:
    return [ProductOut(**p) for p in PaymentService.catalogue()]


@router.post("/store/checkout", response_model=CheckoutOut)
async def checkout(payload: CheckoutRequest, db: DbSession, user: CurrentUser) -> CheckoutOut:
    """Opens a sandbox payment. Nothing is charged and no card data is taken."""
    payment = await PaymentService(db).create_checkout(user, payload.sku)
    return CheckoutOut(
        payment=_payment_out(payment),
        test_card=PAYMENTS["testCard"],
        notice=SANDBOX_NOTICE,
    )


@router.post("/store/payments/{payment_id}/confirm", response_model=PaymentOut)
async def confirm(
    payment_id: str, payload: ConfirmRequest, db: DbSession, user: CurrentUser
) -> PaymentOut:
    """Stands in for the provider callback: settles the payment and delivers."""
    payment = await PaymentService(db).confirm(payment_id, user, payload.outcome)
    return _payment_out(payment)


@router.get("/store/payments", response_model=list[PaymentOut])
async def payments(
    db: DbSession, user: CurrentUser, limit: Annotated[int, Query(ge=1, le=50)] = 20
) -> list[PaymentOut]:
    return [_payment_out(p) for p in await PaymentService(db).history(user, limit)]


@router.get("/quests", response_model=QuestBoard)
async def quests(db: DbSession, user: CurrentUser) -> QuestBoard:
    return QuestBoard(**await QuestService(db).list_quests(user))


@router.post("/quests/{key}/start", response_model=QuestBoard)
async def start_quest(key: str, db: DbSession, user: CurrentUser) -> QuestBoard:
    service = QuestService(db)
    await service.start(user, key)
    return QuestBoard(**await service.list_quests(user))


@router.post("/quests/{key}/claim", response_model=ClaimResult)
async def claim_quest(key: str, db: DbSession, user: CurrentUser) -> ClaimResult:
    return ClaimResult(**await QuestService(db).claim(user, key))
