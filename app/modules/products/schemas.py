# app/modules/products/schemas.py
from pydantic import BaseModel
from typing import Optional

class ProductBase(BaseModel):
    nome: str
    duracao: str
    valor: float
    descricao: Optional[str] = None
    ativo: bool = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    nome: Optional[str] = None
    duracao: Optional[str] = None
    valor: Optional[float] = None
    descricao: Optional[str] = None
    ativo: Optional[bool] = None

class ProductOut(ProductBase):
    id: int
    class Config:
        from_attributes = True
