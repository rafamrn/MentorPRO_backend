# app/asgi.py
import sys, asyncio

# Troca o event loop no Windows ANTES de importar o resto
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Agora importe sua aplicação normalmente
from app.main import app  # noqa: E402
