# app/modules/students/crud.py
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .models import Student  # seu modelo

async def get_student_or_404(db: AsyncSession, tenant_id: int, student_id: int) -> Student:
    stmt = select(Student).where(Student.id == student_id, Student.tenant_id == tenant_id)
    res = await db.execute(stmt)
    student = res.scalar_one_or_none()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aluno {student_id} não encontrado para este tenant."
        )
    return student
