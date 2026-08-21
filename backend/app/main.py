from __future__ import annotations

import asyncio
import logging
import mimetypes
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
            logger.info("catalogue empty, first GoFuture sync will run in the background")
        # never block startup: the first sync takes a couple of minutes and a
        # platform health check would time out long before it finishes
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


# The built SPA is served by the API when it is present, so a single container
# covers the whole app. Without a build the backend still serves the API alone.
SPA_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if SPA_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=SPA_DIR / "assets"), name="spa-assets")

    # a mistyped API path must still answer 404 JSON rather than the SPA shell
    API_PREFIXES = (settings.api_v1_prefix.strip("/"), "media", "docs", "redoc", "openapi.json")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        """History-mode routing: a real file wins, anything else gets index.html."""
        if full_path.split("/")[0] in API_PREFIXES or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        candidate = (SPA_DIR / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(SPA_DIR):
            return FileResponse(candidate)
        return FileResponse(SPA_DIR / "index.html")

else:
    logger.warning("SPA build not found at %s, serving the API only", SPA_DIR)
