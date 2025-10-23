from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.dependencies import get_db, get_tenant
from app.modules.tenants.models import Tenant
from .models import Student
from .schemas import StudentCreate, StudentOut

router = APIRouter()

@router.get("", response_model=list[StudentOut])
async def list_students(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    res = await db.execute(select(Student).where(Student.tenant_id == tenant.id))
    return res.scalars().all()

@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(
    payload: StudentCreate,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
):
    # simples: um aluno por email por tenant (regra básica)
    stmt = select(Student).where(Student.tenant_id == tenant.id, Student.email == payload.email)
    if (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Student with this email already exists for this tenant")
    student = Student(
        tenant_id=tenant.id,
        nome=payload.nome,
        email=payload.email,
        documento=payload.documento,
    )
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return student