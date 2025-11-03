# app/main.py
import sys
import asyncio

# Event loop compatível no Windows (safe em outros SOs também)
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine.url import make_url

from app.core.config import settings
from app.api.v1.router import api_router
from app.db.session import engine
from app.db.base import Base


def _normalize_origins(value) -> list[str]:
    """Aceita lista, JSON string ou CSV e devolve lista de origens."""
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [str(o).strip() for o in value if str(o).strip()]
    if isinstance(value, str):
        # tenta JSON primeiro
        try:
            as_json = json.loads(value)
            if isinstance(as_json, (list, tuple)):
                return [str(o).strip() for o in as_json if str(o).strip()]
        except Exception:
            pass
        # fallback: CSV
        return [o.strip() for o in value.split(",") if o.strip()]
    # fallback final
    return [str(value).strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Em desenvolvimento, cria tabelas automaticamente **apenas** se o dialeto for Postgres,
    evitando erros quando o fallback seria SQLite (p.ex. tipos ARRAY).
    """
    try:
        env = (settings.ENVIRONMENT or "").lower().strip()
    except Exception:
        env = "dev"

    if env == "dev":
        db_url = getattr(settings, "DATABASE_URL", "")
        try:
            url = make_url(db_url) if db_url else None
            is_postgres = url is not None and url.get_backend_name() == "postgresql"
        except Exception:
            is_postgres = False

        if is_postgres:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
    yield
    # teardown se necessário


# --- App ---
app = FastAPI(title="MentorPro Backend (mínimo)", lifespan=lifespan)

# --- CORS (colocado ANTES dos routers) ---
origins = _normalize_origins(getattr(settings, "CORS_ORIGINS", None))

# Defaults úteis para dev + seu front em produção (Railway)
if not origins:
    origins = [
        "http://localhost:8080",
        "http://localhost:5173",
        "https://mentorpro.up.railway.app",  # seu frontend em produção
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # use lista explícita se allow_credentials=True
    allow_credentials=True,     # se futuramente usar cookies/credenciais
    allow_methods=["*"],
    allow_headers=["*"],        # Authorization, Content-Type etc.
    expose_headers=["*"],       # opcional
)

# Healthcheck simples
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# --- API v1 (só depois do CORS) ---
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
