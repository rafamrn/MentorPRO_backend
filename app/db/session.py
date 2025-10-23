# app/db/session.py
import sys, asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
from pathlib import Path
from app.core.config import settings

if settings.DATABASE_URL:
    _db_url = settings.DATABASE_URL
else:
    data_dir = (Path(__file__).resolve().parents[2] / "data")
    data_dir.mkdir(parents=True, exist_ok=True)
    db_file = data_dir / "mentorpro.db"
    # usar caminho POSIX para o SQLAlchemy
    _db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"

engine = create_async_engine(_db_url, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
