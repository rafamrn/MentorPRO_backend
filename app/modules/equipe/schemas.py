# app/modules/equipe/schemas.py
from pydantic import BaseModel, EmailStr
from datetime import date

class TeamMemberBase(BaseModel):
    nome: str
    email: EmailStr
    perfil: str
    status: str = "Ativo"
    alunos_ativos: int = 0
    data_admissao: date | None = None

class TeamMemberCreate(TeamMemberBase):
    pass

class TeamMemberUpdate(BaseModel):
    nome: str | None = None
    email: EmailStr | None = None
    perfil: str | None = None
    status: str | None = None
    alunos_ativos: int | None = None
    data_admissao: date | None = None

class TeamMemberOut(TeamMemberBase):
    id: int
    class Config:
        from_attributes = True
