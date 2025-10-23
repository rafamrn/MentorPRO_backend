from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.dependencies import get_db
from app.core.security import hash_password
from app.modules.users.models import User
from app.modules.tenants.models import Tenant
from .schemas import PublicRegisterIn, PublicRegisterOut

router = APIRouter(prefix="/public", tags=["Public"])

@router.post("/register", response_model=PublicRegisterOut, status_code=201)
async def public_register(body: PublicRegisterIn, db: AsyncSession = Depends(get_db)):
    email = body.email.lower().strip()

    # e-mail único
    exists = await db.execute(select(User).where(User.email == email))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    # garante tenant "global" (ou ajuste para a sua regra)
    t = (await db.execute(select(Tenant).where(Tenant.id == "global"))).scalar_one_or_none()
    if not t:
        t = Tenant(id="global", nome_fantasia="MentorPro Global")
        db.add(t)
        await db.commit()
        await db.refresh(t)

    u = User(
        tenant_id=t.id,
        nome=body.name.strip(),
        email=email,
        senha_hash=hash_password(body.password),
        role="mentor",        # perfil padrão do cadastro
        is_active=False,      # fica pendente até o admin aprovar
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)

    return PublicRegisterOut(
        id=u.id,
        name=u.nome,
        email=u.email,
        is_active=u.is_active,
        created_at=u.created_at.isoformat(),
    )
