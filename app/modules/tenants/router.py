from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.dependencies import get_db
from .models import Tenant
from .schemas import TenantCreate, TenantOut

router = APIRouter()

@router.get("", response_model=list[TenantOut])
async def list_tenants(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Tenant))
    return res.scalars().all()

@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
async def create_tenant(payload: TenantCreate, db: AsyncSession = Depends(get_db)):
    # id explícito para facilitar header X-Client-Id no frontend
    exists = await db.execute(select(Tenant).where(Tenant.id == payload.id))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Tenant id already exists")
    tenant = Tenant(
        id=payload.id,
        nome_fantasia=payload.nome_fantasia,
        cnpj=payload.cnpj,
        plano=payload.plano,
        asaas_api_key=payload.asaas_api_key,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant

@router.put("/{tenant_id}", response_model=TenantOut)
async def update_tenant(tenant_id: str, payload: TenantCreate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    t.nome_fantasia = payload.nome_fantasia
    t.cnpj = payload.cnpj
    t.plano = payload.plano
    t.asaas_api_key = payload.asaas_api_key
    await db.commit(); await db.refresh(t); return t

@router.delete("/{tenant_id}", status_code=204)
async def delete_tenant(tenant_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await db.delete(t); await db.commit(); return
