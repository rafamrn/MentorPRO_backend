# app/crud/crud_asaas_config.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.asaas.models import AsaasConfig

async def get_asaas_config_by_mentor(db: AsyncSession, mentor_id: int) -> AsaasConfig | None:
    q = select(AsaasConfig).where(AsaasConfig.mentor_id == mentor_id)
    res = await db.execute(q)
    return res.scalar_one_or_none()
