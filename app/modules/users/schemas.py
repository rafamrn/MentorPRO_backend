from pydantic import BaseModel, EmailStr

class UserOut(BaseModel):
    id: int
    tenant_id: str
    nome: str
    email: EmailStr
    role: str
    is_active: bool
    class Config:
        from_attributes = True

class UserCreateStaff(BaseModel):
    nome: str
    email: EmailStr
    password: str
