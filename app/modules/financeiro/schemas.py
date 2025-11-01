# app/modules/financeiro/schemas.py
from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_serializer

# ---- Saída de um pagamento (compat com FE) ----
class PagamentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mentor_id: int

    # Compat FE: expor "aluno_id" lendo de student_id
    aluno_id: int = Field(validation_alias="student_id", serialization_alias="aluno_id")

    competencia: str
    due_date: Optional[date] = None

    # Valor como float (mesmo que no banco seja Decimal)
    valor: Optional[float] = None

    status_pagamento: str
    source: Optional[str] = None

    # Compat FE: expor "referencia" lendo de external_reference
    referencia: Optional[str] = Field(
        default=None,
        validation_alias="external_reference",
        serialization_alias="referencia"
    )

    asaas_payment_id: Optional[str] = None

    # Compat FE: expor "data_pagamento" lendo de paid_at
    data_pagamento: Optional[datetime] = Field(
        default=None,
        validation_alias="paid_at",
        serialization_alias="data_pagamento"
    )

    # Compat FE: expor "meio" lendo de method
    meio: Optional[str] = Field(
        default=None,
        validation_alias="method",
        serialization_alias="meio"
    )

    created_at: datetime
    updated_at: datetime

    @field_serializer("valor")
    def _serialize_valor(self, v: Optional[float | Decimal], _info):
        if v is None:
            return None
        try:
            return float(v)
        except Exception:
            return v

# ---- Atualização parcial (use no PUT) ----
class PagamentoUpdate(BaseModel):
    # nomes do modelo
    competencia: Optional[str] = None
    due_date: Optional[date] = None
    valor: Optional[float] = None
    status_pagamento: Optional[str] = None
    source: Optional[str] = None
    external_reference: Optional[str] = None
    asaas_payment_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    method: Optional[str] = None

# ---- Lista paginada ----
class PagamentoListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    items: List[PagamentoOut]
    total: int

# ---- sync competências ----
class SyncCompetenciasIn(BaseModel):
    ate_competencia: Optional[str] = None  # "YYYY-MM"
    valor: Optional[float] = None
    overwrite_due_date: Optional[date] = None

class SyncCompetenciasOut(BaseModel):
    created: int
    skipped: int
