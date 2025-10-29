# app/modules/students/router.py
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, date, timezone
from sqlalchemy import select, delete, and_, func
from typing import List
from app.modules.products.models import Product
from .schemas import RevenueByCreatedOut
from app.core.dependencies import get_db, get_current_user
from app.modules.users.models import User
from .models import Student
from .schemas import (
    StudentOut, StudentCreate, StudentUpdate,
    BulkUpsertItem, BulkDeleteIn, BulkUpsertIn, BulkDeleteOut
)

router = APIRouter()  # <— sem prefixo aqui

# LIST
@router.get("", response_model=list[StudentOut])
async def list_students(
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
    limit: int = Query(1000, le=100000),
    offset: int = 0,
    data_compra_ini: str | None = Query(None, description="YYYY-MM-DD"),
    data_compra_fim: str | None = Query(None, description="YYYY-MM-DD"),
):
    stmt = (
        select(Student)
        .where(Student.mentor_id == me.id)
    )

    # filtros por data_compra (fechando intervalo inclusive)
    from datetime import datetime, date
    if data_compra_ini:
        try:
            d_ini = datetime.strptime(data_compra_ini, "%Y-%m-%d").date()
            stmt = stmt.where(Student.data_compra >= d_ini)
        except ValueError:
            raise HTTPException(status_code=400, detail="data_compra_ini inválida (use YYYY-MM-DD)")
    if data_compra_fim:
        try:
            d_fim = datetime.strptime(data_compra_fim, "%Y-%m-%d").date()
            stmt = stmt.where(Student.data_compra <= d_fim)
        except ValueError:
            raise HTTPException(status_code=400, detail="data_compra_fim inválida (use YYYY-MM-DD)")

    stmt = stmt.order_by(Student.nome.asc()).limit(limit).offset(offset)

    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/created/count")
async def count_created_students(
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
    ini: str = Query(..., description="YYYY-MM-DD"),
    fim: str = Query(..., description="YYYY-MM-DD (inclusive)"),
):
    try:
        dt_ini = datetime.fromisoformat(ini).replace(hour=0, minute=0, second=0, microsecond=0)
        dt_fim = datetime.fromisoformat(fim).replace(hour=23, minute=59, second=59, microsecond=999999)
    except Exception:
        raise HTTPException(status_code=400, detail="Parâmetros ini/fim inválidos. Use YYYY-MM-DD.")

    q = await db.execute(
        select(func.count(Student.id)).where(
            and_(
                Student.mentor_id == me.id,
                Student.created_at >= dt_ini,
                Student.created_at <= dt_fim,
            )
        )
    )
    return {"count": q.scalar_one()}

# CREATE
@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(
    payload: StudentCreate,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    obj = Student(**payload.model_dump(), mentor_id=me.id)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

# UPDATE
@router.put("/{student_id}", response_model=StudentOut)
async def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Student).where(and_(Student.id == student_id, Student.mentor_id == me.id))
    )
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)

    await db.commit()
    await db.refresh(obj)
    return obj

# DELETE (um)
@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Student.id).where(and_(Student.id == student_id, Student.mentor_id == me.id))
    )
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    await db.execute(delete(Student).where(Student.id == student_id))
    await db.commit()
    return

# BULK UPSERT — o FE envia { alunos: [...] } em /students/bulk_upsert (POST)
@router.post("/bulk_upsert", response_model=BulkDeleteOut)  # {"count": n}
async def bulk_upsert(
    inp: BulkUpsertIn,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    created = 0
    for it in inp.alunos:
        obj = Student(**it.model_dump(), mentor_id=me.id)
        db.add(obj)
        created += 1
    await db.commit()
    return {"count": created}

# BULK DELETE — o FE faz DELETE /students/bulk com body { ids: [...] }
@router.delete("/bulk", response_model=BulkDeleteOut)
async def bulk_delete(
    inp: BulkDeleteIn = Body(...),
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    if not inp.ids:
        return {"count": 0}
    stmt = delete(Student).where(and_(Student.mentor_id == me.id, Student.id.in_(inp.ids)))
    res = await db.execute(stmt)
    await db.commit()
    return {"count": res.rowcount or len(inp.ids)}

@router.get("/revenue/purchases", response_model=RevenueByCreatedOut)
async def revenue_by_purchases(
    ini: str,  # YYYY-MM-DD
    fim: str,  # YYYY-MM-DD
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    """
    Soma Product.valor dos alunos cuja data_compra está no intervalo [ini..fim] (inclusive),
    combinando Student.plano == Product.nome e mesmo mentor_id. Produtos inativos não entram.
    """
    # valida datas
    try:
        d_ini = datetime.strptime(ini, "%Y-%m-%d").date()
        d_fim = datetime.strptime(fim, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Datas inválidas. Use YYYY-MM-DD.")

    if d_fim < d_ini:
        raise HTTPException(status_code=400, detail="fim não pode ser menor que ini.")

    # LEFT JOIN para contar alunos mesmo sem produto correspondente; soma ignora NULL
    stmt = (
        select(
            func.coalesce(func.sum(Product.valor), 0).label("total"),
            func.count(Student.id).label("count"),
        )
        .select_from(Student)
        .join(
            Product,
            and_(
                Product.nome == Student.plano,
                Product.mentor_id == Student.mentor_id,
                Product.ativo == True,
            ),
            isouter=True,
        )
        .where(
            and_(
                Student.mentor_id == me.id,
                Student.data_compra.is_not(None),
                Student.data_compra >= d_ini,
                Student.data_compra <= d_fim,
            )
        )
    )

    res = await db.execute(stmt)
    total, count = res.one_or_none() or (0, 0)
    return RevenueByCreatedOut(total=float(total or 0), count=int(count or 0))