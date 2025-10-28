from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Numeric, Date, ForeignKey, TIMESTAMP, text
from app.db.base import Base

class Payment(Base):
    __tablename__ = "pagamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id", ondelete="CASCADE"), index=True)

    # YYYY-MM guardado como dia 1 (Date) ou string ISO "YYYY-MM-01"
    competencia: Mapped[Date] = mapped_column(Date)
    valor: Mapped[float] = mapped_column(Numeric(10, 2))
    data_pagamento: Mapped[Date] = mapped_column(Date)
    meio: Mapped[str | None] = mapped_column(String(50), nullable=True)
    referencia: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("NOW()")
    )
