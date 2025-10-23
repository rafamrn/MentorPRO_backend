from fastapi import APIRouter, Request, Response, status

router = APIRouter()

@router.post("/asaas", status_code=status.HTTP_200_OK)
async def asaas_webhook(request: Request):
    payload = await request.json()
    # TODO: validar assinatura do Asaas e rotear evento
    # Por enquanto só ecoa.
    return {"received": True, "event": payload.get("event"), "id": payload.get("id")}