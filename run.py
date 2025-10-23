import sys, asyncio
if sys.platform.startswith("win"):
    # >>> garante o loop compatível ANTES de criar o loop do uvicorn <<<
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )