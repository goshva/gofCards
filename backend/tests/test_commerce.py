from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.constants import QUESTS
from app.core.exceptions import AlreadyExists, NotAllowed, NotFound
from app.models import Pack, Payment, PaymentStatus, QuestProgress, Referral, User, UserCard
from app.models.base import utcnow
from app.core.security import hash_password
from app.services.payment_service import PaymentService
from app.services.quest_service import QuestService


@pytest.fixture
async def store(db, world):
    """The collector booster the paid products deliver, keyed by the id the
    product catalogue points at."""
    pack = Pack(
        id=4,
        name="Коллекционный бустер",
        price=3500,
        contents_json={"RARE": 1, "ANY": 2},
        team_card_chance=15,
        grants_permanent=True,
    )
    db.add(pack)
    await db.commit()
    return pack


# ---------- sandbox payments ----------


def test_catalogue_is_marked_as_a_sandbox():
    products = PaymentService.catalogue()
    assert products
    assert all(p["provider"] == "sandbox" for p in products)
    assert all(p["price"] > 0 for p in products)


async def test_checkout_creates_a_pending_intent_and_charges_nothing(db, store, alice):
    before = alice.coins
    payment = await PaymentService(db).create_checkout(alice, "PACK_COLLECTOR")

    assert payment.status == PaymentStatus.PENDING
    assert payment.reference.startswith("sbx_")
    assert payment.provider == "sandbox"
    assert alice.coins == before, "до подтверждения ничего не начисляется"


async def test_unknown_sku_is_rejected(db, store, alice):
    with pytest.raises(NotFound):
        await PaymentService(db).create_checkout(alice, "NOT_A_PRODUCT")


async def test_a_confirmed_purchase_delivers_permanent_cards(db, store, alice):
    service = PaymentService(db)
    payment = await service.create_checkout(alice, "PACK_COLLECTOR")
    settled = await service.confirm(payment.id, alice)

    assert settled.status == PaymentStatus.SUCCEEDED
    assert settled.completed_at is not None

    cards = list(await db.scalars(select(UserCard).where(UserCard.user_id == alice.id)))
    assert cards, "покупка должна выдать карточки"
    assert all(c.is_permanent for c in cards)
    assert len(settled.delivered_json["cards"]) == len(cards)


async def test_a_coin_bundle_lands_on_the_balance(db, store, alice):
    before = alice.coins
    service = PaymentService(db)
    payment = await service.create_checkout(alice, "COINS_10000")
    settled = await service.confirm(payment.id, alice)

    assert settled.status == PaymentStatus.SUCCEEDED
    assert alice.coins == before + 10_000
    assert settled.delivered_json["coins"] == 10_000


async def test_a_failed_payment_delivers_nothing(db, store, alice):
    before = alice.coins
    service = PaymentService(db)
    payment = await service.create_checkout(alice, "COINS_10000")
    settled = await service.confirm(payment.id, alice, outcome="failure")

    assert settled.status == PaymentStatus.FAILED
    assert settled.failure_reason
    assert alice.coins == before
    assert await db.scalar(select(func.count()).select_from(UserCard)) == 0


async def test_a_payment_cannot_be_settled_twice(db, store, alice):
    service = PaymentService(db)
    payment = await service.create_checkout(alice, "COINS_10000")
    await service.confirm(payment.id, alice)

    with pytest.raises(AlreadyExists):
        await service.confirm(payment.id, alice)


async def test_a_payment_belongs_to_its_buyer(db, store, alice, bob):
    service = PaymentService(db)
    payment = await service.create_checkout(alice, "COINS_10000")

    with pytest.raises(NotAllowed):
        await service.confirm(payment.id, bob)


async def test_a_multipack_delivers_every_booster(db, store, alice):
    service = PaymentService(db)
    payment = await service.create_checkout(alice, "PACK_COLLECTOR_X3")
    settled = await service.confirm(payment.id, alice)

    cards = list(await db.scalars(select(UserCard).where(UserCard.user_id == alice.id)))
    # three openings of a three-card booster
    assert len(cards) == len(settled.delivered_json["cards"])
    assert len(cards) == 9
    assert all(c.is_permanent for c in cards)


# ---------- quests ----------


async def test_the_board_lists_every_quest_with_a_referral_code(db, alice):
    board = await QuestService(db).list_quests(alice)

    assert len(board["quests"]) == len(QUESTS["items"])
    assert len(board["referral_code"]) == 6
    assert board["friends_invited"] == 0
    assert board["total_earned"] == 0


async def test_a_referral_code_is_stable_and_unique(db, alice, bob):
    service = QuestService(db)
    first = await service.ensure_code(alice)
    again = await service.ensure_code(alice)
    other = await service.ensure_code(bob)

    assert first == again, "код не должен меняться между вызовами"
    assert first != other
    # look-alike characters are excluded so a code can be read out loud
    assert not set(first) & set("OI01")


async def test_a_simple_quest_pays_out_once(db, alice):
    before = alice.coins
    result = await QuestService(db).claim(alice, "DAILY_CHECKIN")

    assert result["reward"] == 150
    assert alice.coins == before + 150
    assert result["quest"]["times_claimed"] == 1
    assert result["quest"]["status"] == "cooldown"


async def test_a_repeatable_quest_waits_out_its_cooldown(db, alice):
    service = QuestService(db)
    await service.claim(alice, "DAILY_CHECKIN")

    with pytest.raises(AlreadyExists):
        await service.claim(alice, "DAILY_CHECKIN")

    progress = await db.scalar(
        select(QuestProgress).where(QuestProgress.quest_key == "DAILY_CHECKIN")
    )
    progress.last_claimed_at = utcnow() - timedelta(hours=48)
    await db.commit()

    second = await service.claim(alice, "DAILY_CHECKIN")
    assert second["quest"]["times_claimed"] == 2


async def test_a_subscription_quest_needs_the_link_opened_first(db, alice):
    service = QuestService(db)

    with pytest.raises(NotAllowed):
        await service.claim(alice, "SUBSCRIBE_TELEGRAM")

    await service.start(alice, "SUBSCRIBE_TELEGRAM")
    result = await service.claim(alice, "SUBSCRIBE_TELEGRAM")

    assert result["reward"] == 300
    assert result["quest"]["status"] == "done"


async def test_a_one_shot_quest_cannot_be_farmed(db, alice):
    service = QuestService(db)
    await service.start(alice, "SUBSCRIBE_YOUTUBE")
    await service.claim(alice, "SUBSCRIBE_YOUTUBE")

    with pytest.raises(AlreadyExists):
        await service.claim(alice, "SUBSCRIBE_YOUTUBE")


async def test_the_referral_quest_is_not_claimable_by_hand(db, alice):
    with pytest.raises(NotAllowed):
        await QuestService(db).claim(alice, "INVITE_FRIEND")


async def test_an_unknown_quest_is_rejected(db, alice):
    with pytest.raises(NotFound):
        await QuestService(db).claim(alice, "NOPE")


async def test_an_invite_pays_both_sides(db, alice, bob):
    service = QuestService(db)
    code = await service.ensure_code(alice)
    inviter_before, invitee_before = alice.coins, bob.coins

    referral = await service.register_referral(bob, code)

    assert referral is not None
    assert alice.coins == inviter_before + QUESTS["referralReward"]
    assert bob.coins == invitee_before + QUESTS["referralFriendBonus"]

    board = await service.list_quests(alice)
    assert board["friends_invited"] == 1


async def test_the_same_friend_counts_once(db, alice, bob):
    service = QuestService(db)
    code = await service.ensure_code(alice)
    await service.register_referral(bob, code)
    coins_after_first = alice.coins

    assert await service.register_referral(bob, code) is None
    assert alice.coins == coins_after_first
    assert await db.scalar(select(func.count()).select_from(Referral)) == 1


async def test_you_cannot_invite_yourself(db, alice):
    service = QuestService(db)
    code = await service.ensure_code(alice)
    before = alice.coins

    assert await service.register_referral(alice, code) is None
    assert alice.coins == before


async def test_an_unknown_code_is_ignored_quietly(db, bob):
    before = bob.coins
    assert await QuestService(db).register_referral(bob, "ZZZZZZ") is None
    assert bob.coins == before


async def test_the_code_is_matched_case_insensitively(db, alice, bob):
    service = QuestService(db)
    code = await service.ensure_code(alice)

    referral = await service.register_referral(bob, code.lower())
    assert referral is not None
