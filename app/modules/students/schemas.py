# app/modules/students/schemas.py
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import date
from typing import Optional, List

class StudentBase(BaseModel):
    nome: str
    email: EmailStr
    concurso: Optional[str] = None
    telefone: Optional[str] = None
    status: Optional[str] = "Ativo"
    plano: Optional[str] = None
    coach: Optional[str] = None
    cpf: Optional[str] = None
    dia_vencimento: Optional[int] = None
    data_compra: Optional[date] = None
    data_fim: Optional[date] = None

class StudentCreate(StudentBase):
    pass

class StudentUpdate(BaseModel):
    nome: Optional[str] = None
    concurso: Optional[str] = None
    telefone: Optional[str] = None
    status: Optional[str] = None
    plano: Optional[str] = None
    coach: Optional[str] = None
    cpf: Optional[str] = None
    dia_vencimento: Optional[int] = None
    data_compra: Optional[date] = None
    data_fim: Optional[date] = None

class StudentOut(StudentBase):
    id: int
    class Config:
        from_attributes = True

# Bulk
class BulkUpsertItem(StudentCreate):
    pass

# FE envia: { "alunos": [ ... ] }
class BulkUpsertIn(BaseModel):
    alunos: List[BulkUpsertItem]

class BulkDeleteIn(BaseModel):
    ids: List[int]

class BulkDeleteOut(BaseModel):
    count: int

class RevenueByCreatedOut(BaseModel):
    total: float    # soma em R$
    count: int      # nº de alunos no período (com ou sem preço)
    model_config = ConfigDict(from_attributes=True)