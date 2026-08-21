from fastapi import APIRouter

from app.api.v1 import admin, auth, cards, commerce, leaderboard, matches, squads, tournament, trades

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cards.router)
api_router.include_router(trades.router)
api_router.include_router(squads.router)
api_router.include_router(matches.router)
api_router.include_router(leaderboard.router)
api_router.include_router(tournament.router)
api_router.include_router(commerce.router)
api_router.include_router(admin.router)
