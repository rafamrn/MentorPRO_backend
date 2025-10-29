# app/api/v1/router.py
from fastapi import APIRouter
from app.modules.tenants.router import router as tenants_router
from app.modules.students.router import router as students_router
from app.modules.webhooks.router import router as webhooks_router
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.public.router import router as public_router
from app.modules.products.router import router as products_router
from app.modules.finance.router import router as finance_router
from app.modules.concursos.router import router as concursos_router
from app.modules.crm.router import router as crm_router
from app.modules.atividades.router import router as atividades_router
from app.modules.metrics.router import router as metrics_router
from app.modules.asaas.router import router as asaas_router
from app.modules.equipe.router import router as equipe_router

api_router = APIRouter()

api_router.include_router(auth_router,    prefix="/auth",    tags=["auth"])
api_router.include_router(tenants_router, prefix="/tenants", tags=["tenants"])
api_router.include_router(users_router,   prefix="/users",   tags=["users"])
api_router.include_router(students_router,prefix="/students",tags=["students"])
api_router.include_router(webhooks_router,prefix="/webhooks",tags=["webhooks"])
api_router.include_router(admin_router,   prefix="/admin",   tags=["admin"])
api_router.include_router(public_router)
api_router.include_router(products_router, prefix="/products", tags=["products"])
api_router.include_router(finance_router, prefix="/financeiro", tags=["financeiro"])
api_router.include_router(concursos_router, prefix="/concursos", tags=["concursos"])
api_router.include_router(crm_router, prefix="/crm", tags=["crm"])
api_router.include_router(atividades_router, prefix="/atividades", tags=["atividades"])
api_router.include_router(metrics_router, prefix="/metrics", tags=["metrics"])
api_router.include_router(asaas_router, prefix="/billing", tags=["Billing/Asaas"])
api_router.include_router(equipe_router, prefix="/equipe", tags=["Equipe"])
