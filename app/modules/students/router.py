# app/modules/students/router.py
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func
from typing import List

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
    status: str | None = Query(None, description="Filtra pelo status do aluno (ex.: 'Ativo', 'Inativo')"),
 ):
    stmt = (
        select(Student)
        .where(Student.mentor_id == me.id)
        .order_by(Student.nome.asc())
        .limit(limit)
        .offset(offset)
    )
    if status:
        stmt = stmt.where(Student.status == status)
    res = await db.execute(stmt)
    return res.scalars().all()  # [] quando vazio

@router.get("/active/count")
async def count_active_students(
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    q = await db.execute(
        select(func.count(Student.id)).where(
            and_(Student.mentor_id == me.id, Student.status == "Ativo")
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
