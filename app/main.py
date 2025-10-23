import sys
import asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import engine
from app.db.base import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Em dev, cria tabelas automaticamente
    if settings.ENVIRONMENT.lower() == "dev":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    # teardown se necessário

app = FastAPI(title="MentorPro Backend (mínimo)", lifespan=lifespan)

# Healthcheck
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# API v1
app.include_router(api_router, prefix=settings.API_V1_PREFIX)