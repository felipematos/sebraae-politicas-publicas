# -*- coding: utf-8 -*-
"""
Endpoints para análise e reanálise de resultados
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict
import asyncio
import uuid
from datetime import datetime

from app.database import db
from app.agente.avaliador import Avaliador
from app.utils.logger import logger

router = APIRouter(tags=["Análise"])

# Dicionário global para rastrear jobs de reanálise em background
reanalisar_jobs: Dict[str, dict] = {}


class ReanalisarRequest(BaseModel):
    """Schema para solicitar reanálise de resultados"""
    avaliar_profundamente: bool = False
    modo_avaliacao: str = "gratuito"  # gratuito, balanceado, premium


@router.get("/api/analise/estimar")
async def estimar_custo_tempo(
    num_fontes: int = Query(..., ge=0),
    modo: str = Query("gratuito", regex="^(gratuito|balanceado|premium)$")
):
    """
    Estima custo e tempo para reanálise de resultados

    Args:
        num_fontes: Número de fontes a serem analisadas
        modo: Modo de avaliação (gratuito, balanceado, premium)

    Returns:
        Estimativa de custo, tempo e modelo utilizado
    """
    # Configurações por modo
    configs = {
        "gratuito": {
            "modelo": "Avaliação Heurística (Gratuita)",
            "tempo_por_fonte": 0.1,  # segundos
            "custo_por_fonte": 0.0
        },
        "balanceado": {
            "modelo": "Llama 3.3 70B via OpenRouter",
            "tempo_por_fonte": 2.0,  # segundos
            "custo_por_fonte": 0.002  # ~R$0.002 por fonte (estimativa)
        },
        "premium": {
            "modelo": "Claude 3.5 Sonnet via Anthropic",
            "tempo_por_fonte": 3.0,  # segundos
            "custo_por_fonte": 0.01  # ~R$0.01 por fonte (estimativa)
        }
    }

    config = configs[modo]

    tempo_estimado_segundos = num_fontes * config["tempo_por_fonte"]
    custo_estimado = num_fontes * config["custo_por_fonte"]

    return {
        "num_fontes": num_fontes,
        "modo": modo,
        "modelo": config["modelo"],
        "tempo_estimado_segundos": tempo_estimado_segundos,
        "custo_estimado": custo_estimado
    }


async def processar_reanalisar_background(
    job_id: str,
    avaliar_profundamente: bool,
    modo_avaliacao: str
):
    """
    Processa reanálise em background com atualização de progresso
    """
    try:
        logger.info(f"[JOB {job_id}] Iniciando reanálise em background")

        # Buscar todos os resultados
        query = """
        SELECT
            r.id,
            r.falha_id,
            r.titulo,
            r.descricao,
            r.titulo_pt,
            r.descricao_pt,
            r.fonte_url,
            r.ferramenta_origem as fonte,
            r.idioma,
            r.query,
            r.num_ocorrencias,
            r.confidence_score as score_anterior
        FROM resultados_pesquisa r
        """

        resultados = await db.fetch_all(query)
        total = len(resultados)

        if total == 0:
            reanalisar_jobs[job_id].update({
                "status": "concluido",
                "progresso": 100,
                "total_reanalisadas": 0,
                "scores_atualizados": 0,
                "mensagem": "Nenhum resultado encontrado",
                "concluido_em": datetime.now().isoformat()
            })
            return

        # Atualizar status
        reanalisar_jobs[job_id].update({
            "status": "processando",
            "total": total,
            "processados": 0,
            "progresso": 0
        })

        # Inicializar avaliador
        avaliador = Avaliador()
        scores_atualizados = 0
        erros = 0

        # Processar cada resultado
        for i, resultado in enumerate(resultados, 1):
            try:
                # Converter para dicionário
                resultado_dict = dict(resultado)

                # Calcular novo score
                if avaliar_profundamente and modo_avaliacao != "gratuito":
                    # Avaliação profunda com LLM
                    novo_score = await avaliador.avaliar(
                        resultado=resultado_dict,
                        query=resultado_dict.get("query", ""),
                        num_ocorrencias=resultado_dict.get("num_ocorrencias", 1),
                        usar_rag=True,  # Usar RAG para avaliação profunda
                        usar_llm=True   # Ativar LLM
                    )
                else:
                    # Avaliação heurística padrão (gratuita)
                    novo_score = await avaliador.avaliar(
                        resultado=resultado_dict,
                        query=resultado_dict.get("query", ""),
                        num_ocorrencias=resultado_dict.get("num_ocorrencias", 1),
                        usar_rag=False
                    )

                # Atualizar score no banco se mudou significativamente (diferença > 0.01)
                score_anterior = resultado_dict.get("score_anterior", 0.0)
                if abs(novo_score - score_anterior) > 0.01:
                    await db.execute(
                        """
                        UPDATE resultados_pesquisa
                        SET confidence_score = ?,
                            atualizado_em = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (novo_score, resultado_dict["id"])
                    )
                    scores_atualizados += 1

            except Exception as e:
                erros += 1
                logger.error(f"[JOB {job_id}] Erro ao processar resultado {resultado_dict.get('id')}: {e}")

            # Atualizar progresso a cada resultado
            progresso = int((i / total) * 100)
            reanalisar_jobs[job_id].update({
                "processados": i,
                "progresso": progresso,
                "scores_atualizados": scores_atualizados,
                "erros": erros
            })

            # Pequeno delay para não sobrecarregar o sistema
            if avaliar_profundamente and modo_avaliacao != "gratuito":
                await asyncio.sleep(0.5)  # Delay maior para LLM
            else:
                await asyncio.sleep(0.01)  # Delay mínimo para heurística

        # Finalizar job
        reanalisar_jobs[job_id].update({
            "status": "concluido",
            "progresso": 100,
            "total_reanalisadas": total,
            "scores_atualizados": scores_atualizados,
            "erros": erros,
            "mensagem": f"Reanálise concluída! {scores_atualizados} scores atualizados, {erros} erros.",
            "concluido_em": datetime.now().isoformat()
        })

        logger.info(f"[JOB {job_id}] Reanálise concluída: {scores_atualizados}/{total} scores atualizados")

    except Exception as e:
        logger.error(f"[JOB {job_id}] Erro fatal na reanálise: {e}")
        reanalisar_jobs[job_id].update({
            "status": "erro",
            "erro": str(e),
            "concluido_em": datetime.now().isoformat()
        })


@router.post("/api/analise/reanalisar")
async def reanalisar_resultados(request: ReanalisarRequest, background_tasks: BackgroundTasks):
    """
    Inicia reanálise de todos os resultados em background

    Args:
        request: Configurações de reanálise
        background_tasks: FastAPI background tasks

    Returns:
        Job ID para acompanhamento do progresso
    """
    try:
        # Gerar job ID único
        job_id = str(uuid.uuid4())

        # Criar registro do job
        reanalisar_jobs[job_id] = {
            "job_id": job_id,
            "status": "iniciado",
            "progresso": 0,
            "total": 0,
            "processados": 0,
            "scores_atualizados": 0,
            "erros": 0,
            "modo_avaliacao": request.modo_avaliacao,
            "avaliar_profundamente": request.avaliar_profundamente,
            "iniciado_em": datetime.now().isoformat()
        }

        # Adicionar tarefa em background
        background_tasks.add_task(
            processar_reanalisar_background,
            job_id,
            request.avaliar_profundamente,
            request.modo_avaliacao
        )

        logger.info(f"[JOB {job_id}] Reanálise iniciada em background")

        return {
            "job_id": job_id,
            "status": "iniciado",
            "mensagem": "Reanálise iniciada. Use o job_id para acompanhar o progresso."
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao iniciar reanálise: {str(e)}"
        )


@router.get("/api/analise/reanalisar/status/{job_id}")
async def obter_status_reanalisar(job_id: str):
    """
    Obtém o status de um job de reanálise

    Args:
        job_id: ID do job de reanálise

    Returns:
        Status atual do job
    """
    if job_id not in reanalisar_jobs:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    return reanalisar_jobs[job_id]
