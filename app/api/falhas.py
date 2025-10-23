# -*- coding: utf-8 -*-
"""
Endpoints para gerenciamento de falhas de mercado
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.database import (
    get_falhas_mercado,
    get_falha_by_id,
    get_resultados_by_falha,
    get_estatisticas_falha,
    db
)
from app.schemas import FalhaResponse, FalhaComResultados, EstatisticasFalhaResponse

router = APIRouter(tags=["Falhas"])


@router.get("/falhas", response_model=List[dict])
async def listar_falhas(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    pilar: Optional[str] = None
):
    """
    Listar todas as falhas de mercado com paginacao, filtros e estatisticas de resultados

    - **skip**: Numero de registros a pular (default: 0)
    - **limit**: Numero maximo de registros a retornar (default: 50, max: 100)
    - **pilar**: Filtrar por pilar especifico (opcional)

    Retorna cada falha com:
    - id, titulo, pilar, descricao, dica_busca
    - total_resultados: quantidade de resultados encontrados
    - confidence_medio: score medio dos resultados
    """
    query = """
    SELECT
        f.id,
        f.titulo,
        f.pilar,
        f.descricao,
        f.dica_busca,
        COUNT(r.id) as total_resultados,
        COALESCE(AVG(r.confidence_score), 0.0) as confidence_medio
    FROM falhas_mercado f
    LEFT JOIN resultados_pesquisa r ON f.id = r.falha_id
    """

    if pilar:
        query += f" WHERE f.pilar LIKE '%{pilar}%'"

    query += " GROUP BY f.id ORDER BY f.id"
    query += f" LIMIT {limit} OFFSET {skip}"

    falhas = await db.fetch_all(query)
    return [dict(falha) for falha in falhas]


@router.get("/falhas/{falha_id}", response_model=FalhaResponse)
async def obter_falha(falha_id: int):
    """
    Obter detalhes de uma falha especifica por ID
    """
    falha = await get_falha_by_id(falha_id)

    if not falha:
        raise HTTPException(status_code=404, detail=f"Falha {falha_id} nao encontrada")

    return falha


@router.get("/falhas/{falha_id}/resultados")
async def obter_resultados_falha(falha_id: int):
    """
    Obter todos os resultados de pesquisa para uma falha
    """
    # Verificar se falha existe
    falha = await get_falha_by_id(falha_id)
    if not falha:
        raise HTTPException(status_code=404, detail=f"Falha {falha_id} nao encontrada")

    # Obter resultados
    resultados = await get_resultados_by_falha(falha_id)

    # Obter estatisticas
    stats = await get_estatisticas_falha(falha_id)

    return {
        "falha": falha,
        "resultados": resultados,
        "total_resultados": stats["total_resultados"],
        "confidence_medio": stats["confidence_medio"],
        "top_paises": stats["top_paises"],
        "idiomas": stats["idiomas"]
    }
