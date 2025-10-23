
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from app.core.dependencies import get_db, get_current_user
from app.modules.users.models import User
from .models import InviteToken
from .schemas import UserAdminOut, InviteOut

router = APIRouter()

async def get_current_superadmin(
    user: User = Depends(get_current_user),
) -> User:
    if user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user

@router.get("/users", response_model=list[UserAdminOut])
async def list_users_admin(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superadmin),
):
    # Lista todos os usuários não-superadmin (clientes/mentores/equipe)
    res = await db.execute(select(User).where(User.role != "superadmin").order_by(User.created_at.desc()))
    users = res.scalars().all()
    return users

@router.get("/invitations", response_model=list[InviteOut])
async def list_invitations(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superadmin),
):
    res = await db.execute(select(InviteToken).order_by(InviteToken.created_at.desc()))
    return res.scalars().all()

@router.post("/users/{user_id}/authorize", response_model=InviteOut)
async def authorize_user(
    user_id: int,
    admin: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    # Verifica usuário alvo
    res = await db.execute(select(User).where(User.id == user_id))
    target = res.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Cria token
    token = uuid4().hex
    expires = datetime.now(timezone.utc) + timedelta(days=7)

    stmt = insert(InviteToken).values(
        token=token,
        email_hint=target.email,
        mentor_name_hint=target.nome,
        created_by_user_id=admin.id,
        expires_at=expires,
    ).returning(InviteToken)
    created = (await db.execute(stmt)).scalar_one()
    await db.commit()
    return created
