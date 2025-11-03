# app/modules/financeiro/schemas.py
from __future__ import annotations
from typing import Optional, List
from datetime import date, datetime  # date é o que será usado
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_serializer

class PagamentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mentor_id: int
    aluno_id: int = Field(validation_alias="student_id", serialization_alias="aluno_id")
    competencia: str
    due_date: Optional[date] = None
    valor: Optional[float] = None
    status_pagamento: str
    source: Optional[str] = None
    referencia: Optional[str] = Field(
        default=None,
        validation_alias="external_reference",
        serialization_alias="referencia",
    )
    asaas_payment_id: Optional[str] = None

    # ⬇⬇⬇ trocado para date
    data_pagamento: Optional[date] = Field(
        default=None,
        validation_alias="paid_at",
        serialization_alias="data_pagamento",
    )

    meio: Optional[str] = Field(
        default=None,
        validation_alias="method",
        serialization_alias="meio",
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

class PagamentoUpdate(BaseModel):
    competencia: Optional[str] = None
    due_date: Optional[date] = None
    valor: Optional[float] = None
    status_pagamento: Optional[str] = None
    source: Optional[str] = None
    external_reference: Optional[str] = None
    asaas_payment_id: Optional[str] = None

    # ⬇⬇⬇ trocado para date
    paid_at: Optional[date] = None

    method: Optional[str] = None

class PagamentoListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    items: List[PagamentoOut]
    total: int

class SyncCompetenciasIn(BaseModel):
    ate_competencia: Optional[str] = None
    valor: Optional[float] = None
    overwrite_due_date: Optional[date] = None

class SyncCompetenciasOut(BaseModel):
    created: int
    skipped: int
