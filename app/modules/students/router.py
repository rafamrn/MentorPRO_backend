from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date
from sqlalchemy import select, delete, and_, func
from typing import Optional, Any, Dict, List
import httpx
import re
import unicodedata
import calendar
from app.modules.financeiro.models import Pagamento
from app.modules.financeiro.schemas import SyncCompetenciasIn, SyncCompetenciasOut
from app.modules.asaas.models import AsaasConfig
from app.modules.products.models import Product
from app.core.dependencies import get_db, get_current_user
from app.modules.users.models import User
from app.modules.financeiro.models import Pagamento, STATUS_CHOICES
from .models import Student
from .schemas import (
    StudentOut, StudentCreate, StudentUpdate,
    BulkUpsertItem, BulkDeleteIn, BulkUpsertIn, BulkDeleteOut,
    RevenueByCreatedOut, ChargeCreateIn, ChargeCreateOut
)

router = APIRouter()

# ==== Helpers comuns ====
def _ym_to_year_month(ym: str) -> tuple[int, int]:
    y, m = ym.split("-")
    yi = int(y); mi = int(m)
    if mi < 1 or mi > 12:
        raise ValueError("Mês inválido em competencia (use YYYY-MM).")
    return yi, mi

def _prev_year_month(today: date | None = None) -> str:
    d = today or date.today()
    y = d.year; m = d.month
    m -= 1
    if m == 0:
        y -= 1; m = 12
    return f"{y:04d}-{m:02d}"

def _iter_ym(start_ym: str, end_ym: str):
    sy, sm = _ym_to_year_month(start_ym)
    ey, em = _ym_to_year_month(end_ym)
    y, m = sy, sm
    while (y < ey) or (y == ey and m <= em):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m == 13:
            m = 1
            y += 1

async def _produto_valor_for_student(db: AsyncSession, st: Student) -> float | None:
    if not st.plano:
        return None
    res = await db.execute(
        select(Product).where(
            and_(Product.nome == st.plano, Product.mentor_id == st.mentor_id, Product.ativo == True)
        )
    )
    prod = res.scalar_one_or_none()
    if not prod:
        return None
    for k in ("valor", "price", "preco"):
        v = getattr(prod, k, None)
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    return None

def _due_for(competencia: str, st: Student) -> date | None:
    """Calcula due_date no dia_vencimento do aluno (clamp no fim do mês)."""
    try:
        dia = int(getattr(st, "dia_vencimento", None) or 0)
    except Exception:
        dia = None
    if not dia or dia < 1 or dia > 31:
        return None
    y, m = _ym_to_year_month(competencia)
    last = calendar.monthrange(y, m)[1]
    d = min(dia, last)
    return date(y, m, d)

def _is_paid(status: str | None) -> bool:
    if not status:
        return False
    s = status.upper()
    return s in {"RECEIVED", "RECEIVED_IN_CASH", "CONFIRMED", "DUNNING_RECEIVED"}

def _paid_at(item: dict) -> str | None:
    """
    Tenta extrair a melhor data de pagamento do item do Asaas.
    """
    for k in ("clientPaymentDate", "paymentDate", "confirmedDate", "creditDate", "estimatedCreditDate"):
        v = item.get(k)
        if v:
            return v
    return None

def _extract_paid_at(item: Dict[str, Any]) -> str | None:
    """
    Prioriza 'clientPaymentDate', depois 'paymentDate', depois 'confirmedDate'.
    Retorna string ISO 'YYYY-MM-DD' se disponível.
    """
    for k in ("clientPaymentDate", "paymentDate", "confirmedDate"):
        v = (item.get(k) or "").strip()
        if v:
            # Em geral a Asaas manda 'YYYY-MM-DD'
            return v[:10]
    return None

def _digits(s: Optional[str]) -> str:
    return re.sub(r"\D+", "", s or "")

def _cpf_cnpj_or_none(value: Optional[str]) -> Optional[str]:
    d = _digits(value)
    return d if len(d) in (11, 14) else None

def _mobile_or_none(value: Optional[str]) -> Optional[str]:
    d = _digits(value)
    return d or None

def _coerce_value(v) -> float:
    if v is None:
        raise ValueError("value é obrigatório")
    if isinstance(v, (int, float)):
        f = float(v)
    else:
        s = re.sub(r"[^\d,\.]", "", str(v) or "")
        if not s:
            raise ValueError("value inválido")
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        f = float(s)
    if f <= 0:
        raise ValueError("value deve ser > 0")
    return round(f, 2)

def _strip_accents_lower(s: str) -> str:
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    no_acc = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", no_acc.lower()).strip()

# ==== Helpers Asaas ====
def _norm_pagto(s: Optional[str]) -> str:
    """
    Normaliza entradas variadas para (boleto|cartao|pix)
    Aceita: 'Boleto', 'Cartão de Crédito', 'cartao credito', 'PIX', etc.
    """
    t = _strip_accents_lower(s or "")
    if not t:
        return ""
    if "boleto" in t:
        return "boleto"
    if "pix" in t:
        return "pix"
    if "cartao" in t or "credito" in t or "credit" in t or "card" in t:
        return "cartao"
    return t  # volta o texto limpo; pode virar UNDEFINED depois

def _prev_year_month(today: date | None = None) -> str:
    d = today or date.today()
    y, m = d.year, d.month
    m -= 1
    if m == 0:
        y -= 1
        m = 12
    return f"{y:04d}-{m:02d}"

def _iter_ym(start_ym: str, end_ym: str):
    sy, sm = map(int, start_ym.split("-"))
    ey, em = map(int, end_ym.split("-"))
    y, m = sy, sm
    while (y < ey) or (y == ey and m <= em):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m == 13:
            m = 1
            y += 1

def _due_for(competencia: str, st: Student) -> date | None:
    try:
        dia = int(getattr(st, "dia_vencimento", None) or 0)
    except Exception:
        dia = None
    if not dia or dia < 1 or dia > 31:
        return None
    y, m = map(int, competencia.split("-"))
    last = calendar.monthrange(y, m)[1]
    d = min(dia, last)
    return date(y, m, d)

async def _produto_valor_for_student(db: AsyncSession, st: Student) -> float | None:
    if not st.plano:
        return None
    res = await db.execute(
        select(Product).where(
            and_(Product.nome == st.plano, Product.mentor_id == st.mentor_id, Product.ativo == True)
        )
    )
    prod = res.scalar_one_or_none()
    if not prod:
        return None
    for k in ("valor", "price", "preco"):
        v = getattr(prod, k, None)
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    return None

def _extract_method(item: Dict[str, Any]) -> str | None:
    bt = (item.get("billingType") or "").strip().lower()
    if not bt:
        return None
    # normaliza para o que você quer salvar na coluna 'method'
    if bt == "boleto":
        return "boleto"
    if bt == "pix":
        return "pix"
    if bt in ("credit_card", "creditcard", "cartao"):
        return "cartao"
    if bt in ("debit_card", "debitcard"):
        return "debito"
    return bt  # fallback

def _billing_type_from_student_method(metodo: Optional[str]) -> str:
    m = _norm_pagto(metodo)
    if m == "boleto":
        return "BOLETO"
    if m == "cartao":
        return "CREDIT_CARD"
    if m == "pix":
        return "PIX"
    return "UNDEFINED"

async def _get_asaas_config(db: AsyncSession, mentor_id: int) -> Optional[AsaasConfig]:
    res = await db.execute(select(AsaasConfig).where(AsaasConfig.mentor_id == mentor_id))
    return res.scalar_one_or_none()

async def _asaas_create_customer(*, api_key: str, sandbox: bool, name: str,
                                 cpf_cnpj: Optional[str], email: Optional[str],
                                 mobile_phone: Optional[str]) -> dict:
    base = "https://api-sandbox.asaas.com/v3" if sandbox else "https://api.asaas.com/v3"
    headers = {"accept": "application/json", "content-type": "application/json", "access_token": api_key}
    payload = {"name": name, "cpfCnpj": cpf_cnpj, "email": email, "mobilePhone": mobile_phone}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(f"{base}/customers", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()

async def _asaas_update_customer(
    *, api_key: str, sandbox: bool, customer_id: str,
    name: str | None = None, cpf_cnpj: str | None = None, email: str | None = None,
    mobile_phone: str | None = None,
) -> dict:
    base = "https://api-sandbox.asaas.com/v3" if sandbox else "https://api.asaas.com/v3"
    headers = {"accept": "application/json", "content-type": "application/json", "access_token": api_key}
    payload = {}
    if name:         payload["name"] = name
    if cpf_cnpj:     payload["cpfCnpj"] = cpf_cnpj
    if email:        payload["email"] = email
    if mobile_phone: payload["mobilePhone"] = mobile_phone
    if not payload:
        return {"skipped": True}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.put(f"{base}/customers/{customer_id}", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()

async def _asaas_find_customer(*, api_key: str, sandbox: bool,
                               cpf_cnpj: Optional[str] = None,
                               email: Optional[str] = None) -> Optional[str]:
    base = "https://api-sandbox.asaas.com/v3" if sandbox else "https://api.asaas.com/v3"
    headers = {"accept": "application/json", "content-type": "application/json", "access_token": api_key}
    async with httpx.AsyncClient(timeout=20.0) as client:
        if cpf_cnpj:
            r = await client.get(f"{base}/customers", params={"cpfCnpj": cpf_cnpj}, headers=headers)
            r.raise_for_status()
            data = r.json() or {}
            items = data.get("data") or data.get("items") or []
            if items:
                return items[0].get("id")
        if email:
            r = await client.get(f"{base}/customers", params={"email": email}, headers=headers)
            r.raise_for_status()
            data = r.json() or {}
            items = data.get("data") or data.get("items") or []
            if items:
                return items[0].get("id")
    return None

async def _asaas_create_payment(
    *, api_key: str, sandbox: bool, customer_id: str,
    value: float, due_date: str, billing_type: str,
    description: Optional[str] = None,
    external_reference: Optional[str] = None,
) -> dict:
    base = "https://api-sandbox.asaas.com/v3" if sandbox else "https://api.asaas.com/v3"
    headers = {"accept": "application/json", "content-type": "application/json", "access_token": api_key}
    payload = {
        "customer": customer_id,
        "value": round(float(value), 2),
        "dueDate": due_date,
        "billingType": billing_type,
    }
    if description:
        payload["description"] = description
    if external_reference:
        payload["externalReference"] = external_reference

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{base}/payments", json=payload, headers=headers)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            try:
                detail = e.response.json()
            except Exception:
                detail = {"status_code": e.response.status_code if e.response else None,
                          "text": e.response.text if e.response else str(e)}
            print("[ASAAS][PAYMENTS][ERROR]", detail)
            errors = (detail or {}).get("errors") or []
            codes = { (err.get("code") or "") for err in errors if isinstance(err, dict) }
            if "invalid_dueDate" in codes:
                raise HTTPException(status_code=400, detail="dueDate não pode ser anterior à data de hoje.")
            raise HTTPException(status_code=502, detail=detail)
        return r.json()

# ======================= ROTAS =======================

@router.get("", response_model=list[StudentOut])
async def list_students(
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
    limit: int = Query(1000, le=100000),
    offset: int = 0,
    data_compra_ini: str | None = Query(None, description="YYYY-MM-DD"),
    data_compra_fim: str | None = Query(None, description="YYYY-MM-DD"),
):
    stmt = select(Student).where(Student.mentor_id == me.id)

    from datetime import datetime as _dt
    if data_compra_ini:
        try:
            d_ini = _dt.strptime(data_compra_ini, "%Y-%m-%d").date()
            stmt = stmt.where(Student.data_compra >= d_ini)
        except ValueError:
            raise HTTPException(status_code=400, detail="data_compra_ini inválida (use YYYY-MM-DD)")
    if data_compra_fim:
        try:
            d_fim = _dt.strptime(data_compra_fim, "%Y-%m-%d").date()
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

@router.post("/{student_id}/payments/sync", response_model=SyncCompetenciasOut)
async def sync_payments_competencias(
    student_id: int,
    body: SyncCompetenciasIn = Body(default=SyncCompetenciasIn()),
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    """
    Gera competências 'pendente' na tabela pagamentos, 1 por mês, desde a data_compra do aluno
    até 'ate_competencia' (default: mês anterior). Não duplica competências existentes.
    """
    # aluno do mentor
    res = await db.execute(select(Student).where(and_(Student.id == student_id, Student.mentor_id == me.id)))
    st = res.scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    if not st.data_compra:
        raise HTTPException(status_code=400, detail="Aluno sem data_compra definida")

    # intervalo de competências
    start_ym = f"{st.data_compra.year:04d}-{st.data_compra.month:02d}"
    end_ym = body.ate_competencia or _prev_year_month()

    # valor default da parcela
    default_valor = body.valor
    if default_valor is None:
        default_valor = await _produto_valor_for_student(db, st)

    created, skipped = 0, 0
    for ym in _iter_ym(start_ym, end_ym):
        # já existe para este aluno/mentor/competência?
        exists = await db.scalar(
            select(func.count(Pagamento.id)).where(
                and_(
                    Pagamento.mentor_id == me.id,
                    Pagamento.student_id == st.id,
                    Pagamento.competencia == ym,
                )
            )
        )
        if exists:
            skipped += 1
            continue

        due = body.overwrite_due_date or _due_for(ym, st)
        ext = f"student:{st.id}:{ym}"

        db.add(Pagamento(
            mentor_id=me.id,
            student_id=st.id,
            competencia=ym,
            due_date=due,
            valor=default_valor,
            status_pagamento="pendente",
            source="manual",
            external_reference=ext,
        ))
        created += 1

    await db.commit()
    return SyncCompetenciasOut(created=created, skipped=skipped)


@router.put("/{student_id}", response_model=StudentOut)
async def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    res = await db.execute(select(Student).where(and_(Student.id == student_id, Student.mentor_id == me.id)))
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)

    if obj.asaas_customer_id:
        cfg = await _get_asaas_config(db, mentor_id=me.id)
        if cfg:
            cpf_cnpj = _cpf_cnpj_or_none(obj.cpf)
            mobile   = _mobile_or_none(obj.telefone)
            try:
                await _asaas_update_customer(
                    api_key=cfg.api_key,
                    sandbox=cfg.sandbox,
                    customer_id=obj.asaas_customer_id,
                    name=obj.nome,
                    cpf_cnpj=cpf_cnpj,
                    email=obj.email,
                    mobile_phone=mobile,
                )
            except httpx.HTTPStatusError as e:
                try:
                    print("[ASAAS][PUT] Falha:", e.response.status_code, e.response.text)
                except Exception:
                    print("[ASAAS][PUT] Falha desconhecida ao atualizar cliente")

    await db.commit()
    await db.refresh(obj)
    return obj

@router.post("", response_model=StudentOut, status_code=201)
async def create_student(
    payload: StudentCreate,
    gerar_competencias: bool = Query(True, description="Se true, cria pagamentos pendentes desde data_compra até mês anterior"),
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    # cria o aluno
    obj = Student(**payload.model_dump(), mentor_id=me.id)
    db.add(obj)
    await db.flush()  # ganha obj.id

    # opcional: cria customer na Asaas se já tiver config e dados (mesma lógica do bulk_upsert)
    cfg = await _get_asaas_config(db, mentor_id=me.id)
    if cfg:
        cpf_cnpj = _cpf_cnpj_or_none(obj.cpf)
        mobile   = _mobile_or_none(obj.telefone)
        try:
            resp = await _asaas_create_customer(
                api_key=cfg.api_key, sandbox=cfg.sandbox,
                name=obj.nome, cpf_cnpj=cpf_cnpj, email=obj.email, mobile_phone=mobile,
            )
            obj.asaas_customer_id = resp.get("id")
        except httpx.HTTPStatusError:
            try:
                existing_id = await _asaas_find_customer(
                    api_key=cfg.api_key, sandbox=cfg.sandbox,
                    cpf_cnpj=cpf_cnpj, email=obj.email,
                )
                if existing_id:
                    obj.asaas_customer_id = existing_id
            except Exception:
                pass

    # gerar competências/pagamentos pendentes
    if gerar_competencias:
        if not obj.data_compra:
            # não gera nada sem data_compra
            pass
        else:
            start_ym = f"{obj.data_compra.year:04d}-{obj.data_compra.month:02d}"
            end_ym = _prev_year_month()
            default_valor = await _produto_valor_for_student(db, obj)

            created = 0
            for ym in _iter_ym(start_ym, end_ym):
                # não duplica se já existir
                exists = await db.scalar(
                    select(func.count(Pagamento.id)).where(
                        and_(
                            Pagamento.mentor_id == me.id,
                            Pagamento.student_id == obj.id,
                            Pagamento.competencia == ym,
                        )
                    )
                )
                if exists:
                    continue

                db.add(Pagamento(
                    mentor_id=me.id,
                    student_id=obj.id,
                    competencia=ym,
                    due_date=_due_for(ym, obj),
                    valor=default_valor,
                    status_pagamento="pendente",
                    source="manual",
                    external_reference=f"student:{obj.id}:{ym}",
                ))
                created += 1
            # você pode logar created se quiser

    await db.commit()
    await db.refresh(obj)
    return obj

@router.post("/bulk_upsert", response_model=BulkDeleteOut)
async def bulk_upsert(
    inp: BulkUpsertIn,
    sync_asaas: bool = Query(False, description="Se true, cria/sincroniza clientes na Asaas para cada aluno importado"),
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    created = 0
    cfg = None
    if sync_asaas:
        cfg = await _get_asaas_config(db, mentor_id=me.id)

    for it in inp.alunos:
        obj = Student(**it.model_dump(), mentor_id=me.id)
        db.add(obj)
        created += 1

        if sync_asaas and cfg:
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
            except httpx.HTTPStatusError:
                try:
                    existing_id = await _asaas_find_customer(
                        api_key=cfg.api_key,
                        sandbox=cfg.sandbox,
                        cpf_cnpj=cpf_cnpj,
                        email=obj.email,
                    )
                    if existing_id:
                        obj.asaas_customer_id = existing_id
                except Exception:
                    pass

    await db.commit()
    return {"count": created}

@router.delete("/bulk", response_model=BulkDeleteOut)
async def bulk_delete(
    inp: BulkDeleteIn = Body(...),
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    if not inp.ids:
        return {"count": 0}

    res = await db.execute(
        select(Student).where(and_(Student.mentor_id == me.id, Student.id.in_(inp.ids)))
    )
    students = res.scalars().all()
    if not students:
        return {"count": 0}

    cfg = await _get_asaas_config(db, mentor_id=me.id)
    if cfg:
        base = "https://api-sandbox.asaas.com/v3" if cfg.sandbox else "https://api.asaas.com/v3"
        headers = {"accept": "application/json", "access_token": cfg.api_key}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                for st in students:
                    if not st.asaas_customer_id:
                        continue
                    url = f"{base}/customers/{st.asaas_customer_id}"
                    try:
                        r = await client.delete(url, headers=headers)
                        if r.status_code >= 400:
                            print(f"[ASAAS] Falha ao excluir cliente {st.asaas_customer_id}: "
                                  f"{r.status_code} {r.text}")
                    except Exception as e:
                        print(f"[ASAAS] Erro ao chamar API de exclusão ({st.asaas_customer_id}): {e}")
        except Exception as e:
            print(f"[ASAAS] Erro geral no bulk delete: {e}")

    await db.execute(delete(Student).where(and_(Student.mentor_id == me.id, Student.id.in_(inp.ids))))
    await db.commit()
    return {"count": len(students)}

@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    res = await db.execute(select(Student).where(and_(Student.id == student_id, Student.mentor_id == me.id)))
    student = res.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    if student.asaas_customer_id:
        cfg = await _get_asaas_config(db, mentor_id=me.id)
        if cfg:
            base = "https://api-sandbox.asaas.com/v3" if cfg.sandbox else "https://api.asaas.com/v3"
            headers = {"accept": "application/json", "access_token": cfg.api_key}
            url = f"{base}/customers/{student.asaas_customer_id}"
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    r = await client.delete(url, headers=headers)
                    if r.status_code >= 400:
                        print(f"[ASAAS] Falha ao excluir cliente {student.asaas_customer_id}: {r.status_code} {r.text}")
            except Exception as e:
                print(f"[ASAAS] Erro ao chamar API de exclusão: {e}")

    await db.execute(delete(Student).where(Student.id == student_id))
    await db.commit()
    return

@router.get("/revenue/purchases", response_model=RevenueByCreatedOut)
async def revenue_by_purchases(
    ini: str,  # YYYY-MM-DD
    fim: str,  # YYYY-MM-DD
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    try:
        d_ini = datetime.strptime(ini, "%Y-%m-%d").date()
        d_fim = datetime.strptime(fim, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Datas inválidas. Use YYYY-MM-DD.")
    if d_fim < d_ini:
        raise HTTPException(status_code=400, detail="fim não pode ser menor que ini.")

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

@router.post("/{student_id}/asaas/charge", response_model=ChargeCreateOut, status_code=201)
async def create_asaas_charge_for_student(
    student_id: int,
    payload: ChargeCreateIn,
    competencia_qs: Optional[str] = Query(
        None,
        alias="competencia",
        description="YYYY-MM (opcional se vier no body.metadata.competencia)"
    ),
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    # 1) Aluno
    res = await db.execute(
        select(Student).where(and_(Student.id == student_id, Student.mentor_id == me.id))
    )
    st: Student | None = res.scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    # 2) Config Asaas
    cfg = await _get_asaas_config(db, mentor_id=me.id)
    if not cfg:
        raise HTTPException(status_code=400, detail="Configuração Asaas não encontrada para este mentor")

    # 3) Garantir customer
    if not st.asaas_customer_id:
        cpf_cnpj = _cpf_cnpj_or_none(st.cpf)
        mobile   = _mobile_or_none(st.telefone)
        try:
            resp = await _asaas_create_customer(
                api_key=cfg.api_key, sandbox=cfg.sandbox,
                name=st.nome, cpf_cnpj=cpf_cnpj, email=st.email, mobile_phone=mobile,
            )
            st.asaas_customer_id = resp.get("id")
            await db.commit()
            await db.refresh(st)
        except httpx.HTTPStatusError:
            existing_id = await _asaas_find_customer(
                api_key=cfg.api_key, sandbox=cfg.sandbox,
                cpf_cnpj=cpf_cnpj, email=st.email,
            )
            if existing_id:
                st.asaas_customer_id = existing_id
                await db.commit()
                await db.refresh(st)
            else:
                raise HTTPException(status_code=502, detail="Falha ao criar/obter cliente no Asaas")

    # 4) Método de pagamento -> billingType
    metodo = payload.metodo_pagamento or st.metodo_pagamento
    billing_type = _billing_type_from_student_method(metodo)
    if billing_type == "UNDEFINED":
        raise HTTPException(status_code=400, detail="Método de pagamento inválido/ausente. Use boleto | cartao | pix.")

    # 5) Valor
    try:
        valor = _coerce_value(payload.value)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 6) dueDate
    if not payload.dueDate:
        raise HTTPException(status_code=400, detail="dueDate é obrigatório (YYYY-MM-DD)")
    try:
        d_due = date.fromisoformat(str(payload.dueDate))
    except Exception:
        raise HTTPException(status_code=400, detail="dueDate deve estar em YYYY-MM-DD")
    if d_due < date.today():
        raise HTTPException(status_code=400, detail="dueDate não pode ser anterior à data de hoje.")

    # 7) COMPETÊNCIA — aceitar body.metadata ou query
    competencia: Optional[str] = None
    if isinstance(payload.metadata, dict):
        comp_raw = payload.metadata.get("competencia") or payload.metadata.get("competência")
        if isinstance(comp_raw, str) and re.fullmatch(r"\d{4}-\d{2}", comp_raw):
            competencia = comp_raw

    if not competencia and competencia_qs:
        if re.fullmatch(r"\d{4}-\d{2}", competencia_qs):
            competencia = competencia_qs

    if not competencia:
        raise HTTPException(
            status_code=400,
            detail="Informe a competência (YYYY-MM) via body.metadata.competencia ou via query ?competencia=YYYY-MM."
        )

    # 8) Buscar a LINHA EXISTENTE da competência (não criar nova)
    res_exist = await db.execute(
        select(Pagamento).where(
            and_(
                Pagamento.mentor_id == me.id,
                Pagamento.student_id == st.id,
                Pagamento.competencia == competencia,
            )
        )
    )
    pg = res_exist.scalar_one_or_none()
    if not pg:
        raise HTTPException(
            status_code=404,
            detail=f"Competência {competencia} não encontrada para este aluno. Gere/sincronize as competências antes."
        )

    # 9) Cria cobrança na Asaas (sem metadata, com externalReference informativa)
    ext_ref = f"student:{student_id}:{competencia}"
    raw = await _asaas_create_payment(
        api_key=cfg.api_key,
        sandbox=cfg.sandbox,
        customer_id=st.asaas_customer_id,
        value=valor,
        due_date=str(d_due),
        billing_type=billing_type,
        description=payload.description or f"Cobrança {st.nome} ({competencia})",
        external_reference=ext_ref,
    )

    # 10) Atualiza a linha EXISTENTE para 'pendente' (PENDING)
    m_norm = (metodo or "").strip().lower()
    method_txt = "pix" if "pix" in m_norm else ("cartao" if "cart" in m_norm else ("boleto" if "boleto" in m_norm else None))

    pg.status_pagamento = "pendente"
    pg.asaas_payment_id = raw.get("id") or pg.asaas_payment_id
    pg.external_reference = ext_ref
    pg.method = method_txt or pg.method
    pg.valor = float(valor)
    pg.due_date = d_due
    pg.source = "asaas"
    pg.paid_at = None

    await db.commit()
    await db.refresh(pg)

    return ChargeCreateOut(
        id = raw.get("id") or "",
        status = raw.get("status"),
        billingType = raw.get("billingType"),
        invoiceUrl = raw.get("invoiceUrl"),
        bankSlipUrl = raw.get("bankSlipUrl"),
        pixQrCodeId = (raw.get("pixTransaction") or {}).get("id") if isinstance(raw.get("pixTransaction"), dict) else None,
        raw = raw,
    )

@router.post("/{student_id}/asaas/sync", response_model=StudentOut)
async def sync_student_asaas(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    res = await db.execute(select(Student).where(and_(Student.id == student_id, Student.mentor_id == me.id)))
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    if obj.asaas_customer_id:
        return obj

    cfg = await _get_asaas_config(db, mentor_id=me.id)
    if not cfg:
        raise HTTPException(status_code=400, detail="Configuração Asaas não encontrada para este mentor")

    cpf_cnpj = _cpf_cnpj_or_none(obj.cpf)
    mobile   = _mobile_or_none(obj.telefone)

    try:
        resp = await _asaas_create_customer(
            api_key=cfg.api_key, sandbox=cfg.sandbox,
            name=obj.nome, cpf_cnpj=cpf_cnpj, email=obj.email, mobile_phone=mobile,
        )
        obj.asaas_customer_id = resp.get("id")
        await db.commit()
        await db.refresh(obj)
        return obj
    except httpx.HTTPStatusError as e:
        detail = {"message": "Falha ao criar cliente no Asaas"}
        try:
            detail["asaas"] = e.response.json()
        except Exception:
            detail["asaas_raw"] = e.response.text
        raise HTTPException(status_code=502, detail=detail)

@router.get("/{student_id}/asaas/payments")
async def list_asaas_payments_for_student(
    student_id: int,
    competencia: str = Query(..., description="YYYY-MM"),
    reconcile: bool = Query(True, description="Se true, ajusta o status_pagamento local conforme status do Asaas"),
    db: AsyncSession = Depends(get_db),
    me: User = Depends(get_current_user),
):
    # --- valida competência ---
    try:
        dt_ini = datetime.strptime(competencia, "%Y-%m").date().replace(day=1)
        last_day = calendar.monthrange(dt_ini.year, dt_ini.month)[1]
        dt_fim = date(dt_ini.year, dt_ini.month, last_day)
    except Exception:
        raise HTTPException(status_code=400, detail="competencia inválida (use YYYY-MM)")

    # --- aluno / mentor ---
    res = await db.execute(
        select(Student).where(and_(Student.id == student_id, Student.mentor_id == me.id))
    )
    st: Student | None = res.scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    # --- config Asaas ---
    cfg = await _get_asaas_config(db, mentor_id=me.id)
    if not cfg:
        raise HTTPException(status_code=400, detail="Configuração Asaas não encontrada para este mentor")

    base = "https://api-sandbox.asaas.com/v3" if cfg.sandbox else "https://api.asaas.com/v3"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "access_token": cfg.api_key,
    }

    def _enrich(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched = []
        for it in items:
            it2 = dict(it)
            it2["isPaid"] = _is_paid(it2.get("status"))
            it2["paidAt"] = _extract_paid_at(it2)  # 'YYYY-MM-DD' se existir
            enriched.append(it2)
        return enriched

    items: List[Dict[str, Any]] = []
    source: str = "none"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1) Busca exata por externalReference da competência
        params_xref = {
            "externalReference": f"student:{st.id}:{competencia}",
            "limit": 100,
            "offset": 0,
        }
        r_xref = await client.get(f"{base}/payments", params=params_xref, headers=headers)
        if r_xref.status_code >= 400:
            raise HTTPException(status_code=502, detail={"asaas": r_xref.text, "status": r_xref.status_code})
        data_xref = r_xref.json() or {}
        items_xref = data_xref.get("data") or data_xref.get("items") or []
        if items_xref:
            items = _enrich(items_xref)
            source = "xref"

        # 2) Busca por externalReference do aluno, limitada ao mês, se não achou na #1
        if not items:
            params_gen = {
                "externalReference": f"student:{st.id}",
                "limit": 100,
                "offset": 0,
                "dueDate[ge]": dt_ini.isoformat(),
                "dueDate[le]": dt_fim.isoformat(),
            }
            r_gen = await client.get(f"{base}/payments", params=params_gen, headers=headers)
            if r_gen.status_code >= 400:
                raise HTTPException(status_code=502, detail={"asaas": r_gen.text, "status": r_gen.status_code})
            data_gen = r_gen.json() or {}
            items_gen = data_gen.get("data") or data_gen.get("items") or []
            if items_gen:
                items = _enrich(items_gen)
                source = "gen"

        # 3) Fallback por customer (janela do mês)
        if not items:
            if not st.asaas_customer_id:
                raise HTTPException(status_code=404, detail="Aluno sem customer vinculado na Asaas")
            params_cust = {
                "customer": st.asaas_customer_id,
                "limit": 100,
                "offset": 0,
                "dueDate[ge]": dt_ini.isoformat(),
                "dueDate[le]": dt_fim.isoformat(),
            }
            r_cust = await client.get(f"{base}/payments", params=params_cust, headers=headers)
            if r_cust.status_code >= 400:
                raise HTTPException(status_code=502, detail={"asaas": r_cust.text, "status": r_cust.status_code})
            data_cust = r_cust.json() or {}
            items_cust = data_cust.get("data") or data_cust.get("items") or []
            if items_cust:
                items = _enrich(items_cust)
                source = "customer"

    if not items:
        # nada encontrado no mês
        raise HTTPException(status_code=404, detail="Nenhum pagamento encontrado na competência")

    # --- CONCILIAÇÃO LOCAL ---
    if reconcile:
        rpg = await db.execute(
            select(Pagamento).where(
                and_(
                    Pagamento.mentor_id == me.id,
                    Pagamento.student_id == st.id,
                    Pagamento.competencia == competencia,
                )
            )
        )
        pg = rpg.scalar_one_or_none()
        if pg:
            # pega sempre o melhor candidato: pago > pendente > qualquer
            paid_item = next((it for it in items if it.get("isPaid")), None)
            pending_item = next((it for it in items if (it.get("status") or "").upper() == "PENDING"), None)
            any_item = items[0]

            if paid_item:
                pg.status_pagamento = "pago"
                # paid_at (prioriza clientPaymentDate)
                paid_at_iso = paid_item.get("paidAt")  # 'YYYY-MM-DD'
                if paid_at_iso:
                    try:
                        pg.paid_at = datetime.strptime(paid_at_iso, "%Y-%m-%d")
                    except Exception:
                        pg.paid_at = datetime.fromisoformat(paid_at_iso)
                # method
                m = _extract_method(paid_item)
                if m:
                    pg.method = m
                # asaas_payment_id
                pid = (paid_item.get("id") or "").strip()
                if pid:
                    pg.asaas_payment_id = pid

            elif pending_item:
                if pg.status_pagamento != "pendente":
                    pg.status_pagamento = "pendente"
                # se ainda não tinha vinculado o asaas_payment_id, vincula
                pid = (pending_item.get("id") or "").strip()
                if pid and not pg.asaas_payment_id:
                    pg.asaas_payment_id = pid
                # método (opcional)
                m = _extract_method(pending_item)
                if m and not pg.method:
                    pg.method = m

            else:
                # fallback: não pago e não pendente — mantém o que já tem,
                # mas se achar OVERDUE, pode marcar como atrasado (opcional)
                st0 = (any_item.get("status") or "").upper()
                if st0 == "OVERDUE" and pg.status_pagamento not in ("pago", "pendente"):
                    pg.status_pagamento = "atrasado"
                pid = (any_item.get("id") or "").strip()
                if pid and not pg.asaas_payment_id:
                    pg.asaas_payment_id = pid
                m = _extract_method(any_item)
                if m and not pg.method:
                    pg.method = m

            await db.commit()
            await db.refresh(pg)

    return {
        "object": "list",
        "source": source,
        "hasMore": False,
        "totalCount": len(items),
        "limit": 100,
        "offset": 0,
        "data": items,
    }