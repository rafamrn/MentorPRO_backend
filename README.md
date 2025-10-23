# MentorPro Backend — Pacote Mínimo

Backend mínimo com FastAPI + SQLAlchemy async, já com **Tenants** e **Students** (escopo por tenant via header `X-Client-Id`), webhook básico do Asaas e client stub.

## Rodar local (dev)

```bash
# Python 3.11+
pip install -e .  # se usar pip>=23 com pyproject, pode ser: pip install -r <generated> (mas aqui usamos pyproject diretamente)
pip install uvicorn

# variáveis (opcional — se não setar, cai para sqlite em /tmp)
cp .env.example .env

# subir
uvicorn app.main:app --reload
# abra http://localhost:8000/docs
```

## Variáveis (.env)

- `DATABASE_URL` — ex.: `postgresql+asyncpg://user:pass@localhost:5432/mentorpro`
- `ENVIRONMENT` — `dev` (cria tabelas automaticamente) ou `prod`
- `ASAAS_API_BASE` — default `https://api.asaas.com/v3`

## Uso rápido

- Crie um tenant:
  - `POST /api/v1/tenants` → retorna `id`
- Use o `id` do tenant no header **X-Client-Id** para operar alunos:
  - `POST /api/v1/students` (com `{"nome": "...", "email": "..."}`)
  - `GET /api/v1/students`

Webhook Asaas: `POST /api/v1/webhooks/asaas` (stub).

> **Atenção:** Este pacote é mínimo (sem JWT). Depois é só plugar autenticação e RBAC.