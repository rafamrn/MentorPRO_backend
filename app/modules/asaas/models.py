# app/models/asaas_config.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Integer, ForeignKey, UniqueConstraint
from app.db.base import Base

class AsaasConfig(Base):
    __tablename__ = "asaas_config"
    __table_args__ = (
        UniqueConstraint("mentor_id", name="uq_asaas_config_mentor"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    api_key: Mapped[str] = mapped_column(String(200))
    sandbox: Mapped[bool] = mapped_column(Boolean, default=True)
