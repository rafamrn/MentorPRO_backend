from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    Integer,
    String,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.students.models import Student as StudentModel

STATUS_CHOICES = ("pendente", "pago", "atrasado", "cancelado")


class Pagamento(Base):
    __tablename__ = "pagamentos"

    __table_args__ = (
        # 1 competência por aluno/mentor
        UniqueConstraint(
            "mentor_id",
            "student_id",
            "competencia",
            name="uq_pagto_competencia_por_aluno",
        ),
        # guarda só valores conhecidos de status
        CheckConstraint(
            f"status_pagamento in {STATUS_CHOICES}",
            name="ck_pagamento_status_valido",
        ),
        # índices úteis para filtros
        Index("ix_pagto_mentor_student", "mentor_id", "student_id"),
        Index("ix_pagto_external_reference", "external_reference"),
        Index("ix_pagto_asaas_payment_id", "asaas_payment_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    mentor_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)

    student_id: Mapped[int] = mapped_column(
        ForeignKey(f"{StudentModel.__tablename__}.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # "YYYY-MM" (ex.: "2025-08")
    competencia: Mapped[str] = mapped_column(String(7), nullable=False, index=True)

    # vencimento da parcela (se aplicável)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # valor da parcela (Decimal é mais seguro p/ dinheiro)
    valor: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    # status do pagamento
    status_pagamento: Mapped[str] = mapped_column(
        String(16),
        default="pendente",
        nullable=False,
    )

    # origem: "manual" | "asaas"
    source: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # referência externa (ex.: "student:{id}:{YYYY-MM}")
    external_reference: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    # id da cobrança no Asaas
    asaas_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # metadados de quitação
    # >>> ATENÇÃO: agora é Date (não DateTime) para casar com clientPaymentDate/paymentDate
    paid_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    # boleto/cartao/pix/etc.
    method: Mapped[str | None] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # relacionamento (navegação a partir do aluno)
    student = relationship("Student", backref="pagamentos", lazy="joined")
