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