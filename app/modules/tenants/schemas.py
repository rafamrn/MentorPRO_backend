from pydantic import BaseModel, Field

class TenantCreate(BaseModel):
    id: str = Field(description="UUID ou string única do tenant")
    nome_fantasia: str
    cnpj: str | None = None
    plano: str | None = None
    asaas_api_key: str | None = None

class TenantOut(BaseModel):
    id: str
    nome_fantasia: str
    cnpj: str | None
    plano: str | None

    class Config:
        from_attributes = True