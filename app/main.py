# -*- coding: utf-8 -*-
"""
Aplicacao FastAPI principal
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.config import settings, get_static_path
from app.database import db
from app.api import falhas, resultados, pesquisas


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle da aplicacao"""
    # Startup: Inicializar tabelas
    await db.init_tables()
    print(f" {settings.APP_NAME} iniciado!")
    print(f"=Ê Banco de dados: {db.db_path}")

    yield

    # Shutdown
    print("=K Aplicacao encerrada")


# Criar aplicacao FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Montar pasta static
static_path = get_static_path()
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Incluir routers da API
app.include_router(falhas.router, prefix=settings.API_PREFIX)
app.include_router(resultados.router, prefix=settings.API_PREFIX)
app.include_router(pesquisas.router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    """Rota principal - retorna o dashboard HTML"""
    return FileResponse(str(static_path / "index.html"))


@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.VERSION
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
