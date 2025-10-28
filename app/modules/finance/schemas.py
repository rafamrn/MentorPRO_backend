# app/modules/finance/schemas.py
from pydantic import BaseModel, field_validator
from datetime import date
from typing import Optional

class PaymentBase(BaseModel):
    aluno_id: int
    competencia: str
    valor: float
    data_pagamento: date
    meio: Optional[str] = None
    referencia: Optional[str] = None

    @field_validator("competencia")
    @classmethod
    def normalize_comp(cls, v: str) -> str:
        v = v.strip()
        return f"{v}-01" if len(v) == 7 else v

class PaymentCreate(PaymentBase):
    pass

class PaymentOut(BaseModel):
    id: int
    aluno_id: int
    competencia: date
    valor: float
    data_pagamento: date
    meio: Optional[str] = None
    referencia: Optional[str] = None

    class Config:
        from_attributes = True