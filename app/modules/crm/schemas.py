# app/modules/crm/schemas.py
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field


# ===================== FUNIS =====================
class FunilBase(BaseModel):
    nome: str = Field(..., max_length=120)
    ordem: int | None = None


class FunilCreate(FunilBase):
    pass


class FunilUpdate(BaseModel):
    nome: str | None = Field(None, max_length=120)
    ordem: int | None = None


class FunilOut(FunilBase):
    id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# ===================== LEADS =====================
class LeadBase(BaseModel):
    titulo: str
    cpf: str | None = None
    telefone: str | None = None
    email: str | None = None
    estado: str | None = None
    cidade: str | None = None
    planoDesejado: str | None = None
    concursoDesejado: str | None = None
    descricao: str | None = None


class LeadCreate(LeadBase):
    stage_id: str


class LeadUpdate(BaseModel):
    # Atualizações do formulário
    titulo: str | None = None
    cpf: str | None = None
    telefone: str | None = None
    email: str | None = None
    estado: str | None = None
    cidade: str | None = None
    planoDesejado: str | None = None
    concursoDesejado: str | None = None
    descricao: str | None = None

    # Movimentação/Reordenação
    stage_id: str | None = None
    order_index: int | None = None


class LeadOut(LeadBase):
    id: int
    stage_id: str
    order_index: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
