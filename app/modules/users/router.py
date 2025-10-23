from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_db, get_current_user, get_tenant
from app.modules.tenants.models import Tenant
from .models import User
from .schemas import UserOut, UserCreateStaff
from app.core.security import hash_password

router = APIRouter()

@router.get("", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
    user: User = Depends(get_current_user),
):
    stmt = select(User).where(User.tenant_id == tenant.id)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/staff", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_staff_user(
    payload: UserCreateStaff,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
    user: User = Depends(get_current_user),
):
    # somente mentor ou superadmin cria staff
    if user.role not in ("mentor", "superadmin"):
        raise HTTPException(status_code=403, detail="Sem permissão")
    # unique por tenant + email
    exists = await db.execute(select(User).where(User.tenant_id == tenant.id, User.email == payload.email))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="E-mail já existe nesse tenant")
    u = User(
        tenant_id=tenant.id,
        nome=payload.nome,
        email=payload.email,
        senha_hash=hash_password(payload.password),
        role="staff",
        is_active=True,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u
