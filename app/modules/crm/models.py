# app/modules/crm/models.py
from uuid import uuid4
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Text, Index  # (DateTime/func se quiser timestamps)
from app.db.base import Base

class CRMFunil(Base):
    __tablename__ = "crm_funis"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)  # FK no banco
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    ordem: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_crm_funis_tenant_owner_ordem", "tenant_id", "owner_user_id", "ordem"),
    )


class CRMLead(Base):
    __tablename__ = "crm_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)  # FK no banco

    stage_id: Mapped[str] = mapped_column(String, index=True, nullable=False)  # id do funil
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 🔽 Campos que estavam faltando
    titulo: Mapped[str] = mapped_column(String(150), nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(20), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    estado: Mapped[str | None] = mapped_column(String(2), nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(120), nullable=True)
    planoDesejado: Mapped[str | None] = mapped_column(String(120), nullable=True)
    concursoDesejado: Mapped[str | None] = mapped_column(String(120), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_crm_leads_tenant_owner_stage_idx", "tenant_id", "owner_user_id", "stage_id", "order_index"),
    )
