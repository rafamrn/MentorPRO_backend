from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete, or_
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

    # ✅ Marca o usuário como ativo
    target.is_active = True
    await db.commit()
    await db.refresh(target)

    # Cria token (mantido caso você queira continuar enviando)
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

@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    admin: User = Depends(get_current_superadmin),
    db: AsyncSession = Depends(get_db),
):
    # 1) Localiza o alvo
    res = await db.execute(select(User).where(User.id == user_id))
    target = res.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # 2) Regras de segurança
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir a si mesmo.")
    if target.role == "superadmin":
        raise HTTPException(status_code=403, detail="Não é permitido excluir um superadmin.")

    # 3) Limpa convites relacionados (evita FK e sujeira)
    await db.execute(
        delete(InviteToken).where(
            or_(
                InviteToken.used_by_user_id == target.id,
                InviteToken.email_hint == target.email,
            )
        )
    )

    # 4) Exclui o usuário
    await db.delete(target)
    await db.commit()

    return Response(status_code=204)
