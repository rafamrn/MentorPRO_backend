from __future__ import annotations
from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: int
    tenant_id: str
    nome: str
    email: EmailStr
    role: str
    is_active: bool
    # campos usados na UI de equipe
    perfil: Optional[str] = None
    status_text: Optional[str] = None     # "Ativo" | "Inativo" | "Férias"
    data_admissao: Optional[date] = None

    class Config:
        from_attributes = True


class UserCreateMember(BaseModel):
    nome: str
    email: EmailStr
    password: str
    # opcionais da UI
    perfil: Optional[str] = None
    status: Optional[str] = None          # "Ativo" | "Inativo" | "Férias"
    data_admissao: Optional[date] = None


class UserUpdateMember(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    perfil: Optional[str] = None
    status: Optional[str] = None          # "Ativo" | "Inativo" | "Férias"
    data_admissao: Optional[date] = None
    # role: Optional[str] = None          # se algum dia quiser expor
