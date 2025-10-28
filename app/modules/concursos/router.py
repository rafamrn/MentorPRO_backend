from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from app.modules.concursos.models import Concurso
from app.modules.concursos.schemas import ConcursoOut, ConcursoCreate, ConcursoUpdate
from app.modules.users.models import User
from app.core.security import decode_token  # se precisar em deps
from app.core.dependencies import get_db, get_current_user

router = APIRouter()

@router.get("", response_model=List[ConcursoOut])
async def list_concursos(
    q: Optional[str] = Query(None),
    uf: Optional[str] = Query(None, max_length=2),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conds = [Concurso.mentor_id == user.id]
    if uf:
        conds.append(Concurso.uf == uf)
    if status:
        conds.append(Concurso.status == status)
    if q:
        like = f"%{q}%"
        conds.append(or_(
            Concurso.titulo.ilike(like),
            Concurso.orgao.ilike(like),
            Concurso.cidade.ilike(like),
            Concurso.banca.ilike(like),
            Concurso.cargo.ilike(like),
            Concurso.escolaridade.ilike(like),
            Concurso.uf.ilike(like),
        ))

    stmt = (
        select(Concurso)
        .where(*conds)
        .order_by(Concurso.prova_data.asc().nulls_last())
        .limit(limit)
        .offset(offset)
    )
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/{concurso_id}", response_model=ConcursoOut)
async def get_concurso(
    concurso_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Concurso).where(
        Concurso.id == concurso_id,
        Concurso.mentor_id == user.id,
    )
    res = await db.execute(stmt)
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Concurso não encontrado")
    return obj

@router.post("", response_model=ConcursoOut)
async def create_concurso(
    payload: ConcursoCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    obj = Concurso(
        **payload.model_dump(),
        mentor_id=user.id,
        owner_id=int(user.id),  # se usar
    )
    db.add(obj)
    try:
        await db.flush()
    except IntegrityError as e:
        await db.rollback()
        # opcional: verifique o nome da sua unique (ajuste se diferente)
        if "ix_concursos_unique_mentor_titulo_prova" in str(e.orig):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um concurso com esse título e data de prova para este mentor.",
            )
        raise
    await db.commit()
    await db.refresh(obj)
    return obj

@router.put("/{concurso_id}", response_model=ConcursoOut)
async def update_concurso(
    concurso_id: int,
    payload: ConcursoUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Busca restrita ao mentor
    stmt = select(Concurso).where(
        Concurso.id == concurso_id,
        Concurso.mentor_id == user.id,
    )
    res = await db.execute(stmt)
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Concurso não encontrado")

    data = payload.model_dump(exclude_unset=True)
    # se vier tags=None, ignore; se vier lista, aplica
    if "tags" in data and data["tags"] is None:
        data.pop("tags")

    for k, v in data.items():
        setattr(obj, k, v)

    await db.flush()
    await db.refresh(obj)
    return obj

@router.delete("/{concurso_id}")
async def delete_concurso(
    concurso_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Concurso).where(
        Concurso.id == concurso_id,
        Concurso.mentor_id == user.id,
    )
    res = await db.execute(stmt)
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Concurso não encontrado")

    await db.delete(obj)
    await db.commit()
    return {"ok": True}
