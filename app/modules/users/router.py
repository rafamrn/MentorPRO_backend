from __future__ import annotations

from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_db, get_current_user, get_tenant
from app.modules.tenants.models import Tenant
from app.core.security import hash_password
from .models import User
from .schemas import (
    UserOut,
    UserCreateMember,
    UserUpdateMember,
)

router = APIRouter()


def _status_to_active(status_text: Optional[str]) -> bool:
    # convenção simples: "Inativo" => False; qualquer outra (Ativo/Férias/None) => True
    if status_text is None:
        return True
    return status_text != "Inativo"


@router.get("", response_model=List[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
    user: User = Depends(get_current_user),
):
    # lista todos do tenant (mentor + staff + outros perfis se houver)
    stmt = select(User).where(User.tenant_id == tenant.id)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateMember,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
    user: User = Depends(get_current_user),
):
    # somente mentor ou superadmin criam membros
    if user.role not in ("mentor", "superadmin"):
        raise HTTPException(status_code=403, detail="Sem permissão")

    # unique por tenant + email
    exists = await db.execute(
        select(User).where(User.tenant_id == tenant.id, User.email == payload.email)
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="E-mail já existe neste tenant")

    # role padrão para equipe criada pela UI é "staff"
    role = "staff"

    u = User(
        tenant_id=tenant.id,
        nome=payload.nome,
        email=payload.email,
        senha_hash=hash_password(payload.password),
        role=role,
        perfil=payload.perfil,                      # opcional
        status_text=payload.status,                 # opcional: "Ativo" | "Inativo" | "Férias"
        data_admissao=payload.data_admissao,        # opcional: date
        is_active=_status_to_active(payload.status),
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


# Mantém compatibilidade com o endpoint antigo
@router.post("/staff", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_staff_user_legacy(
    payload: UserCreateMember,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
    user: User = Depends(get_current_user),
):
    return await create_user(payload, db, tenant, user)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdateMember,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
    user: User = Depends(get_current_user),
):
    # somente mentor ou superadmin editam
    if user.role not in ("mentor", "superadmin"):
        raise HTTPException(status_code=403, detail="Sem permissão")

    q = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant.id)
    )
    u = q.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # campos editáveis
    if payload.nome is not None:
        u.nome = payload.nome
    if payload.email is not None:
        # checa conflito de e-mail
        if payload.email != u.email:
            exists = await db.execute(
                select(User).where(User.tenant_id == tenant.id, User.email == payload.email)
            )
            if exists.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="E-mail já existe neste tenant")
        u.email = payload.email

    if payload.perfil is not None:
        u.perfil = payload.perfil
    if payload.status is not None:
        u.status_text = payload.status
        u.is_active = _status_to_active(payload.status)
    if payload.data_admissao is not None:
        u.data_admissao = payload.data_admissao

    # segurança extra: papel só pode ser mudado por superadmin (se você quiser expor no futuro)
    # if payload.role is not None:
    #     if user.role != "superadmin":
        #         raise HTTPException(status_code=403, detail="Apenas superadmin altera role")
    #     u.role = payload.role

    await db.commit()
    await db.refresh(u)
    return u


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_tenant),
    user: User = Depends(get_current_user),
):
    if user.role not in ("mentor", "superadmin"):
        raise HTTPException(status_code=403, detail="Sem permissão")

    q = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant.id)
    )
    u = q.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    await db.delete(u)
    await db.commit()
    return None


@router.get("/me", response_model=UserOut)
async def users_me(user: User = Depends(get_current_user)):
    return user
