from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Integer, ForeignKey, UniqueConstraint, TIMESTAMP, text
from app.db.base import Base

class AsaasConfig(Base):
    __tablename__ = "asaas_config"
    __table_args__ = (UniqueConstraint("mentor_id", name="uq_asaas_config_mentor"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # antes: String(128)
    api_key: Mapped[str] = mapped_column(String(512), nullable=False)
    sandbox: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"), onupdate=text("NOW()"))