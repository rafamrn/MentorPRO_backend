# app/api/v1/routes/metrics.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date
from decimal import Decimal
from app.core.dependencies import get_db, get_current_user
from app.modules.students.models import Student
from app.modules.products.models import Product

router = APIRouter()

@router.get("/mrr")
async def get_mrr(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),  # precisa ter .id (mentor_id)
):
    """
    MRR estimado = soma dos valores dos produtos recorrentes (mensal/recorrente)
    para alunos ATIVOS do mentor atual. 
    Não inclui planos trimestrais/semestrais/anuais pagos à vista.
    """
    # Durações consideradas "recorrentes":
    DURACOES_RECORRENTES = ["recorrente", "mensal"]

    # Join por nome do plano (Student.plano == Product.nome) e pelo mentor_id
    stmt = (
        select(
            func.coalesce(func.sum(Product.valor), 0),
            func.count()
        )
        .select_from(Student)
        .join(
            Product,
            (Product.nome == Student.plano) & (Product.mentor_id == Student.mentor_id),
            isouter=False,
        )
        .where(
            Student.mentor_id == current_user.id,
            Student.status == "Ativo",
            Product.duracao.in_(DURACOES_RECORRENTES),
            # Se quiser garantir que a assinatura ainda está válida:
            # (Student.data_fim.is_(None)) | (Student.data_fim >= date.today())
        )
    )

    res = await db.execute(stmt)
    total_valor, qtd_assinantes = res.one_or_none() or (0, 0)

    # Garantir tipos serializáveis
    if isinstance(total_valor, Decimal):
        total_valor = float(total_valor)

    return {"mrr": float(total_valor or 0), "assinantes": int(qtd_assinantes or 0)}