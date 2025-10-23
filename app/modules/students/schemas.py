from pydantic import BaseModel, EmailStr

class StudentCreate(BaseModel):
    nome: str
    email: EmailStr
    documento: str | None = None

class StudentOut(BaseModel):
    id: int
    tenant_id: str
    nome: str
    email: EmailStr
    documento: str | None = None
    asaas_customer_id: str | None = None

    class Config:
        from_attributes = True