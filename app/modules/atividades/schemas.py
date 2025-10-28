from __future__ import annotations
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ====================== FUNIS (STAGES) ======================

class StageBase(BaseModel):
    nome: str = Field(..., max_length=120)
    cor: Optional[str] = Field(None, max_length=48)
    ordem: Optional[int] = None


class StageCreate(StageBase):
    pass


class StageUpdate(BaseModel):
    nome: Optional[str] = Field(None, max_length=120)
    cor: Optional[str] = Field(None, max_length=48)
    ordem: Optional[int] = None


class StageOut(BaseModel):
    id: str
    nome: str
    cor: Optional[str] = None
    ordem: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ====================== ATIVIDADES (ITEMS) ======================

class ActivityBase(BaseModel):
    titulo: str = Field(..., max_length=200)
    descricao: Optional[str] = None
    prioridade: Optional[str] = Field(None, pattern="^(Alta|Média|Baixa)?$")
    responsavel: Optional[str] = Field(None, max_length=120)
    dataVencimento: Optional[date] = Field(None, description="YYYY-MM-DD")
    tags: Optional[List[str]] = None


class ActivityCreate(ActivityBase):
    stage_id: str
    # order_index é calculado automaticamente na criação (vai pro final da coluna)


class ActivityUpdate(BaseModel):
    # Campos editáveis de conteúdo
    titulo: Optional[str] = Field(None, max_length=200)
    descricao: Optional[str] = None
    prioridade: Optional[str] = Field(None, pattern="^(Alta|Média|Baixa)?$")
    responsavel: Optional[str] = Field(None, max_length=120)
    dataVencimento: Optional[date] = Field(None, description="YYYY-MM-DD")
    tags: Optional[List[str]] = None

    # Movimentação/ordenamento
    stage_id: Optional[str] = None
    order_index: Optional[int] = None


class ActivityOut(BaseModel):
    id: int
    stage_id: str
    order_index: int

    titulo: str
    descricao: Optional[str] = None
    prioridade: Optional[str] = None
    responsavel: Optional[str] = None
    dataVencimento: Optional[date] = None
    tags: Optional[List[str]] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
