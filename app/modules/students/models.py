from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Date, Boolean, ForeignKey, TIMESTAMP, text
from app.db.base import Base  # ou Base do seu projeto

class Student(Base):
    __tablename__ = "alunos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Dono do registro = mentor (usuário logado)
    mentor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    nome: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cpf: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # manter nomes que o FE já usa
    concurso: Mapped[str | None] = mapped_column(String(255), nullable=True)   # FE envia “concurso”
    plano: Mapped[str | None] = mapped_column(String(255), nullable=True)
    coach: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="Ativo")

    dia_vencimento: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_compra: Mapped[Date | None] = mapped_column(Date, nullable=True)
    data_fim: Mapped[Date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("NOW()")
    )
