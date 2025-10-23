# test_db.py
from sqlalchemy import text
from sqlalchemy import create_engine

engine = create_engine("postgresql+psycopg://postgres:2OuiW6psxgkGfpfS@db.psxdobpqnnrddhxasxpi.supabase.co:5432/postgres?sslmode=require", pool_pre_ping=True)
with engine.begin() as conn:
    r = conn.execute(text("select now()")).scalar_one()
    print("DB ok:", r)