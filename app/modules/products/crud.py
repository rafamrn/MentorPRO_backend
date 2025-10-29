# app/modules/products/crud.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from .models import Product

async def get_product_or_404(db: AsyncSession, mentor_id: int, product_id: int) -> Product:
    q = await db.execute(
        select(Product).where(Product.id == product_id, Product.mentor_id == mentor_id, Product.ativo == True)
    )
    product = q.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado/ativo.")
    return product

async def get_product_by_name_or_none(db: AsyncSession, mentor_id: int, nome: str) -> Product | None:
    q = await db.execute(
        select(Product).where(Product.nome == nome, Product.mentor_id == mentor_id, Product.ativo == True)
    )
    return q.scalar_one_or_none()
