from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.dependencies import get_db
from app.core.security import verify_password, create_access_token
from app.modules.users.models import User
from app.modules.tenants.models import Tenant
from .schemas import LoginRequest, TokenOut

router = APIRouter()

@router.post("/login", response_model=TokenOut)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    # valida tenant
    t = await db.execute(select(Tenant).where(Tenant.id == payload.tenant_id))
    tenant = t.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant inválido")

    # procura usuário
    q = await db.execute(select(User).where(User.tenant_id == tenant.id, User.email == payload.email))
    user = q.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuário inativo")

    token = create_access_token(
        {"sub": str(user.id), "tenant_id": tenant.id, "role": user.role},
        expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        secret_key=settings.SECRET_KEY,
    )
    return TokenOut(access_token=token)

@router.get("/me")
async def me(user: User = Depends(lambda: None)):
    # /me real virá via get_current_user em dependencies (ver abaixo)
    return {"detail": "Use GET /auth/me via get_current_user (ver dependencies)."}
