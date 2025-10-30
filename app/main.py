# -*- coding: utf-8 -*-
"""
Aplicacao FastAPI principal
"""
import asyncio
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.config import settings, get_static_path, get_chroma_path
from app.database import db
from app.api import falhas, resultados, pesquisas, health_check, config, vector_search, priorizacoes, knowledge_base
from app.agente.processador import Processador
from app.vector.vector_store import get_vector_store
from app.vector.embeddings import EmbeddingClient


# Variaveis globais para controle do worker
worker_task = None
processador_global = None  # Referência global ao processador para pausar/retomar


async def worker_processador():
    """
    Task assincron que processa fila continuamente
    Roda a cada intervalo (default 30 segundos)

    Utiliza processamento paralelo com até 5 workers simultâneos
    para acelerar o processamento da fila de pesquisas

    IMPORTANTE: Inicia em estado PAUSADO. Usuário deve clicar "Pesquisa em Andamento" para começar
    """
    global processador_global
    processador = Processador(max_workers=5)  # Parallelismo: até 5 buscas simultâneas
    processador.ativo = False  # INICIAR EM ESTADO PAUSADO - Usuário controla quando começar
    processador_global = processador  # Armazenar referência global para pausar/retomar

    # Configurar rate limiting para permitir processamento mais rápido
    processador.configurar_rate_limiting(
        delay_minimo=0.3,              # Reduzido de 1.0 para 0.3 segundos
        max_requests_por_minuto=150    # Aumentado de 60 para 150 requests/min
    )

    intervalo = 20  # Reduzido de 30 para 20 segundos entre iterações

    print("[WORKER] Iniciado em estado PAUSADO. Clique 'Pesquisa em Andamento' para começar...")
    print("[WORKER] Rate limiting: 0.3s delay, 150 req/min")

    try:
        while True:
            try:
                # Processar lote em PARALELO (até 5 buscas simultâneas)
                entradas_processadas = await processador.processar_em_paralelo(max_por_lote=20)

                # Log de progresso
                if entradas_processadas > 0:
                    print(f"[WORKER] Processadas {entradas_processadas} entradas em paralelo")

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

    # Inicializar vector store se habilitado
    if settings.RAG_ENABLED or settings.USAR_VECTOR_DB:
        try:
            embedding_client = EmbeddingClient(api_key=settings.OPENAI_API_KEY)
            persist_path = get_chroma_path()
            await get_vector_store(persist_path=persist_path, embedding_client=embedding_client)
            print(f"✓ Vector Store inicializado em {persist_path}")
        except Exception as e:
            print(f"⚠ Aviso: Vector Store não inicializado: {e}")

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
app.include_router(priorizacoes.router)  # Sem prefix pois as rotas já têm /api/priorizacoes
app.include_router(vector_search.router)  # Sem prefix pois as rotas já têm /api/
app.include_router(knowledge_base.router)  # Knowledge base with CSV/MD support

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
