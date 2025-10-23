# app/core/config.py
from __future__ import annotations

from typing import List, Union, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ambiente
    ENVIRONMENT: str = "dev"                 # dev | prod
    API_V1_PREFIX: str = "/api/v1"

    # Banco
    DATABASE_URL: Optional[str] = None       # ex.: postgresql+psycopg://postgres:...@db.x.supabase.co:5432/postgres?sslmode=require

    # Segurança / JWT (se já existirem em outro lugar, mantenha)
    SECRET_KEY: str = "dev-secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # CORS (aceita JSON ["http://...","http://..."] ou CSV "http://...,http://...")
    CORS_ORIGINS: Union[List[str], str] = []

    # Outras integrações
    ASAAS_API_BASE: str = "https://api.asaas.com/v3"

    class Config:
        env_file = ".env"
        extra = "ignore"   # ignora envs desconhecidas para não quebrar


# >>> NÃO ESQUEÇA desta linha <<<
settings = Settings()
