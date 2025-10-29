# app/integrations/asaas_client.py
from __future__ import annotations
from typing import Optional, Dict, Any
import httpx

class AsaasClient:
    def __init__(self, api_key: str, sandbox: bool = True, timeout: float = 20.0):
        self.api_key = api_key
        self.base_url = "https://api-sandbox.asaas.com/v3" if sandbox else "https://api.asaas.com/v3"
        self._timeout = timeout
        self._headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "access_token": self.api_key,
        }

    async def create_customer(self, *, name: str, cpf_cnpj: Optional[str] = None,
                              email: Optional[str] = None, mobile_phone: Optional[str] = None,
                              extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {
            "name": name,
            "cpfCnpj": (cpf_cnpj or "").strip() or None,
            "email": (email or "").strip() or None,
            "mobilePhone": (mobile_phone or "").strip() or None,
        }
        if extra:
            payload |= {k: v for k, v in extra.items() if v not in (None, "", [])}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(f"{self.base_url}/customers", json=payload, headers=self._headers)
            # Se já existir, Asaas costuma retornar 409; devolvemos o corpo p/ você logar/decidir
            if r.status_code >= 400:
                # Tenta devolver o JSON de erro do Asaas
                try:
                    data = r.json()
                except Exception:
                    data = {"error": r.text}
                data["_status_code"] = r.status_code
                raise AsaasError("create_customer_failed", data)
            return r.json()

class AsaasError(RuntimeError):
    def __init__(self, code: str, data: Any):
        super().__init__(code)
        self.code = code
        self.data = data
