from __future__ import annotations

from typing import List, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user, get_tenant
from app.modules.users.models import User
from app.modules.tenants.models import Tenant

from .models import CRMLead, CRMPipeline
from .schemas import (
    CRMLeadCreate,
    CRMLeadUpdate,
    CRMLeadOut,
    CRMLeadMove,
    CRMPipelineCreate,
    CRMPipelineUpdate,
    CRMPipelineOut,
    CRMBoardOut,
    CRMStatsOut,
)

router = APIRouter()


# ------------------------ helpers ------------------------
async def _get_first_pipeline(db: AsyncSession, mentor_id: int) -> Optional[CRMPipeline]:
    q = await db.execute(
        select(CRMPipeline).where(CRMPipeline.mentor_id == mentor_id).order_by(CRMPipeline.position.asc(), CRMPipeline.id.asc())
    )
    return q.scalars().first()


async def _get_max_position_in_pipeline(db: AsyncSession, mentor_id: int, pipeline_id: int) -> int:
    q = await db.execute(
        select(func.coalesce(func.max(CRMLead.position), -1)).where(
            CRMLead.mentor_id == mentor_id,
            CRMLead.pipeline_id == pipeline_id,
        )
    )
    return int(q.scalar_one())


# ------------------------ pipelines ------------------------
@router.get("/pipelines", response_model=List[CRMPipelineOut])
async def list_pipelines(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant),
):
    q = await db.execute(
        select(CRMPipeline)
        .where(CRMPipeline.mentor_id == tenant.id)
        .order_by(CRMPipeline.position.asc(), CRMPipeline.id.asc())
    )
    return q.scalars().all()


@router.post("/pipelines", response_model=CRMPipelineOut, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    payload: CRMPipelineCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant),
):
    # define position default = last + 1
    if payload.position is None:
        qpos = await db.execute(
            select(func.coalesce(func.max(CRMPipeline.position), -1)).where(CRMPipeline.mentor_id == tenant.id)
        )
        payload.position = int(qpos.scalar_one()) + 1

    obj = CRMPipeline(
        mentor_id=tenant.id,
        name=payload.name,
        color=payload.color or "border-l-primary",
        position=payload.position or 0,
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.put("/pipelines/{pipeline_id}", response_model=CRMPipelineOut)
async def update_pipeline(
    pipeline_id: int,
    payload: CRMPipelineUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant),
):
    q = await db.execute(
        select(CRMPipeline).where(CRMPipeline.id == pipeline_id, CRMPipeline.mentor_id == tenant.id)
    )
    obj = q.scalars().first()
    if not obj:
        raise HTTPException(404, "Pipeline não encontrado")

    if payload.name is not None:
        obj.name = payload.name.strip() or obj.name
    if payload.color is not None:
        obj.color = payload.color
    if payload.position is not None:
        obj.position = payload.position

    await db.flush()
    await db.refresh(obj)
    return obj


@router.delete("/pipelines/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pipeline(
    pipeline_id: int,
    target_pipeline_id: Optional[int] = Query(None, description="Se informado, move os leads para este pipeline antes de deletar"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant),
):
    # pipeline a excluir
    q = await db.execute(
        select(CRMPipeline).where(CRMPipeline.id == pipeline_id, CRMPipeline.mentor_id == tenant.id)
    )
    pipe = q.scalars().first()
    if not pipe:
        raise HTTPException(404, "Pipeline não encontrado")

    # leads existentes?
    ql = await db.execute(
        select(CRMLead.id).where(CRMLead.mentor_id == tenant.id, CRMLead.pipeline_id == pipeline_id)
    )
    lead_ids = [lid for (lid,) in ql.all()]

    if lead_ids and not target_pipeline_id:
        raise HTTPException(
            400,
            "Há leads neste pipeline. Informe 'target_pipeline_id' para mover antes de remover.",
        )

    if lead_ids and target_pipeline_id:
        # valida pipeline destino
        qdest = await db.execute(
            select(CRMPipeline).where(CRMPipeline.id == target_pipeline_id, CRMPipeline.mentor_id == tenant.id)
        )
        dest = qdest.scalars().first()
        if not dest:
            raise HTTPException(400, "Pipeline destino inválido")

        # move todos para o final do destino
        maxpos = await _get_max_position_in_pipeline(db, tenant.id, dest.id)
        await db.execute(
            update(CRMLead)
            .where(CRMLead.id.in_(lead_ids))
            .values(pipeline_id=dest.id, position=maxpos + 1)
        )

    # remove pipeline
    await db.execute(delete(CRMPipeline).where(CRMPipeline.id == pipeline_id))
    return


# ------------------------ leads ------------------------
@router.get("/board", response_model=CRMBoardOut)
async def get_board(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant),
):
    # pipelines
    qp = await db.execute(
        select(CRMPipeline)
        .where(CRMPipeline.mentor_id == tenant.id)
        .order_by(CRMPipeline.position.asc(), CRMPipeline.id.asc())
    )
    pipelines = qp.scalars().all()

    # leads de todos
    ql = await db.execute(
        select(CRMLead)
        .where(CRMLead.mentor_id == tenant.id)
        .order_by(CRMLead.pipeline_id.asc(), CRMLead.position.asc(), CRMLead.id.asc())
    )
    leads = ql.scalars().all()

    grouped: Dict[int, List[CRMLead]] = {}
    for p in pipelines:
        grouped[p.id] = []
    for lead in leads:
        grouped.setdefault(lead.pipeline_id, []).append(lead)

    return {
        "pipelines": pipelines,
        "leads_by_pipeline": {pid: [lead for lead in lst] for pid, lst in grouped.items()},
    }


@router.get("/leads", response_model=List[CRMLeadOut])
async def list_leads(
    pipeline_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant),
):
    stmt = select(CRMLead).where(CRMLead.mentor_id == tenant.id)
    if pipeline_id:
        stmt = stmt.where(CRMLead.pipeline_id == pipeline_id)
    stmt = stmt.order_by(CRMLead.pipeline_id.asc(), CRMLead.position.asc(), CRMLead.id.asc())

    q = await db.execute(stmt)
    return q.scalars().all()


@router.post("/leads", response_model=CRMLeadOut, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: CRMLeadCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant),
):
    # pipeline default = primeiro por position
    if not payload.pipeline_id:
        first = await _get_first_pipeline(db, tenant.id)
        if not first:
            # cria funis padrão se necessário
            first = CRMPipeline(mentor_id=tenant.id, name="Lead Recebido", color="border-l-primary", position=0)
            db.add(first)
            await db.flush()
        payload.pipeline_id = first.id

    # position default = final da coluna
    if payload.position is None:
        maxpos = await _get_max_position_in_pipeline(db, tenant.id, payload.pipeline_id)
        payload.position = maxpos + 1

    obj = CRMLead(
        mentor_id=tenant.id,
        owner_id=user.id,
        pipeline_id=payload.pipeline_id,
        titulo=payload.titulo,
        cpf=payload.cpf,
        telefone=payload.telefone,
        email=str(payload.email) if payload.email else None,
        estado=payload.estado,
        cidade=payload.cidade,
        plano_desejado=payload.plano_desejado,
        concurso_desejado=payload.concurso_desejado,
        descricao=payload.descricao,
        position=payload.position or 0,
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


@router.put("/leads/{lead_id}", response_model=CRMLeadOut)
async def update_lead(
    lead_id: int,
    payload: CRMLeadUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant),
):
    q = await db.execute(
        select(CRMLead).where(CRMLead.id == lead_id, CRMLead.mentor_id == tenant.id)
    )
    obj = q.scalars().first()
    if not obj:
        raise HTTPException(404, "Lead não encontrado")

    # altera pipeline?
    if payload.pipeline_id is not None and payload.pipeline_id != obj.pipeline_id:
        # mover para outra coluna no final
        maxpos = await _get_max_position_in_pipeline(db, tenant.id, payload.pipeline_id)
        obj.pipeline_id = payload.pipeline_id
        obj.position = maxpos + 1

    # campos simples
    if payload.titulo is not None:
        obj.titulo = payload.titulo
    if payload.cpf is not None:
        obj.cpf = payload.cpf
    if payload.telefone is not None:
        obj.telefone = payload.telefone
    if payload.email is not None:
        obj.email = str(payload.email)
    if payload.estado is not None:
        obj.estado = payload.estado
    if payload.cidade is not None:
        obj.cidade = payload.cidade
    if payload.plano_desejado is not None:
        obj.plano_desejado = payload.plano_desejado
    if payload.concurso_desejado is not None:
        obj.concurso_desejado = payload.concurso_desejado
    if payload.descricao is not None:
        obj.descricao = payload.descricao

    # posição manual (reordenação dentro da coluna)
    if payload.position is not None:
        obj.position = payload.position

    await db.flush()
    await db.refresh(obj)
    return obj


@router.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant),
):
    q = await db.execute(
        select(CRMLead).where(CRMLead.id == lead_id, CRMLead.mentor_id == tenant.id)
    )
    obj = q.scalars().first()
    if not obj:
        raise HTTPException(404, "Lead não encontrado")

    await db.delete(obj)
    return


@router.post("/leads/{lead_id}/move", response_model=CRMLeadOut)
async def move_lead(
    lead_id: int,
    payload: CRMLeadMove,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant),
):
    q = await db.execute(
        select(CRMLead).where(CRMLead.id == lead_id, CRMLead.mentor_id == tenant.id)
    )
    obj = q.scalars().first()
    if not obj:
        raise HTTPException(404, "Lead não encontrado")

    # valida destino
    qdest = await db.execute(
        select(CRMPipeline).where(CRMPipeline.id == payload.to_pipeline_id, CRMPipeline.mentor_id == tenant.id)
    )
    dest = qdest.scalars().first()
    if not dest:
        raise HTTPException(400, "Pipeline destino inválido")

    obj.pipeline_id = dest.id
    obj.position = max(0, payload.to_position)

    await db.flush()
    await db.refresh(obj)
    return obj


# ------------------------ stats ------------------------
@router.get("/stats", response_model=CRMStatsOut)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_tenant),
):
    # total
    q_total = await db.execute(
        select(func.count(CRMLead.id)).where(CRMLead.mentor_id == tenant.id)
    )
    total = int(q_total.scalar_one() or 0)

    # fechado = pipeline com nome 'Fechamento' (ou contains)
    q_close_pipes = await db.execute(
        select(CRMPipeline.id).where(
            CRMPipeline.mentor_id == tenant.id,
            func.lower(CRMPipeline.name).like("%fechamento%"),
        )
    )
    close_ids = [pid for (pid,) in q_close_pipes.all()] or [-1]

    q_closed = await db.execute(
        select(func.count(CRMLead.id)).where(
            CRMLead.mentor_id == tenant.id, CRMLead.pipeline_id.in_(close_ids)
        )
    )
    closed = int(q_closed.scalar_one() or 0)

    return CRMStatsOut(
        total_leads=total,
        closed_count=closed,
        in_progress=max(0, total - closed),
    )
