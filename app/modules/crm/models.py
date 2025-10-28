from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
    func,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.base import Base


class CRMPipeline(Base):
    __tablename__ = "crm_pipelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mentor_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    color: Mapped[str] = mapped_column(String(50), nullable=False, default="border-l-primary")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=True, onupdate=func.now()
    )

    leads: Mapped[list["CRMLead"]] = relationship(
        "CRMLead",
        back_populates="pipeline",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="CRMLead.position.asc()",
    )

    __table_args__ = (
        # Nome único por mentor
        Index(
            "ix_crm_pipeline_unique_mentor_name",
            "mentor_id",
            "name",
            unique=True,
        ),
        Index("ix_crm_pipeline_order", "mentor_id", "position"),
    )


class CRMLead(Base):
    __tablename__ = "crm_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mentor_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    pipeline_id: Mapped[int] = mapped_column(
        ForeignKey("crm_pipelines.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Dados do lead
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)  # nome do aluno
    cpf: Mapped[str | None] = mapped_column(String(20), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    estado: Mapped[str | None] = mapped_column(String(2), nullable=True)  # UF
    cidade: Mapped[str | None] = mapped_column(String(120), nullable=True)
    plano_desejado: Mapped[str | None] = mapped_column(String(120), nullable=True)
    concurso_desejado: Mapped[str | None] = mapped_column(String(160), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Ordenação dentro do pipeline
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=True, onupdate=func.now()
    )

    pipeline: Mapped[CRMPipeline] = relationship("CRMPipeline", back_populates="leads")

    __table_args__ = (
        Index("ix_crm_lead_pipeline_order", "mentor_id", "pipeline_id", "position"),
    )
