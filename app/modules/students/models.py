from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Date, ForeignKey, TIMESTAMP, text
from app.db.base import Base

class Student(Base):
    __tablename__ = "alunos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    nome: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cpf: Mapped[str | None] = mapped_column(String(20), nullable=True)

    concurso: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plano: Mapped[str | None] = mapped_column(String(255), nullable=True)
    coach: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="Ativo")

    product_id: Mapped[int | None] = mapped_column(ForeignKey("produtos.id", ondelete="SET NULL"), index=True, nullable=True)
    dia_vencimento: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_compra: Mapped[Date | None] = mapped_column(Date, nullable=True)
    data_fim: Mapped[Date | None] = mapped_column(Date, nullable=True)

    asaas_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    created_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
