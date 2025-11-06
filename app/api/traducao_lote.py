# -*- coding: utf-8 -*-
"""
Endpoints para tradução em lote com background processing
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict
import uuid
from datetime import datetime
import asyncio

from app.database import db
from app.integracao.openrouter_api import OpenRouterClient
from app.utils.logger import logger

router = APIRouter(tags=["Tradução em Lote"])

# Dicionário global para rastrear jobs de tradução em background
traducao_jobs: Dict[str, dict] = {}


class TraduzirLoteRequest(BaseModel):
    """Schema para solicitar tradução em lote"""
    max_concurrent: int = 10  # Máximo de traduções simultâneas


async def processar_traducoes_background(job_id: str, max_concurrent: int = 10):
    """
    Processa traduções em background com atualização de progresso

    Args:
        job_id: ID único do job
        max_concurrent: Número máximo de traduções simultâneas
    """
    try:
        logger.info(f"[JOB {job_id}] Iniciando traduções em background")

        # Buscar resultados sem tradução
        query = """
        SELECT id, falha_id, titulo, descricao, idioma
        FROM resultados_pesquisa
        WHERE idioma != 'pt'
        AND (titulo_pt IS NULL OR titulo_pt = '')
        ORDER BY id
        """

        resultados = await db.fetch_all(query)
        total = len(resultados)

        if total == 0:
            traducao_jobs[job_id].update({
                "status": "concluido",
                "progresso": 100,
                "total_traduzidas": 0,
                "erros": 0,
                "mensagem": "Nenhum resultado para traduzir",
                "concluido_em": datetime.now().isoformat()
            })
            return

        # Atualizar status
        traducao_jobs[job_id].update({
            "status": "processando",
            "total": total,
            "processados": 0,
            "progresso": 0,
            "traduzidas": 0,
            "erros": 0
        })

        traduzidas = 0
        erros = 0
        processados = 0

        # Criar semáforo para controlar concorrência
        semaphore = asyncio.Semaphore(max_concurrent)

        async def traduzir_um_resultado(resultado):
            """Traduz um resultado individualmente"""
            nonlocal traduzidas, erros, processados

            async with semaphore:
                try:
                    resultado_dict = dict(resultado)
                    idioma_origem = resultado_dict.get('idioma', 'en')

                    # Traduzir com OpenRouterClient
                    async with OpenRouterClient() as client:
                        titulo_pt = await client.traduzir_texto(
                            texto=resultado_dict['titulo'],
                            idioma_alvo="pt",
                            idioma_origem=idioma_origem
                        )

                        descricao_pt = await client.traduzir_texto(
                            texto=resultado_dict['descricao'],
                            idioma_alvo="pt",
                            idioma_origem=idioma_origem
                        )

                    # Atualizar no banco
                    if titulo_pt and descricao_pt:
                        await db.execute(
                            """
                            UPDATE resultados_pesquisa
                            SET titulo_pt = ?, descricao_pt = ?, atualizado_em = CURRENT_TIMESTAMP
                            WHERE id = ?
                            """,
                            (titulo_pt.strip(), descricao_pt.strip(), resultado_dict['id'])
                        )
                        traduzidas += 1
                    else:
                        erros += 1

                except Exception as e:
                    erros += 1
                    logger.error(f"[JOB {job_id}] Erro ao traduzir resultado {resultado_dict.get('id')}: {e}")

                finally:
                    processados += 1
                    # Atualizar progresso
                    progresso = int((processados / total) * 100)
                    traducao_jobs[job_id].update({
                        "processados": processados,
                        "progresso": progresso,
                        "traduzidas": traduzidas,
                        "erros": erros
                    })

        # Processar todos os resultados em paralelo (controlado pelo semáforo)
        await asyncio.gather(*[traduzir_um_resultado(r) for r in resultados])

        # Finalizar job
        traducao_jobs[job_id].update({
            "status": "concluido",
            "progresso": 100,
            "total_traduzidas": traduzidas,
            "total_erros": erros,
            "mensagem": f"Tradução concluída! {traduzidas} resultados traduzidos, {erros} erros.",
            "concluido_em": datetime.now().isoformat()
        })

        logger.info(f"[JOB {job_id}] Tradução concluída: {traduzidas}/{total} resultados traduzidos")

    except Exception as e:
        logger.error(f"[JOB {job_id}] Erro fatal na tradução: {e}")
        traducao_jobs[job_id].update({
            "status": "erro",
            "erro": str(e),
            "concluido_em": datetime.now().isoformat()
        })


@router.post("/api/traducao/lote/iniciar")
async def iniciar_traducao_lote(request: TraduzirLoteRequest, background_tasks: BackgroundTasks):
    """
    Inicia tradução em lote de todos os resultados sem tradução

    Args:
        request: Configurações de tradução (max_concurrent)
        background_tasks: FastAPI background tasks

    Returns:
        Job ID para acompanhamento do progresso
    """
    try:
        # Gerar job ID único
        job_id = str(uuid.uuid4())

        # Criar registro do job
        traducao_jobs[job_id] = {
            "job_id": job_id,
            "status": "iniciado",
            "progresso": 0,
            "total": 0,
            "processados": 0,
            "traduzidas": 0,
            "erros": 0,
            "max_concurrent": request.max_concurrent,
            "iniciado_em": datetime.now().isoformat()
        }

        # Adicionar tarefa em background
        background_tasks.add_task(
            processar_traducoes_background,
            job_id,
            request.max_concurrent
        )

        logger.info(f"[JOB {job_id}] Tradução em lote iniciada (max_concurrent={request.max_concurrent})")

        return {
            "job_id": job_id,
            "status": "iniciado",
            "mensagem": "Tradução em lote iniciada. Use o job_id para acompanhar o progresso."
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao iniciar tradução em lote: {str(e)}"
        )


@router.get("/api/traducao/lote/status/{job_id}")
async def obter_status_traducao(job_id: str):
    """
    Obtém o status de um job de tradução em lote

    Args:
        job_id: ID do job de tradução

    Returns:
        Status atual do job
    """
    if job_id not in traducao_jobs:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    return traducao_jobs[job_id]
