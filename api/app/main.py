import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import get_engine
from app.routers import content as content_router
from app.routers import sessions as sessions_router

logger = logging.getLogger("inkling.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("db_ok url=%s", _safe_url(settings.database_url))
    except Exception:
        logger.exception("db_unreachable url=%s", _safe_url(settings.database_url))
        raise
    yield


def _safe_url(url: str) -> str:
    return url.split("@", 1)[-1] if "@" in url else url


app = FastAPI(title="Inkling API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router.router)
app.include_router(content_router.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
