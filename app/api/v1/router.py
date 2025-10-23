from fastapi import APIRouter
from app.modules.tenants.router import router as tenants_router
from app.modules.students.router import router as students_router
from app.modules.webhooks.router import router as webhooks_router
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(tenants_router, prefix="/tenants", tags=["tenants"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(students_router, prefix="/students", tags=["students"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])

api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
