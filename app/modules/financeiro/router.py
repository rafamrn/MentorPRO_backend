from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import date, datetime
import calendar as _cal

from app.core.dependencies import get_db, get_current_user
from app.modules.users.models import User
from app.modules.products.models import Product
from app.modules.students.models import Student  # ajuste: caminho do seu Student
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
    # tente campos comuns
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
# app/modules/financeiro/router.py

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
    # aluno
    r = await db.execute(
        select(Student).where(and_(Student.id == student_id, Student.mentor_id == me.id))
    )
    st = r.scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    if not st.data_compra:
        raise HTTPException(status_code=400, detail="Aluno sem data_compra definida")

    # monta intervalo de competências
    start_ym = f"{st.data_compra.year:04d}-{st.data_compra.month:02d}"
    end_ym = body.ate_competencia or _prev_year_month()

    # valor padrão
    default_valor = body.valor
    if default_valor is None:
        default_valor = await _produto_valor_for_student(db, st)

    created, skipped = 0, 0
    for ym in _iter_ym(start_ym, end_ym):
        # já existe?
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
