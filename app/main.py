from fastapi import FastAPI
from app.core.logging import configure_logging
from app.api.v1.router import api_router

app = FastAPI(title="PA Copilot API", version="0.0.1")

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(api_router, prefix="/v1")