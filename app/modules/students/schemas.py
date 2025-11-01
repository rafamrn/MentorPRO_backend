from __future__ import annotations
from pydantic import BaseModel, EmailStr, ConfigDict, Field, model_validator, field_validator
from datetime import date
from typing import Optional, List, Literal, Union, Dict, Any
import re

MetodoPagamento = Literal["Boleto", "Cartão de Crédito", "PIX"]

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
    metodo_pagamento: Optional[MetodoPagamento] = None

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
    metodo_pagamento: Optional[MetodoPagamento] = None

class StudentOut(StudentBase):
    id: int
    asaas_customer_id: str | None = None
    model_config = ConfigDict(from_attributes=True)

# Bulk
class BulkUpsertItem(StudentCreate):
    pass

class BulkUpsertIn(BaseModel):
    alunos: List[BulkUpsertItem]

class BulkDeleteIn(BaseModel):
    ids: List[int]

class BulkDeleteOut(BaseModel):
    count: int

class RevenueByCreatedOut(BaseModel):
    total: float
    count: int
    model_config = ConfigDict(from_attributes=True)

class ChargeCreateIn(BaseModel):
    value: float | str
    dueDate: str
    metodo_pagamento: Optional[str] = None
    description: Optional[str] = None
    # ✅ aceitar um dicionário metadata (usaremos metadata["competencia"] = "YYYY-MM")
    metadata: Optional[Dict[str, Any]] = None

class ChargeCreateOut(BaseModel):
    id: str
    status: Optional[str] = None
    billingType: Optional[str] = None
    invoiceUrl: Optional[str] = None
    bankSlipUrl: Optional[str] = None
    pixQrCodeId: Optional[str] = None
    raw: Optional[dict] = None

# ================= Cobrança =================

def _coerce_value_text_to_float(txt: str) -> float:
    s = re.sub(r"[^\d,\.]", "", txt or "")
    if not s:
        raise ValueError("value vazio")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    return float(s)
