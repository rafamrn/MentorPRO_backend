# app/modules/products/models.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Boolean, ForeignKey, TIMESTAMP, text, Numeric
from app.db.base import Base

class Product(Base):
    __tablename__ = "produtos"  # tabela (pode manter em pt-BR)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Dono (mentor logado)
    mentor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    nome: Mapped[str] = mapped_column(String(255))
    descricao: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    duracao: Mapped[str] = mapped_column(String(50))  # "recorrente" | "mensal" | "anual" | ...
    valor: Mapped[float] = mapped_column(Numeric(10, 2))  # Decimal(10,2)

    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("NOW()")
    )
