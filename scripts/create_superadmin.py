
import asyncio
from getpass import getpass
from sqlalchemy import select, insert
from app.db.session import AsyncSessionLocal
from app.modules.tenants.models import Tenant
from app.modules.users.models import User
from app.core.security import hash_password

async def main():
    tenant_id = input("Tenant id for superadmin (default: global): ").strip() or "global"
    tenant_name = input("Tenant nome_fantasia (default: MentorPro Global): ").strip() or "MentorPro Global"
    async with AsyncSessionLocal() as db:
        # ensure tenant
        res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        t = res.scalar_one_or_none()
        if not t:
            t = Tenant(id=tenant_id, nome_fantasia=tenant_name)
            db.add(t)
            await db.commit()
            await db.refresh(t)
            print(f"Created tenant {t.id}")
        # user
        nome = input("Admin nome: ").strip() or "Super Admin"
        email = input("Admin email: ").strip().lower()
        password = getpass("Admin password: ")
        res = await db.execute(select(User).where(User.email == email))
        if res.scalar_one_or_none():
            print("User already exists")
            return
        u = User(
            tenant_id=t.id,
            nome=nome,
            email=email,
            senha_hash=hash_password(password),
            role="superadmin",
            is_active=True,
        )
        db.add(u)
        await db.commit()
        await db.refresh(u)
        print(f"Superadmin created: {u.id} ({u.email}) tenant={u.tenant_id}")

if __name__ == "__main__":
    asyncio.run(main())
