from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, ForeignKey
from app.db.base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="mentor")  # mentor | staff | superadmin
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
