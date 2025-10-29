from __future__ import annotations
from pydantic import BaseModel, Field

# Entrada para criar/atualizar as credenciais do Asaas
class AsaasConfigIn(BaseModel):
    api_key: str = Field(..., min_length=10)
    sandbox: bool = True

# Saída (quando buscamos a config do mentor)
class AsaasConfigOut(BaseModel):
    api_key: str
    sandbox: bool

class HealthOut(BaseModel):
    ok: bool
    message: str | None = None
