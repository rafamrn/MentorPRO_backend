from typing import Any
import httpx
from app.core.config import settings

class AsaasClient:
    def __init__(self, api_key: str, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url or settings.ASAAS_API_BASE
        self._headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "access_token": self.api_key,
        }

    async def create_customer(self, data: dict[str, Any]) -> dict[str, Any]:
        # Stub — implemente chamadas reais aqui
        # Exemplo:
        # async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=30) as client:
        #     r = await client.post("/customers", json=data)
        #     r.raise_for_status()
        #     return r.json()
        raise NotImplementedError("Implementar integração real com Asaas")