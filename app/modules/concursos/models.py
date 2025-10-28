# app/modules/concursos/models.py
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Date, Integer, Numeric, Boolean, func
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base
from sqlalchemy.sql import text as sqltext
from sqlalchemy.dialects.postgresql import ARRAY

class Concurso(Base):
    __tablename__ = "concursos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    titulo: Mapped[str] = mapped_column(Text, nullable=False)
    orgao: Mapped[str | None] = mapped_column(Text)
    uf: Mapped[str | None] = mapped_column(String(2))          # <- aqui
    cidade: Mapped[str | None] = mapped_column(Text)
    banca: Mapped[str | None] = mapped_column(Text)
    cargo: Mapped[str | None] = mapped_column(Text)
    escolaridade: Mapped[str | None] = mapped_column(Text)
    vagas: Mapped[int | None] = mapped_column(Integer)
    salario: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    modalidade: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="Previsto")
    tags: Mapped[list[str] | None] = mapped_column(JSONB, default=list)

    edital_url: Mapped[str | None] = mapped_column(Text)
    inscricao_inicio: Mapped[date | None] = mapped_column(Date)
    inscricao_fim: Mapped[date | None] = mapped_column(Date)
    prova_data: Mapped[date | None] = mapped_column(Date)
    tags: Mapped[list[str]] = mapped_column(
ARRAY(String), nullable=False, server_default=sqltext("'{}'::text[]")
    )

    observacoes: Mapped[str | None] = mapped_column(Text)
    destaque: Mapped[bool] = mapped_column(Boolean, default=False)

    mentor_id: Mapped[int | None] = mapped_column(Integer)     # alinha com user.id int
    owner_id: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now())
