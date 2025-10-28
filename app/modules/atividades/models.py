from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    String,
    Integer,
    Text,
    Date,
    ForeignKey,
    DateTime,
    func,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ARRAY

# Ajuste estes imports conforme seu projeto
from app.db.base import Base
# Se você usa multi-tenant por coluna (tenant_id), você pode adicionar os campos abaixo:
# from sqlalchemy import BigInteger
# from app.modules.users.models import User  # opcional, se quiser relationship


class ActivityStage(Base):
    """
    Coluna (funil) do quadro de atividades de um mentor.
    Escopo por owner_id (usuário autenticado). Se desejar por tenant_id, acrescente o campo.
    """
    __tablename__ = "activity_stages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    owner_id: Mapped[int] = mapped_column(Integer, index=True)  # usuário "mentor" dono
    # tenant_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)

    nome: Mapped[str] = mapped_column(String(120), index=True)
    cor: Mapped[str | None] = mapped_column(String(48), nullable=True)
    ordem: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    atividades: Mapped[list["Activity"]] = relationship(
        "Activity",
        back_populates="stage",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_activity_stages_owner_nome", "owner_id", "nome"),
    )


class Activity(Base):
    """
    Item do quadro (atividade/tarefa).
    """
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(Integer, index=True)  # usuário "mentor" dono
    # tenant_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)

    stage_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("activity_stages.id", ondelete="CASCADE"),
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0, index=True)

    titulo: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Mantemos prioridade como string livre ("Alta" | "Média" | "Baixa") para simplicidade
    prioridade: Mapped[str | None] = mapped_column(String(16), nullable=True)

    responsavel: Mapped[str | None] = mapped_column(String(120), nullable=True)
    data_vencimento: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Supabase é Postgres → ARRAY funciona. Se quiser compatibilidade SQLite, troque por JSON.
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    stage: Mapped["ActivityStage"] = relationship("ActivityStage", back_populates="atividades")

    __table_args__ = (
        Index("ix_activities_owner_stage_order", "owner_id", "stage_id", "order_index"),
    )
