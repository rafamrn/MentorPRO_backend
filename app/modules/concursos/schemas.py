from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import date

ConcursoStatus = Literal[
    "Previsto",
    "Autorizado",
    "Edital publicado",
    "Inscrições abertas",
    "Inscrições encerradas",
    "Prova aplicada",
]

class ConcursoBase(BaseModel):
    titulo: str
    orgao: Optional[str] = None
    uf: Optional[str] = None
    cidade: Optional[str] = None
    banca: Optional[str] = None
    cargo: Optional[str] = None
    escolaridade: Optional[str] = None
    vagas: Optional[int] = None
    salario: Optional[float] = None
    modalidade: Optional[str] = None
    status: ConcursoStatus
    tags: List[str] = Field(default_factory=list)
    edital_url: Optional[str] = None
    inscricao_inicio: Optional[date] = None
    inscricao_fim: Optional[date] = None
    prova_data: Optional[date] = None
    observacoes: Optional[str] = None
    destaque: Optional[bool] = None

class ConcursoCreate(ConcursoBase):
    """Mesmos campos do base; titulo e status já são obrigatórios."""

class ConcursoUpdate(BaseModel):
    """Todos os campos opcionais para atualização parcial (PUT/PATCH)."""
    titulo: Optional[str] = None
    orgao: Optional[str] = None
    uf: Optional[str] = None
    cidade: Optional[str] = None
    banca: Optional[str] = None
    cargo: Optional[str] = None
    escolaridade: Optional[str] = None
    vagas: Optional[int] = None
    salario: Optional[float] = None
    modalidade: Optional[str] = None
    status: Optional[ConcursoStatus] = None
    tags: Optional[List[str]] = None
    edital_url: Optional[str] = None
    inscricao_inicio: Optional[date] = None
    inscricao_fim: Optional[date] = None
    prova_data: Optional[date] = None
    observacoes: Optional[str] = None
    destaque: Optional[bool] = None

class ConcursoOut(ConcursoBase):
    id: int
    mentor_id: int

    model_config = {"from_attributes": True}
