import sys, asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# --- CORS (DEV) ---
origins = settings.CORS_ORIGINS
# Settings pode vir como str (".env"); normaliza para lista
if isinstance(origins, str):
    try:
        origins = json.loads(origins)  # aceita formato JSON: ["http://...","http://..."]
    except Exception:
        origins = [o.strip() for o in origins.split(",") if o.strip()]

# Defaults úteis em dev
if not origins:
    origins = ["http://localhost:8080", "http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           # precisa ser lista específica se allow_credentials=True
    allow_credentials=True,          # mantenha True para cookies/credenciais se usar no futuro
    allow_methods=["*"],
    allow_headers=["*"],             # inclui Authorization, Content-Type etc.
    expose_headers=["*"],            # opcional: expor headers custom
)