# -*- coding: utf-8 -*-
"""
Endpoints para análise e reanálise de resultados
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.database import db
from app.agente.avaliador import Avaliador

router = APIRouter(tags=["Análise"])


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


@router.post("/api/analise/reanalisar")
async def reanalisar_resultados(request: ReanalisarRequest):
    """
    Reanalisa todos os resultados existentes recalculando os confidence scores

    Args:
        request: Configurações de reanálise

    Returns:
        Estatísticas da reanálise realizada
    """
    try:
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

        if not resultados:
            return {
                "total_reanalisadas": 0,
                "scores_atualizados": 0,
                "modo_utilizado": request.modo_avaliacao,
                "mensagem": "Nenhum resultado encontrado para reanalisar"
            }

        # Inicializar avaliador
        avaliador = Avaliador()

        scores_atualizados = 0

        # Processar cada resultado
        for resultado in resultados:
            # Converter para dicionário
            resultado_dict = dict(resultado)

            # Calcular novo score
            if request.avaliar_profundamente and request.modo_avaliacao != "gratuito":
                # TODO: Implementar avaliação profunda com LLM
                # Por enquanto, usar avaliação heurística
                novo_score = await avaliador.avaliar(
                    resultado=resultado_dict,
                    query=resultado_dict.get("query", ""),
                    num_ocorrencias=resultado_dict.get("num_ocorrencias", 1),
                    usar_rag=False
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

        return {
            "total_reanalisadas": len(resultados),
            "scores_atualizados": scores_atualizados,
            "modo_utilizado": request.modo_avaliacao,
            "mensagem": f"Reanálise concluída com sucesso! {scores_atualizados} scores foram atualizados."
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao reanalisar resultados: {str(e)}"
        )
