from __future__ import annotations

import asyncio
import logging
import mimetypes
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.models import Base
from app.seed import has_catalog, seed_packs
from app.services.media import MEDIA_ROOT
from app.services.sync_service import run_sync_once, sync_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        await seed_packs(db)
        empty = not await has_catalog(db)

    task: asyncio.Task | None = None
    if settings.sync_on_startup:
        if empty:
            # nothing to hand out until the catalogue exists, so seed it inline
            logger.info("catalogue empty, running first GoFuture sync")
            await run_sync_once()
        task = asyncio.create_task(sync_loop(settings.sync_interval_seconds))

    yield

    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    lifespan=lifespan,
    description="Коллекционные карточки и фэнтези-составы по фиджитал-футболу Games of the Future",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)

# Windows does not register these in its MIME registry, and StaticFiles reads
# from there — without this the photos are served as text/plain
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("image/avif", ".avif")

# locally mirrored athlete photos and club badges, served from one place
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_ROOT), name="media")


@app.get("/health", tags=["service"])
async def health() -> dict:
    return {"status": "ok", "project": settings.project_name}
