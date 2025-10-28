from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.modules.atividades import schemas as s
from app.modules.atividades.models import ActivityStage, Activity

router = APIRouter()

# =============== Defaults (seed) ===============
DEFAULT_STAGES = [
    {"nome": "A Fazer",        "cor": "border-l-warning",   "ordem": 1},
    {"nome": "Em Andamento",   "cor": "border-l-primary",   "ordem": 2},
    {"nome": "Revisão",        "cor": "border-l-secondary", "ordem": 3},
    {"nome": "Concluído",      "cor": "border-l-success",   "ordem": 4},
]

# =============== Helpers ===============
async def _assert_stage_owner(db: AsyncSession, stage_id: str, owner_id: int) -> ActivityStage:
    st = await db.scalar(
        select(ActivityStage).where(ActivityStage.id == stage_id, ActivityStage.owner_id == owner_id)
    )
    if not st:
        raise HTTPException(status_code=404, detail="Funil não encontrado")
    return st

async def _compact_order_indices(db: AsyncSession, owner_id: int, stage_id: str) -> None:
    """
    Reindexa as atividades de uma coluna para 0..n-1 (mantendo a ordem atual).
    Útil após exclusões ou movimentos.
    """
    rows = (await db.execute(
        select(Activity).where(
            Activity.owner_id == owner_id,
            Activity.stage_id == stage_id
        ).order_by(Activity.order_index.asc(), Activity.id.asc())
    )).scalars().all()

    for idx, row in enumerate(rows):
        if row.order_index != idx:
            row.order_index = idx
            db.add(row)

async def _next_order_index(db: AsyncSession, owner_id: int, stage_id: str) -> int:
    max_idx = await db.scalar(
        select(func.max(Activity.order_index)).where(
            Activity.owner_id == owner_id,
            Activity.stage_id == stage_id
        )
    )
    return 0 if max_idx is None else int(max_idx) + 1

async def _insert_at_index(
    db: AsyncSession,
    owner_id: int,
    stage_id: str,
    insert_index: int,
    skip_activity_id: Optional[int] = None
) -> None:
    """
    Abre espaço na coluna a partir de 'insert_index', empurrando os demais (+1).
    skip_activity_id: não incrementa o item que está sendo movido.
    """
    rows = (await db.execute(
        select(Activity).where(
            Activity.owner_id == owner_id,
            Activity.stage_id == stage_id,
            Activity.id != (skip_activity_id or -1),
            Activity.order_index >= insert_index
        ).order_by(Activity.order_index.desc())
    )).scalars().all()

    # Atualiza de trás pra frente para evitar conflitos únicos temporários
    for row in rows:
        row.order_index = row.order_index + 1
        db.add(row)

# =============== FUNIS (STAGES) ===============
@router.get("/funis", response_model=List[s.StageOut])
async def list_funis(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = (await db.execute(
        select(ActivityStage)
        .where(ActivityStage.owner_id == current_user.id)
        .order_by(ActivityStage.ordem.asc().nulls_last(), ActivityStage.created_at.asc())
    )).scalars().all()

    # Seed automático para o mentor, se vazio
    if not rows:
        for st in DEFAULT_STAGES:
            db.add(ActivityStage(owner_id=current_user.id, **st))
        await db.commit()
        rows = (await db.execute(
            select(ActivityStage)
            .where(ActivityStage.owner_id == current_user.id)
            .order_by(ActivityStage.ordem.asc().nulls_last(), ActivityStage.created_at.asc())
        )).scalars().all()

    return rows

@router.post("/funis", response_model=s.StageOut, status_code=status.HTTP_201_CREATED)
async def create_funil(
    payload: s.StageCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    stage = ActivityStage(
        owner_id=current_user.id,
        nome=payload.nome,
        cor=payload.cor,
        ordem=payload.ordem,
    )
    db.add(stage)
    await db.commit()
    await db.refresh(stage)
    return stage

@router.patch("/funis/{stage_id}", response_model=s.StageOut)
async def update_funil(
    stage_id: str,
    payload: s.StageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    st = await _assert_stage_owner(db, stage_id, current_user.id)

    if payload.nome is not None:
        st.nome = payload.nome
    if payload.cor is not None:
        st.cor = payload.cor
    if payload.ordem is not None:
        st.ordem = payload.ordem

    db.add(st)
    await db.commit()
    await db.refresh(st)
    return st

@router.delete("/funis/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_funil(
    stage_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    st = await _assert_stage_owner(db, stage_id, current_user.id)
    await db.delete(st)  # cascade apaga atividades
    await db.commit()
    return None

# =============== ATIVIDADES (ITEMS) ===============
# IMPORTANTE: sem "/" no path raiz para evitar 307 ➜ 404
@router.get("", response_model=List[s.ActivityOut])
async def list_atividades(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = (await db.execute(
        select(Activity)
        .where(Activity.owner_id == current_user.id)
        .order_by(Activity.stage_id.asc(), Activity.order_index.asc())
    )).scalars().all()
    return rows

@router.post("", response_model=s.ActivityOut, status_code=status.HTTP_201_CREATED)
async def create_atividade(
    payload: s.ActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # valida stage
    await _assert_stage_owner(db, payload.stage_id, current_user.id)

    # order_index vai para o final da coluna
    oi = await _next_order_index(db, current_user.id, payload.stage_id)

    item = Activity(
        owner_id=current_user.id,
        stage_id=payload.stage_id,
        order_index=oi,
        titulo=payload.titulo,
        descricao=payload.descricao,
        prioridade=payload.prioridade,
        responsavel=payload.responsavel,
        data_vencimento=payload.dataVencimento,
        tags=payload.tags or [],
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.patch("/{atividade_id}", response_model=s.ActivityOut)
async def update_atividade(
    atividade_id: int,
    payload: s.ActivityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = await db.scalar(
        select(Activity).where(Activity.id == atividade_id, Activity.owner_id == current_user.id)
    )
    if not item:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")

    # Conteúdo básico
    if payload.titulo is not None:
        item.titulo = payload.titulo
    if payload.descricao is not None:
        item.descricao = payload.descricao
    if payload.prioridade is not None:
        item.prioridade = payload.prioridade
    if payload.responsavel is not None:
        item.responsavel = payload.responsavel
    if payload.dataVencimento is not None:
        item.data_vencimento = payload.dataVencimento
    if payload.tags is not None:
        item.tags = payload.tags

    # Movimentação / ordenação
    new_stage_id = payload.stage_id or item.stage_id
    new_index = payload.order_index

    # Caso 1: mudando de coluna
    if payload.stage_id and payload.stage_id != item.stage_id:
        # valida novo stage do owner
        await _assert_stage_owner(db, payload.stage_id, current_user.id)

        old_stage = item.stage_id

        # "Move" item de coluna: primeiro compacta a antiga
        item.stage_id = payload.stage_id
        await _compact_order_indices(db, current_user.id, old_stage)

        # Define posição na nova coluna
        if new_index is None:
            new_index = await _next_order_index(db, current_user.id, new_stage_id)
        else:
            await _insert_at_index(db, current_user.id, new_stage_id, new_index, skip_activity_id=item.id)

        item.order_index = new_index

    # Caso 2: mesma coluna, apenas reordena
    elif new_index is not None:
        if new_index < 0:
            new_index = 0

        rows = (await db.execute(
            select(Activity).where(
                Activity.owner_id == current_user.id,
                Activity.stage_id == item.stage_id
            ).order_by(Activity.order_index.asc(), Activity.id.asc())
        )).scalars().all()

        rows = [r for r in rows if r.id != item.id]
        if new_index > len(rows):
            new_index = len(rows)
        rows.insert(new_index, item)

        for idx, r in enumerate(rows):
            r.order_index = idx
            db.add(r)

    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.delete("/{atividade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_atividade(
    atividade_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = await db.scalar(
        select(Activity).where(Activity.id == atividade_id, Activity.owner_id == current_user.id)
    )
    if not item:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")

    stage_id = item.stage_id
    await db.delete(item)
    await db.commit()

    # Compacta índices após exclusão
    await _compact_order_indices(db, current_user.id, stage_id)
    await db.commit()
    return None
