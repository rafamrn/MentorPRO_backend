# app/modules/equipe/router.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.core.dependencies import get_db
from .models import TeamMember
from .schemas import TeamMemberCreate, TeamMemberUpdate, TeamMemberOut

router = APIRouter()

def get_tenant_id_from_header(request: Request) -> str:
    tenant_id = request.headers.get("X-Client-Id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="X-Client-Id header é obrigatório")
    return tenant_id

@router.get("", response_model=list[TeamMemberOut])
async def list_members(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_from_header),
):
    res = await db.execute(select(TeamMember).where(TeamMember.tenant_id == tenant_id).order_by(TeamMember.nome))
    return res.scalars().all()

@router.post("", response_model=TeamMemberOut, status_code=status.HTTP_201_CREATED)
async def create_member(
    payload: TeamMemberCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_from_header),
):
    member = TeamMember(tenant_id=tenant_id, **payload.model_dump())
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member

@router.put("/{member_id}", response_model=TeamMemberOut)
async def update_member(
    member_id: int,
    payload: TeamMemberUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_from_header),
):
    res = await db.execute(select(TeamMember).where(TeamMember.id == member_id, TeamMember.tenant_id == tenant_id))
    member = res.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Membro não encontrado")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(member, k, v)

    await db.commit()
    await db.refresh(member)
    return member

@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    member_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id_from_header),
):
    q = select(TeamMember).where(TeamMember.id == member_id, TeamMember.tenant_id == tenant_id)
    res = await db.execute(q)
    member = res.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Membro não encontrado")

    await db.delete(member)
    await db.commit()
