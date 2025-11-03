# app/modules/financeiro/router.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import date, datetime
import calendar as _cal
from pydantic import BaseModel, Field

from app.core.dependencies import get_db, get_current_user
from app.modules.users.models import User
from app.modules.products.models import Product
from app.modules.students.models import Student
from .models import Pagamento
from .schemas import (
    PagamentoOut, PagamentoUpdate, PagamentoListOut,
    SyncCompetenciasIn, SyncCompetenciasOut
)

router = APIRouter(tags=["Financeiro - Pagamentos"])

# ---------- helpers ----------
def _ym_to_year_month(ym: str) -> tuple[int, int]:
    y, m = ym.split("-")
    yi = int(y); mi = int(m)
    if mi < 1 or mi > 12:
        raise ValueError("Mês inválido em competencia (use YYYY-MM).")
    return yi, mi

def _normalize_competencia(raw: str) -> str:
    """Aceita 'YYYY-MM' ou 'YYYY-MM-01' e retorna 'YYYY-MM'."""
    s = raw.strip()
    if len(s) >= 7:
        s = s[:7]
    _ym_to_year_month(s)  # valida
    return s

def _prev_year_month(today: date | None = None) -> str:
    d = today or date.today()
    y = d.year; m = d.month
    m -= 1
    if m == 0:
        y -= 1; m = 12
    return f"{y:04d}-{m:02d}"

def _iter_ym(start_ym: str, end_ym: str):
    sy, sm = _ym_to_year_month(start_ym)
    ey, em = _ym_to_year_month(end_ym)
    y, m = sy, sm
    while (y < ey) or (y == ey and m <= em):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m == 13:
            m = 1
            y += 1

async def _produto_valor_for_student(db: AsyncSession, st: Student) -> float | None:
    if not st.plano:
        return None
    res = await db.execute(
        select(Product).where(
            and_(Product.nome == st.plano, Product.mentor_id == st.mentor_id, Product.ativo == True)
        )
    )
    prod = res.scalar_one_or_none()
    if not prod:
        return None
    for k in ("valor", "price", "preco"):
        v = getattr(prod, k, None)
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    return None

def _due_for(competencia: str, st) -> date | None:
    """Calcula um due_date básico no 'dia_vencimento' do aluno, clampado ao fim do mês."""
    dia = None
    try:
        dia = int(getattr(st, "dia_vencimento", None) or 0)
    except Exception:
        dia = None
    if not dia or dia < 1 or dia > 31:
        return None
    y, m = _ym_to_year_month(competencia)
    last = _cal.monthrange(y, m)[1]
    d = min(dia, last)
    return date(y, m, d)

# ---------- rotas ----------
@router.get("", response_model=PagamentoListOut)
async def list_pagamentos(
    student_id: int | None = Query(None),
    competencia: str | None = Query(None, description="YYYY-MM"),
    status_pagamento: str | None = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = 0,

    # aliases para o FE
    start: str | None = Query(None, alias="start"),
    end: str | None = Query(None, alias="end"),
    aluno_id: int | None = Query(None, alias="aluno_id"),

    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    _student_id = aluno_id if aluno_id is not None else student_id

    stmt = select(Pagamento).where(Pagamento.mentor_id == me.id)

    if _student_id:
        stmt = stmt.where(Pagamento.student_id == _student_id)

    if competencia:
        stmt = stmt.where(Pagamento.competencia == competencia)

    # intervalo YYYY-MM
    if start and end:
        stmt = stmt.where(Pagamento.competencia >= start, Pagamento.competencia <= end)
    elif start:
        stmt = stmt.where(Pagamento.competencia >= start)
    elif end:
        stmt = stmt.where(Pagamento.competencia <= end)

    if status_pagamento:
        stmt = stmt.where(Pagamento.status_pagamento == status_pagamento)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(Pagamento.competencia.asc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    items_orm = res.scalars().all()

    items = [PagamentoOut.model_validate(obj) for obj in items_orm]
    return PagamentoListOut(items=items, total=int(total or 0))


@router.post("/sync/{student_id}", response_model=SyncCompetenciasOut)
async def sync_competencias_for_student(
    student_id: int,
    body: SyncCompetenciasIn = Body(default=SyncCompetenciasIn()),
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    """
    Gera competências 'pendentes' desde a data_compra do aluno até 'ate_competencia' (default: mês anterior).
    - Se já existir a competência (mentor_id, student_id, competencia), não recria.
    - due_date: usa overwrite_due_date (se enviado) OU o dia_vencimento do aluno (clamp no fim do mês).
    - valor: usa body.valor (se enviado) OU tenta descobrir pelo Product vinculado ao plano do aluno.
    """
    r = await db.execute(
        select(Student).where(and_(Student.id == student_id, Student.mentor_id == me.id))
    )
    st = r.scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    if not st.data_compra:
        raise HTTPException(status_code=400, detail="Aluno sem data_compra definida")

    start_ym = f"{st.data_compra.year:04d}-{st.data_compra.month:02d}"
    end_ym = body.ate_competencia or _prev_year_month()

    default_valor = body.valor
    if default_valor is None:
        default_valor = await _produto_valor_for_student(db, st)

    created, skipped = 0, 0
    for ym in _iter_ym(start_ym, end_ym):
        exists = await db.scalar(
            select(func.count(Pagamento.id)).where(
                and_(
                    Pagamento.mentor_id == me.id,
                    Pagamento.student_id == st.id,
                    Pagamento.competencia == ym,
                )
            )
        )
        if exists:
            skipped += 1
            continue

        due = body.overwrite_due_date or _due_for(ym, st)
        ext = f"student:{st.id}:{ym}"

        db.add(Pagamento(
            mentor_id=me.id,
            student_id=st.id,
            competencia=ym,
            due_date=due,
            valor=default_valor,
            status_pagamento="pendente",
            source="manual",
            external_reference=ext,
        ))
        created += 1

    await db.commit()
    return SyncCompetenciasOut(created=created, skipped=skipped)

# ---------- marcar como pago ----------
class PagamentoMarkPaidIn(BaseModel):
    aluno_id: int = Field(..., gt=0)
    competencia: str  # "YYYY-MM" ou "YYYY-MM-01"
    valor: float = Field(..., gt=0)
    data_pagamento: date = Field(..., description="YYYY-MM-DD")
    meio: str | None = None
    referencia: str | None = None

# Suporte a AMBOS caminhos:
# - POST ""  (quando o router é montado em "/financeiro/pagamentos")
# - POST "/pagamentos" (quando o router é montado em "/financeiro")
@router.post("", response_model=PagamentoOut, status_code=status.HTTP_201_CREATED)
@router.post("/pagamentos", response_model=PagamentoOut, status_code=status.HTTP_201_CREATED)
async def mark_paid_upsert(
    body: PagamentoMarkPaidIn,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    ym = _normalize_competencia(body.competencia)

    r = await db.execute(
        select(Student).where(and_(Student.id == body.aluno_id, Student.mentor_id == me.id))
    )
    st = r.scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    existing_q = select(Pagamento).where(
        and_(
            Pagamento.mentor_id == me.id,
            Pagamento.student_id == body.aluno_id,
            Pagamento.competencia == ym,
        )
    )
    res = await db.execute(existing_q)
    existing = res.scalar_one_or_none()

    if existing:
        existing.valor = body.valor
        existing.status_pagamento = "pago"
        existing.paid_at = body.data_pagamento
        existing.method = body.meio
        if body.referencia:
            existing.external_reference = body.referencia
        existing.source = existing.source or "manual"
        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        return PagamentoOut.model_validate(existing)

    due = _due_for(ym, st)
    novo = Pagamento(
        mentor_id=me.id,
        student_id=body.aluno_id,
        competencia=ym,
        due_date=due,
        valor=body.valor,
        status_pagamento="pago",
        source="manual",
        external_reference=body.referencia,
        paid_at=body.data_pagamento,
        method=body.meio,
    )
    db.add(novo)
    await db.commit()
    await db.refresh(novo)
    return PagamentoOut.model_validate(novo)

# ---------- desfazer (DELETE by aluno/competencia) ----------
@router.delete("/by-aluno/{aluno_id}/{competencia}")
@router.delete("/pagamentos/by-aluno/{aluno_id}/{competencia}")  # alias caso o prefixo seja apenas "/financeiro"
async def delete_pagamento_by_aluno_competencia(
    aluno_id: int = Path(..., gt=0),
    competencia: str = Path(..., description="YYYY-MM ou YYYY-MM-01"),
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    ym = _normalize_competencia(competencia)
    q = select(Pagamento).where(
        and_(
            Pagamento.mentor_id == me.id,
            Pagamento.student_id == aluno_id,
            Pagamento.competencia == ym,
        )
    )
    res = await db.execute(q)
    row = res.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    await db.delete(row)
    await db.commit()
    return {"ok": True}
