from pydantic import BaseModel, EmailStr

class PublicRegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str  # hash no backend

class PublicRegisterOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_active: bool
    created_at: str
