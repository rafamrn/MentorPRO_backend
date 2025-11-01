from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Date, ForeignKey, Boolean
from app.db.base import Base, TimestampMixin

class Student(Base, TimestampMixin):
    __tablename__ = "alunos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mentor_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    telefone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cpf: Mapped[str | None] = mapped_column(String(20), nullable=True)

    concurso: Mapped[str | None] = mapped_column(String(200), nullable=True)
    plano: Mapped[str | None] = mapped_column(String(200), nullable=True)
    coach: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True, default="Ativo")

    product_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dia_vencimento: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_compra: Mapped[Date | None] = mapped_column(Date, nullable=True)
    data_fim: Mapped[Date | None] = mapped_column(Date, nullable=True)

    asaas_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ✅ NOVO CAMPO
    metodo_pagamento: Mapped[str | None] = mapped_column(String(30), nullable=True)
