from fastapi import APIRouter, Depends, Query, HTTPException, Body, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func
from datetime import datetime
from typing import List, Optional

from app.core.dependencies import get_db, get_current_user
from app.modules.users.models import User
from app.modules.students.models import Student
from .models import Payment
from .schemas import PaymentOut, PaymentCreate

router = APIRouter(prefix="/pagamentos", tags=["financeiro"])

def _to_date_yyyy_mm(v: str) -> datetime.date:
    v = v.strip()
    if len(v) == 7: v = f"{v}-01"
    return datetime.strptime(v, "%Y-%m-%d").date()

# LIST ?start=YYYY-MM&end=YYYY-MM&aluno_id=?
@router.get("", response_model=List[PaymentOut])
async def list_payments(
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    aluno_id: Optional[int] = Query(None),
):
    stmt = select(Payment).where(Payment.mentor_id == me.id)

    if aluno_id:
        stmt = stmt.where(Payment.aluno_id == aluno_id)

    if start:
        stmt = stmt.where(Payment.competencia >= _to_date_yyyy_mm(start))
    if end:
        stmt = stmt.where(Payment.competencia <= _to_date_yyyy_mm(end))

    stmt = stmt.order_by(Payment.competencia.asc(), Payment.data_pagamento.asc())
    res = await db.execute(stmt)
    return res.scalars().all()

# CREATE
@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    # garante ownership do aluno
    s = await db.execute(select(Student.id).where(
        and_(Student.id == payload.aluno_id, Student.mentor_id == me.id)
    ))
    if not s.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    obj = Payment(
        mentor_id=me.id,
        aluno_id=payload.aluno_id,
        competencia=_to_date_yyyy_mm(payload.competencia),
        valor=payload.valor,
        data_pagamento=payload.data_pagamento,
        meio=payload.meio,
        referencia=payload.referencia,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

# DELETE (um por chave aluno_id+competencia)
@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    aluno_id: int = Query(...),
    competencia: str = Query(...),  # "YYYY-MM"
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    comp = _to_date_yyyy_mm(competencia)

    # delete restrito ao mentor
    stmt = delete(Payment).where(and_(
        Payment.mentor_id == me.id,
        Payment.aluno_id == aluno_id,
        Payment.competencia == comp
    ))
    res = await db.execute(stmt)
    await db.commit()
    if (res.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    return
