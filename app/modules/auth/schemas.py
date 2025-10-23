from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str
    tenant_id: str  # identifica o mentor no login

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
