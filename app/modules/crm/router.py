# app/modules/crm/router.py
from __future__ import annotations
from typing import List, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.modules.crm.models import CRMFunil, CRMLead
from app.modules.crm.schemas import (
    FunilCreate, FunilOut, FunilUpdate,
    LeadCreate, LeadOut, LeadUpdate
)

router = APIRouter()

# -------- Helpers --------
def is_staff(user) -> bool:
    return getattr(user, "role", None) in {"admin", "staff"}

async def _ensure_funil_belongs(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    funil_id: str,
    can_see_all: bool
) -> CRMFunil:
    q = select(CRMFunil).where(CRMFunil.id == funil_id, CRMFunil.tenant_id == tenant_id)
    if not can_see_all:
        q = q.where(CRMFunil.owner_user_id == user_id)
    res = await db.execute(q)
    funil = res.scalar_one_or_none()
    if not funil:
        raise HTTPException(status_code=404, detail="Funil não encontrado")
    return funil

# -------- FUNIS --------
@router.get("/funis", response_model=List[FunilOut])
async def list_funis(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    q = (
        select(CRMFunil)
        .where(CRMFunil.tenant_id == user.tenant_id)
        .order_by(CRMFunil.ordem.nulls_last(), CRMFunil.id)
    )
    if not is_staff(user):
        q = q.where(CRMFunil.owner_user_id == user.id)

    res = await db.execute(q)
    return res.scalars().all()

@router.post("/funis", response_model=FunilOut, status_code=status.HTTP_201_CREATED)
async def create_funil(
    payload: FunilCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    res = await db.execute(
        select(func.max(CRMFunil.ordem)).where(
            CRMFunil.tenant_id == user.tenant_id,
            CRMFunil.owner_user_id == user.id,
        )
    )
    next_ord = (res.scalar() or 0) + 1

    funil = CRMFunil(
        tenant_id=user.tenant_id,
        owner_user_id=user.id,
        nome=payload.nome.strip(),
        ordem=payload.ordem if payload.ordem is not None else next_ord,
    )
    db.add(funil)
    await db.flush()
    await db.commit()
    await db.refresh(funil)
    return funil

@router.patch("/funis/{funil_id}")
async def update_funil(
    funil_id: str,
    payload: FunilUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    funil = await _ensure_funil_belongs(db, user.tenant_id, user.id, funil_id, can_see_all=is_staff(user))

    if payload.nome is not None:
        new_name = payload.nome.strip()
        if not new_name:
            raise HTTPException(status_code=400, detail="Nome não pode ser vazio")
        funil.nome = new_name

    if payload.ordem is not None:
        funil.ordem = payload.ordem

    await db.flush()
    await db.commit()
    return {"ok": True}

@router.delete("/funis/{funil_id}", status_code=204)
async def delete_funil(
    funil_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    funil = await _ensure_funil_belongs(db, user.tenant_id, user.id, funil_id, can_see_all=is_staff(user))

    # apaga leads do mesmo dono naquele funil
    await db.execute(
        text("DELETE FROM crm_leads WHERE tenant_id = :t AND owner_user_id = :u AND stage_id = :s"),
        {"t": user.tenant_id, "u": user.id, "s": funil.id},
    )
    await db.delete(funil)
    await db.flush()
    await db.commit()
    return None

# -------- LEADS --------
@router.get("/leads", response_model=List[LeadOut])
async def list_leads(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    q = (
        select(CRMLead)
        .where(CRMLead.tenant_id == user.tenant_id)
        .order_by(CRMLead.stage_id, CRMLead.order_index, CRMLead.id)
    )
    if not is_staff(user):
        q = q.where(CRMLead.owner_user_id == user.id)

    res = await db.execute(q)
    return res.scalars().all()

@router.post("/leads", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    # só permite criar no funil do próprio usuário (ou staff)
    await _ensure_funil_belongs(db, user.tenant_id, user.id, payload.stage_id, can_see_all=is_staff(user))

    # último índice na coluna do próprio dono
    q = await db.execute(
        select(func.max(CRMLead.order_index)).where(
            CRMLead.tenant_id == user.tenant_id,
            CRMLead.owner_user_id == user.id,
            CRMLead.stage_id == payload.stage_id,
        )
    )
    idx = (q.scalar() or -1) + 1

    lead = CRMLead(
        tenant_id=user.tenant_id,
        owner_user_id=user.id,
        stage_id=payload.stage_id,
        order_index=idx,
        titulo=payload.titulo.strip(),
        cpf=payload.cpf,
        telefone=payload.telefone,
        email=payload.email,
        estado=payload.estado,
        cidade=payload.cidade,
        planoDesejado=payload.planoDesejado,
        concursoDesejado=payload.concursoDesejado,
        descricao=payload.descricao,
    )
    db.add(lead)
    await db.flush()
    await db.commit()
    await db.refresh(lead)
    return lead

@router.patch("/leads/{lead_id}")
async def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    q = select(CRMLead).where(CRMLead.id == lead_id, CRMLead.tenant_id == user.tenant_id)
    if not is_staff(user):
        q = q.where(CRMLead.owner_user_id == user.id)
    res = await db.execute(q)
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    # updates simples
    for f in ["titulo","cpf","telefone","email","estado","cidade","planoDesejado","concursoDesejado","descricao"]:
        val = getattr(payload, f, None)
        if val is not None:
            setattr(lead, f, val.strip() if isinstance(val, str) else val)

    move_stage = payload.stage_id
    target_index = payload.order_index

    # helper: reindex da coluna (por dono)
    async def reindex(stage: str, owner_id: str):
        r = await db.execute(
            select(CRMLead)
            .where(
                CRMLead.tenant_id == user.tenant_id,
                CRMLead.owner_user_id == owner_id,
                CRMLead.stage_id == stage,
            )
            .order_by(CRMLead.order_index, CRMLead.id)
        )
        arr = list(r.scalars().all())
        for i, l in enumerate(arr):
            l.order_index = i

    # se mover de coluna, garantir que a coluna destino pertence ao mesmo dono (ou staff)
    if move_stage is not None:
        await _ensure_funil_belongs(db, user.tenant_id, user.id, move_stage, can_see_all=is_staff(user))

    owner_for_ops = lead.owner_user_id  # staff mantém o dono do lead

    if move_stage is None and target_index is not None:
        await reindex(lead.stage_id, owner_for_ops)
        r = await db.execute(
            select(CRMLead)
            .where(
                CRMLead.tenant_id == user.tenant_id,
                CRMLead.owner_user_id == owner_for_ops,
                CRMLead.stage_id == lead.stage_id,
            )
            .order_by(CRMLead.order_index, CRMLead.id)
        )
        lst = [l for l in r.scalars().all() if l.id != lead.id]
        insert_at = max(0, min(target_index, len(lst)))
        lst.insert(insert_at, lead)
        for i, l in enumerate(lst):
            l.order_index = i

    if move_stage is not None:
        old_stage = lead.stage_id
        await reindex(old_stage, owner_for_ops)

        # source (remove)
        rsrc = await db.execute(
            select(CRMLead)
            .where(
                CRMLead.tenant_id == user.tenant_id,
                CRMLead.owner_user_id == owner_for_ops,
                CRMLead.stage_id == old_stage,
            )
            .order_by(CRMLead.order_index, CRMLead.id)
        )
        src = [l for l in rsrc.scalars().all() if l.id != lead.id]
        for i, l in enumerate(src):
            l.order_index = i

        # destino (insere)
        rdst = await db.execute(
            select(CRMLead)
            .where(
                CRMLead.tenant_id == user.tenant_id,
                CRMLead.owner_user_id == owner_for_ops,
                CRMLead.stage_id == move_stage,
            )
            .order_by(CRMLead.order_index, CRMLead.id)
        )
        dst = list(rdst.scalars().all())
        insert_at = target_index if (target_index is not None and 0 <= target_index <= len(dst)) else len(dst)

        lead.stage_id = move_stage
        dst.insert(insert_at, lead)
        for i, l in enumerate(dst):
            l.order_index = i

    await db.flush()
    await db.commit()
    return {"ok": True}

@router.delete("/leads/{lead_id}", status_code=204)
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    q = select(CRMLead).where(CRMLead.id == lead_id, CRMLead.tenant_id == user.tenant_id)
    if not is_staff(user):
        q = q.where(CRMLead.owner_user_id == user.id)
    res = await db.execute(q)
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado")

    stage = lead.stage_id
    owner_for_ops = lead.owner_user_id

    await db.delete(lead)
    await db.flush()

    # reindex da coluna do mesmo dono
    await db.execute(
        text("""
        WITH ordered AS (
          SELECT id, ROW_NUMBER() OVER (ORDER BY order_index, id) - 1 AS rn
          FROM crm_leads
          WHERE tenant_id = :t AND owner_user_id = :u AND stage_id = :s
        )
        UPDATE crm_leads l
        SET order_index = o.rn
        FROM ordered o
        WHERE l.id = o.id
        """),
        {"t": user.tenant_id, "u": owner_for_ops, "s": stage},
    )
    await db.commit()
    return None
