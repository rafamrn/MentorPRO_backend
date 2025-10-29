# app/modules/students/router.py
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from sqlalchemy import select, delete, and_, func
from typing import List, Optional
import httpx
import re
from app.modules.asaas.models import AsaasConfig
from app.modules.products.models import Product
from .schemas import RevenueByCreatedOut
from app.core.dependencies import get_db, get_current_user
from app.modules.users.models import User
from .models import Student
from .schemas import (
    StudentOut, StudentCreate, StudentUpdate,
    BulkUpsertItem, BulkDeleteIn, BulkUpsertIn, BulkDeleteOut
)

router = APIRouter()  # <— sem prefixo aqui

# ==== Helpers Asaas ====
def _digits(s: Optional[str]) -> str:
    return re.sub(r"\D+", "", s or "")

def _cpf_cnpj_or_none(value: Optional[str]) -> Optional[str]:
    d = _digits(value)
    return d if len(d) in (11, 14) else None

def _mobile_or_none(value: Optional[str]) -> Optional[str]:
    d = _digits(value)
    return d or None

async def _get_asaas_config(db: AsyncSession, mentor_id: int) -> Optional[AsaasConfig]:
    """
    Busca api_key/sandbox por mentor.
    Ajuste este SELECT se sua tabela/campos tiverem outros nomes.
    """
    res = await db.execute(
        select(AsaasConfig).where(AsaasConfig.mentor_id == mentor_id)
    )
    return res.scalar_one_or_none()

async def _asaas_create_customer(*, api_key: str, sandbox: bool, name: str,
                                 cpf_cnpj: Optional[str], email: Optional[str],
                                 mobile_phone: Optional[str]) -> dict:
    base = "https://api-sandbox.asaas.com/v3" if sandbox else "https://api.asaas.com/v3"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "access_token": api_key,
    }
    payload = {
        "name": name,
        "cpfCnpj": cpf_cnpj,
        "email": email,
        "mobilePhone": mobile_phone,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(f"{base}/customers", json=payload, headers=headers)
        # Se falhar, levanta erro (você pode querer tratar 409 de duplicidade diferente)
        r.raise_for_status()
        return r.json()
# =======================

# LIST
@router.get("", response_model=list[StudentOut])
async def list_students(
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
    limit: int = Query(1000, le=100000),
    offset: int = 0,
    data_compra_ini: str | None = Query(None, description="YYYY-MM-DD"),
    data_compra_fim: str | None = Query(None, description="YYYY-MM-DD"),
):
    stmt = (
        select(Student)
        .where(Student.mentor_id == me.id)
    )

    # filtros por data_compra (fechando intervalo inclusive)
    from datetime import datetime, date
    if data_compra_ini:
        try:
            d_ini = datetime.strptime(data_compra_ini, "%Y-%m-%d").date()
            stmt = stmt.where(Student.data_compra >= d_ini)
        except ValueError:
            raise HTTPException(status_code=400, detail="data_compra_ini inválida (use YYYY-MM-DD)")
    if data_compra_fim:
        try:
            d_fim = datetime.strptime(data_compra_fim, "%Y-%m-%d").date()
            stmt = stmt.where(Student.data_compra <= d_fim)
        except ValueError:
            raise HTTPException(status_code=400, detail="data_compra_fim inválida (use YYYY-MM-DD)")

    stmt = stmt.order_by(Student.nome.asc()).limit(limit).offset(offset)

    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/created/count")
async def count_created_students(
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
    ini: str = Query(..., description="YYYY-MM-DD"),
    fim: str = Query(..., description="YYYY-MM-DD (inclusive)"),
):
    try:
        dt_ini = datetime.fromisoformat(ini).replace(hour=0, minute=0, second=0, microsecond=0)
        dt_fim = datetime.fromisoformat(fim).replace(hour=23, minute=59, second=59, microsecond=999999)
    except Exception:
        raise HTTPException(status_code=400, detail="Parâmetros ini/fim inválidos. Use YYYY-MM-DD.")

    q = await db.execute(
        select(func.count(Student.id)).where(
            and_(
                Student.mentor_id == me.id,
                Student.created_at >= dt_ini,
                Student.created_at <= dt_fim,
            )
        )
    )
    return {"count": q.scalar_one()}

# CREATE
@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(
    payload: StudentCreate,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    # 1) Cria o aluno no banco
    obj = Student(**payload.model_dump(), mentor_id=me.id)
    db.add(obj)
    await db.flush()     # garante PK sem fechar a transação

    # 2) Busca config Asaas do mentor
    cfg = await _get_asaas_config(db, mentor_id=me.id)

    if cfg:
        # 3) Normaliza campos e chama Asaas
        cpf_cnpj = _cpf_cnpj_or_none(obj.cpf)
        mobile   = _mobile_or_none(obj.telefone)
        try:
            resp = await _asaas_create_customer(
                api_key=cfg.api_key,
                sandbox=cfg.sandbox,
                name=obj.nome,
                cpf_cnpj=cpf_cnpj,
                email=obj.email,
                mobile_phone=mobile,
            )
            obj.asaas_customer_id = resp.get("id")
        except httpx.HTTPStatusError as e:
            # Política: não bloquear criação do aluno; apenas segue sem asaas_customer_id
            # Para bloquear, troque por raise HTTPException(...)
            # Se quiser tratar 409 (duplicado), você pode buscar o id existente e setar aqui.
            pass

    await db.commit()
    await db.refresh(obj)
    return obj

# UPDATE
@router.put("/{student_id}", response_model=StudentOut)
async def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Student).where(and_(Student.id == student_id, Student.mentor_id == me.id))
    )
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)

    await db.commit()
    await db.refresh(obj)
    return obj

# DELETE (um)
@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    # 1) Busca aluno e garante que pertence ao mentor
    res = await db.execute(
        select(Student).where(and_(Student.id == student_id, Student.mentor_id == me.id))
    )
    student = res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    # 2) Se aluno tem asaas_customer_id, tenta deletar no Asaas
    if student.asaas_customer_id:
        # usa helper já existente para pegar a config
        cfg = await _get_asaas_config(db, mentor_id=me.id)
        if cfg:
            base = "https://api-sandbox.asaas.com/v3" if cfg.sandbox else "https://api.asaas.com/v3"
            headers = {
                "accept": "application/json",
                "access_token": cfg.api_key,
            }
            url = f"{base}/customers/{student.asaas_customer_id}"

            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    r = await client.delete(url, headers=headers)
                    # sucesso normalmente 200/204; se falhar, apenas loga e segue
                    if r.status_code >= 400:
                        print(f"[ASAAS] Falha ao excluir cliente {student.asaas_customer_id}: {r.status_code} {r.text}")
            except Exception as e:
                print(f"[ASAAS] Erro ao chamar API de exclusão: {e}")

    # 3) Exclui aluno localmente
    await db.execute(delete(Student).where(Student.id == student_id))
    await db.commit()
    return



# BULK DELETE — o FE faz DELETE /students/bulk com body { ids: [...] }
@router.delete("/bulk", response_model=BulkDeleteOut)
async def bulk_delete(
    inp: BulkDeleteIn = Body(...),
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    if not inp.ids:
        return {"count": 0}
    stmt = delete(Student).where(and_(Student.mentor_id == me.id, Student.id.in_(inp.ids)))
    res = await db.execute(stmt)
    await db.commit()
    return {"count": res.rowcount or len(inp.ids)}

@router.get("/revenue/purchases", response_model=RevenueByCreatedOut)
async def revenue_by_purchases(
    ini: str,  # YYYY-MM-DD
    fim: str,  # YYYY-MM-DD
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    """
    Soma Product.valor dos alunos cuja data_compra está no intervalo [ini..fim] (inclusive),
    combinando Student.plano == Product.nome e mesmo mentor_id. Produtos inativos não entram.
    """
    # valida datas
    try:
        d_ini = datetime.strptime(ini, "%Y-%m-%d").date()
        d_fim = datetime.strptime(fim, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Datas inválidas. Use YYYY-MM-DD.")

    if d_fim < d_ini:
        raise HTTPException(status_code=400, detail="fim não pode ser menor que ini.")

    # LEFT JOIN para contar alunos mesmo sem produto correspondente; soma ignora NULL
    stmt = (
        select(
            func.coalesce(func.sum(Product.valor), 0).label("total"),
            func.count(Student.id).label("count"),
        )
        .select_from(Student)
        .join(
            Product,
            and_(
                Product.nome == Student.plano,
                Product.mentor_id == Student.mentor_id,
                Product.ativo == True,
            ),
            isouter=True,
        )
        .where(
            and_(
                Student.mentor_id == me.id,
                Student.data_compra.is_not(None),
                Student.data_compra >= d_ini,
                Student.data_compra <= d_fim,
            )
        )
    )

    res = await db.execute(stmt)
    total, count = res.one_or_none() or (0, 0)
    return RevenueByCreatedOut(total=float(total or 0), count=int(count or 0))

@router.post("/{student_id}/asaas/sync", response_model=StudentOut)
async def sync_student_asaas(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Student).where(and_(Student.id == student_id, Student.mentor_id == me.id))
    )
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    if obj.asaas_customer_id:
        return obj  # já sincronizado

    cfg = await _get_asaas_config(db, mentor_id=me.id)
    if not cfg:
        raise HTTPException(status_code=400, detail="Configuração Asaas não encontrada para este mentor")

    cpf_cnpj = _cpf_cnpj_or_none(obj.cpf)
    mobile   = _mobile_or_none(obj.telefone)

    try:
        resp = await _asaas_create_customer(
            api_key=cfg.api_key,
            sandbox=cfg.sandbox,
            name=obj.nome,
            cpf_cnpj=cpf_cnpj,
            email=obj.email,
            mobile_phone=mobile,
        )
        obj.asaas_customer_id = resp.get("id")
        await db.commit()
        await db.refresh(obj)
        return obj
    except httpx.HTTPStatusError as e:
        # expondo retorno do Asaas para debug no FE (422/409/etc.)
        detail = {"message": "Falha ao criar cliente no Asaas"}
        try:
            detail["asaas"] = e.response.json()
        except Exception:
            detail["asaas_raw"] = e.response.text
        raise HTTPException(status_code=502, detail=detail)