from __future__ import annotations

import httpx
import pytest

from app.api.deps import get_db
from app.core.config import settings
from app.main import app
from app.seed import seed_packs

API = settings.api_v1_prefix


@pytest.fixture
async def client(db, world) -> httpx.AsyncClient:
    """Drives the real ASGI app against the in-memory database. The lifespan is
    not run, so no network sync happens during tests."""
    await seed_packs(db)
    app.dependency_overrides[get_db] = lambda: db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def register(ac: httpx.AsyncClient, username: str) -> dict:
    resp = await ac.post(
        f"{API}/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": "password1"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_health(client):
    resp = await client.get("/health")
    assert resp.json()["status"] == "ok"


async def test_register_grants_coins_and_no_free_players(client):
    """A new account starts with money and an empty collection: the squad has
    to be bought."""
    data = await register(client, "carol")
    assert data["welcome_cards"] == 0
    assert data["token"]["user"]["coins"] == settings.starting_coins

    token = data["token"]["access_token"]
    me = await client.get(f"{API}/auth/me", headers=auth(token))
    assert me.json()["username"] == "carol"

    collection = await client.get(f"{API}/cards/my-collection", headers=auth(token))
    assert collection.json()["total"] == 0


async def test_duplicate_username_is_rejected(client):
    await register(client, "dave")
    resp = await client.post(
        f"{API}/auth/register",
        json={"username": "dave", "email": "other@example.com", "password": "password1"},
    )
    assert resp.status_code == 409


async def test_login_then_buy_the_first_players(client):
    await register(client, "erin")
    resp = await client.post(f"{API}/auth/login", json={"username": "erin", "password": "password1"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    packs = (await client.get(f"{API}/cards/packs")).json()
    bought = await client.post(f"{API}/cards/open-pack", json={"pack_id": packs[0]["id"]}, headers=auth(token))
    assert bought.status_code == 200, bought.text

    collection = await client.get(f"{API}/cards/my-collection", headers=auth(token))
    assert collection.status_code == 200
    assert collection.json()["total"] == len(bought.json()["cards"])


async def test_collection_requires_a_token(client):
    assert (await client.get(f"{API}/cards/my-collection")).status_code == 401


async def test_packs_include_the_collector_booster(client):
    packs = (await client.get(f"{API}/cards/packs")).json()
    permanent = [p for p in packs if p["grants_permanent"]]
    starter = [p for p in packs if p["guarantees_goalkeeper"]]

    assert permanent, "должен быть бустер с вечными карточками"
    assert starter, "должен быть бустер с гарантированным вратарём"
    assert permanent[0]["price"] > starter[0]["price"]


async def test_open_pack_endpoint_spends_coins(client):
    token = (await register(client, "frank"))["token"]["access_token"]
    packs = (await client.get(f"{API}/cards/packs")).json()
    assert packs

    resp = await client.post(
        f"{API}/cards/open-pack", json={"pack_id": packs[0]["id"]}, headers=auth(token)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["coins_left"] == settings.starting_coins - packs[0]["price"]
    assert len(body["cards"]) >= 1


async def test_matches_and_leaderboard_are_public_enough(client, world):
    matches = await client.get(f"{API}/matches")
    assert matches.status_code == 200
    assert matches.json()["total"] == 1

    board = await client.get(f"{API}/leaderboard")
    assert board.status_code == 200


async def test_admin_endpoints_reject_plain_users(client):
    token = (await register(client, "grace"))["token"]["access_token"]
    resp = await client.post(
        f"{API}/admin/matches/1/lineups",
        json={"home_player_ids": [1], "away_player_ids": [7]},
        headers=auth(token),
    )
    assert resp.status_code == 403


async def buy_pack(client, headers, pack_id: int = 1):
    resp = await client.post(f"{API}/cards/open-pack", json={"pack_id": pack_id}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["cards"]


async def test_squad_flow_over_http(client, db, world):
    token = (await register(client, "heidi"))["token"]["access_token"]
    headers = auth(token)
    await buy_pack(client, headers)

    cards = (await client.get(f"{API}/cards/my-collection?limit=200", headers=headers)).json()["items"]
    keeper = next(c for c in cards if c["template"].get("position") == "GOALKEEPER")

    resp = await client.post(
        f"{API}/squad/select",
        json={"user_card_id": keeper["id"], "position_slot": "GK"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["filled_slots"] == 1

    validation = await client.post(f"{API}/squad/validate", headers=headers)
    assert validation.json()["valid"] is False

    removed = await client.delete(f"{API}/squad/remove/GK", headers=headers)
    assert removed.json()["filled_slots"] == 0


async def test_trade_flow_over_http(client, db, world):
    a = await register(client, "ivan")
    b = await register(client, "judy")
    a_headers = auth(a["token"]["access_token"])
    b_headers = auth(b["token"]["access_token"])
    await buy_pack(client, a_headers)
    b_owned = len(await buy_pack(client, b_headers))

    a_cards = (await client.get(f"{API}/cards/my-collection", headers=a_headers)).json()["items"]
    found = await client.get(f"{API}/trades/users?q=judy", headers=a_headers)
    receiver_id = found.json()[0]["id"]

    offer = await client.post(
        f"{API}/trades/offer",
        json={"receiver_id": receiver_id, "sender_cards": [a_cards[0]["id"]], "receiver_cards": []},
        headers=a_headers,
    )
    assert offer.status_code == 200, offer.text
    trade_id = offer.json()["id"]

    incoming = await client.get(f"{API}/trades/incoming", headers=b_headers)
    assert [o["id"] for o in incoming.json()] == [trade_id]

    accepted = await client.post(f"{API}/trades/{trade_id}/accept", headers=b_headers)
    assert accepted.json()["status"] == "ACCEPTED"

    b_cards = (await client.get(f"{API}/cards/my-collection", headers=b_headers)).json()
    assert b_cards["total"] == b_owned + 1
