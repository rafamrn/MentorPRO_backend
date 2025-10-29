from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
import httpx

from app.core.dependencies import get_db, get_current_user
from app.modules.users.models import User
from app.modules.asaas.models import AsaasConfig
from app.modules.asaas.schemas import AsaasConfigIn, AsaasConfigOut, HealthOut

router = APIRouter()

# ---------- Helpers ----------
async def _get_config_for_mentor(db: AsyncSession, mentor_id: int) -> AsaasConfig | None:
    q = await db.execute(select(AsaasConfig).where(AsaasConfig.mentor_id == mentor_id))
    return q.scalar_one_or_none()

def _asaas_base_url(sandbox: bool) -> str:
    return "https://sandbox.asaas.com/api/v3" if sandbox else "https://www.asaas.com/api/v3"

def _asaas_headers(api_key: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "access_token": api_key,
    }

# ---------- Endpoints ----------
@router.get("/config", response_model=AsaasConfigOut)
async def get_config(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cfg = await _get_config_for_mentor(db, user.id)
    if not cfg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AsaasConfig não encontrado para este mentor")
    return AsaasConfigOut(api_key=cfg.api_key, sandbox=cfg.sandbox)

@router.post("/config", response_model=dict)
async def upsert_config(
    payload: AsaasConfigIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cfg = await _get_config_for_mentor(db, user.id)
    if cfg:
        await db.execute(
            update(AsaasConfig)
            .where(AsaasConfig.id == cfg.id)
            .values(api_key=payload.api_key, sandbox=payload.sandbox)
        )
    else:
        await db.execute(
            insert(AsaasConfig).values(
                mentor_id=user.id,
                api_key=payload.api_key,
                sandbox=payload.sandbox,
            )
        )
    await db.commit()
    return {"ok": True}

@router.get("/health", response_model=HealthOut)
async def health_check(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cfg = await _get_config_for_mentor(db, user.id)
    if not cfg:
        return HealthOut(ok=False, message="Credenciais não configuradas")

    base_url = _asaas_base_url(cfg.sandbox)
    try:
        async with httpx.AsyncClient(timeout=20.0, headers=_asaas_headers(cfg.api_key)) as client:
            r = await client.get(f"{base_url}/customers", params={"limit": 1})
            r.raise_for_status()
        return HealthOut(ok=True, message="Conexão com Asaas OK")
    except httpx.HTTPStatusError as e:
        return HealthOut(ok=False, message=f"HTTP {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        return HealthOut(ok=False, message=str(e))
