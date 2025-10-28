from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict

from pydantic import BaseModel, Field, EmailStr


# ---------------- Pipelines ----------------
class CRMPipelineBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    color: str = Field(default="border-l-primary")


class CRMPipelineCreate(CRMPipelineBase):
    position: Optional[int] = None


class CRMPipelineUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    color: Optional[str] = None
    position: Optional[int] = None


class CRMPipelineOut(CRMPipelineBase):
    id: int
    position: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------- Leads ----------------
class CRMLeadBase(BaseModel):
    titulo: str
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    estado: Optional[str] = None  # UF
    cidade: Optional[str] = None
    plano_desejado: Optional[str] = None
    concurso_desejado: Optional[str] = None
    descricao: Optional[str] = None


class CRMLeadCreate(CRMLeadBase):
    pipeline_id: Optional[int] = None   # se não enviar, vai para o primeiro pipeline
    position: Optional[int] = None


class CRMLeadUpdate(CRMLeadBase):
    pipeline_id: Optional[int] = None
    position: Optional[int] = None


class CRMLeadMove(BaseModel):
    to_pipeline_id: int
    to_position: int = 0


class CRMLeadOut(CRMLeadBase):
    id: int
    pipeline_id: int
    position: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# -------------- Board (pipelines + leads) --------------
class CRMBoardOut(BaseModel):
    pipelines: List[CRMPipelineOut]
    leads_by_pipeline: Dict[int, List[CRMLeadOut]]


# -------------- Stats --------------
class CRMStatsOut(BaseModel):
    total_leads: int
    closed_count: int
    in_progress: int
