from typing import AsyncIterator, Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.security import OAuth2PasswordBearer

from app.db.session import AsyncSessionLocal
from app.modules.tenants.models import Tenant
from app.modules.users.models import User
from app.core.config import settings
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")  # só referência

async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = decode_token(token, settings.SECRET_KEY)
        user_id = int(payload.get("sub"))
        tenant_id = payload.get("tenant_id")
        if not user_id or not tenant_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    q = await db.execute(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    user = q.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user

async def get_tenant(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Tenant:
    stmt = select(Tenant).where(Tenant.id == user.tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
