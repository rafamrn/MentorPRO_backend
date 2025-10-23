# app/modules/products/router.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update, delete
from app.core.dependencies import get_db, get_current_user
from app.modules.users.models import User
from .models import Product
from .schemas import ProductOut, ProductCreate, ProductUpdate

router = APIRouter()  # será incluído com prefix "/products"

# LIST
@router.get("", response_model=list[ProductOut])
async def list_products(
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
    limit: int = Query(1000, le=100000),
    offset: int = 0,
):
    stmt = (
        select(Product)
        .where(Product.mentor_id == me.id)
        .order_by(Product.nome.asc())
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(stmt)
    return res.scalars().all()

# CREATE
@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    # troque model_dict() -> model_dump()
    obj = Product(**payload.model_dump(), mentor_id=me.id)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

# UPDATE
@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    res = await db.execute(select(Product).where(and_(Product.id == product_id, Product.mentor_id == me.id)))
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    # troque model_dict(exclude_unset=True) -> model_dump(exclude_unset=True)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)

    await db.commit()
    await db.refresh(obj)
    return obj

# TOGGLE STATUS
@router.post("/{product_id}/toggle", response_model=ProductOut)
async def toggle_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    res = await db.execute(select(Product).where(and_(Product.id == product_id, Product.mentor_id == me.id)))
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    obj.ativo = not obj.ativo
    await db.commit()
    await db.refresh(obj)
    return obj

# DELETE
@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    res = await db.execute(select(Product.id).where(and_(Product.id == product_id, Product.mentor_id == me.id)))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    await db.execute(delete(Product).where(Product.id == product_id))
    await db.commit()
    return
