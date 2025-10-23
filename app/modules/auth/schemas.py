from typing import Optional
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: Optional[str] = None  # opcional mesmo


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
