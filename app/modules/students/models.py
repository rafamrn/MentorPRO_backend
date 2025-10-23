from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey
from app.db.base import Base, TimestampMixin

class Student(Base, TimestampMixin):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    documento: Mapped[str | None] = mapped_column(String(32), nullable=True)
    asaas_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)