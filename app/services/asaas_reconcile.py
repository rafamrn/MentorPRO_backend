# app/services/asaas_reconcile.py
from datetime import datetime, date, timezone
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import select
from app.modules.financeiro.models import Pagamento  # ajuste o import ao seu projeto

PAID_STATUSES = {"RECEIVED", "RECEIVED_IN_CASH", "CONFIRMED", "DUNNING_RECEIVED"}

def _parse_date_yyyy_mm_dd(v: Optional[str]) -> Optional[date]:
    """
    Asaas devolve 'YYYY-MM-DD' em clientPaymentDate/paymentDate/confirmedDate.
    Converte com segurança para date (na ausência, retorna None).
    """
    if not v:
        return None
    try:
        # aceita "YYYY-MM-DD" ou ISO completo
        if len(v) == 10:
            return datetime.strptime(v, "%Y-%m-%d").date()
        # ISO completo -> pega só a parte de data
        return datetime.fromisoformat(v).date()
    except Exception:
        return None

def reconcile_pagamento_from_asaas(
    db: Session,
    student_id: int,
    competencia: str,             # "YYYY-MM"
    asaas_payment: Dict[str, Any] # item do Asaas (um dict do array "data")
) -> Optional[Pagamento]:
    """
    Se o pagamento vier como 'pago' no Asaas, atualiza/insere na nossa tabela `pagamentos`:
      - status_pagamento = "pago"
      - paid_at = clientPaymentDate (fallback: paymentDate, confirmedDate)
      - asaas_payment_id, method/billingType, valor, source = "asaas"
    Retorna o objeto `Pagamento` alterado (ou None se não houver nada a atualizar).
    """
    status = str(asaas_payment.get("status", "")).upper()
    if status not in PAID_STATUSES:
        return None

    paid_at = (
        _parse_date_yyyy_mm_dd(asaas_payment.get("clientPaymentDate"))
        or _parse_date_yyyy_mm_dd(asaas_payment.get("paymentDate"))
        or _parse_date_yyyy_mm_dd(asaas_payment.get("confirmedDate"))
    )

    valor = asaas_payment.get("value")
    asaas_payment_id = asaas_payment.get("id")
    metodo = (asaas_payment.get("billingType") or "").lower()  # "BOLETO" -> "boleto"
    if metodo == "boleto":
        metodo = "boleto"
    elif metodo == "PIX":
        metodo = "pix"
    elif metodo == "CREDIT_CARD":
        metodo = "cartao"

    # Busca por chave natural (student_id + competencia). Garanta um índice/unique nessa dupla.
    stmt = select(Pagamento).where(
        Pagamento.aluno_id == student_id,
        Pagamento.competencia == competencia
    )
    pag = db.execute(stmt).scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if pag is None:
        # cria registro já como PAGO
        pag = Pagamento(
            aluno_id=student_id,
            competencia=competencia,          # "YYYY-MM"
            valor=valor,
            status_pagamento="pago",
            paid_at=paid_at,
            method=metodo or None,
            source="asaas",
            asaas_payment_id=asaas_payment_id,
            external_reference=asaas_payment.get("externalReference"),
            created_at=now,
            updated_at=now,
        )
        db.add(pag)
    else:
        # atualiza registro existente
        pag.valor = valor if valor is not None else pag.valor
        pag.status_pagamento = "pago"
        pag.paid_at = paid_at or pag.paid_at
        pag.method = (metodo or pag.method)
        pag.source = "asaas"
        pag.asaas_payment_id = asaas_payment_id or pag.asaas_payment_id
        if not getattr(pag, "external_reference", None):
            pag.external_reference = asaas_payment.get("externalReference")
        pag.updated_at = now

    db.flush()
    return pag
