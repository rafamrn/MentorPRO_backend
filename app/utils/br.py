# app/utils/br.py
import re

def only_digits(s: str | None) -> str:
    return re.sub(r"\D+", "", s or "")

def normalize_cpf_cnpj(value: str | None) -> str | None:
    digits = only_digits(value)
    if len(digits) in (11, 14):
        return digits
    return None  # deixa None se vier inválido/ausente

def normalize_mobile_phone(value: str | None) -> str | None:
    # Asaas aceita strings como "11987654321" (DDI opcional); vamos enviar só dígitos
    digits = only_digits(value)
    return digits or None
