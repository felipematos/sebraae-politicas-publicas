# -*- coding: utf-8 -*-
"""
Aplicacao FastAPI principal
"""
import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.config import settings, get_static_path
from app.database import db
from app.api import falhas, resultados, pesquisas, health_check, config, vector_search
from app.agente.processador import Processador


# Variaveis globais para controle do worker
worker_task = None


async def worker_processador():
    """
    Task assincron que processa fila continuamente
    Roda a cada intervalo (default 30 segundos)
    """
    processador = Processador(max_workers=3)
    intervalo = 30  # segundos entre iteracoes

    print("[WORKER] Iniciado processador de fila...")

    try:
        while True:
            try:
                # Processar lote pendente
                await processador.processar_lote()

                # Aguardar antes da proxima iteracao
                await asyncio.sleep(intervalo)
            except Exception as e:
                print(f"[WORKER] Erro ao processar lote: {e}")
                # Continuar processando mesmo com erros
                await asyncio.sleep(intervalo)

    except asyncio.CancelledError:
        print("[WORKER] Processador encerrado")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle da aplicacao"""
    global worker_task

    # Startup: Inicializar tabelas
    await db.init_tables()
    print(f"OK {settings.APP_NAME} iniciado!")
    print(f"DB {db.db_path}")

    # Iniciar worker em background
    worker_task = asyncio.create_task(worker_processador())

    yield

    # Shutdown: Cancelar worker
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    print("Aplicacao encerrada")


# Criar aplicacao FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Incluir routers da API
app.include_router(falhas.router, prefix=settings.API_PREFIX)
app.include_router(resultados.router, prefix=settings.API_PREFIX)
app.include_router(pesquisas.router, prefix=settings.API_PREFIX)
app.include_router(health_check.router, prefix=settings.API_PREFIX)
app.include_router(config.router, prefix=settings.API_PREFIX)
app.include_router(vector_search.router)  # Sem prefix pois as rotas já têm /api/

# Montar pasta static
try:
    static_path = get_static_path()
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
except Exception as e:
    print(f"Aviso: static files nao montados: {e}")


@app.get("/")
async def root():
    """Rota principal - retorna o dashboard HTML"""
    try:
        return FileResponse(str(get_static_path() / "index.html"))
    except:
        return {"message": "Dashboard nao encontrado. Acesse /api/falhas"}


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
