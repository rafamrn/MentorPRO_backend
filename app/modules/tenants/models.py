from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from app.db.base import Base, TimestampMixin

class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # pode usar UUID str
    nome_fantasia: Mapped[str] = mapped_column(String(200), nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String(20), nullable=True)
    plano: Mapped[str | None] = mapped_column(String(50), nullable=True)
    asaas_api_key: Mapped[str | None] = mapped_column(String(200), nullable=True)