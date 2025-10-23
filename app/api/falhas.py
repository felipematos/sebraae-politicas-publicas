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
    - searches_completed: numero de buscas completadas ou com erro
    - searches_in_progress: numero de buscas em processamento
    - searches_pending: numero de buscas pendentes
    - total_buscas_enfileiradas: total de buscas enfileiradas (para calculo de progresso)
    - max_searches: numero maximo de buscas esperado (configuracao geral)
    - num_ferramentas: numero distinct de ferramentas utilizadas
    - num_idiomas: numero distinct de idiomas utilizados
    """
    from app.config import settings

    query = """
    SELECT
        f.id,
        f.titulo,
        f.pilar,
        f.descricao,
        f.dica_busca,
        COUNT(DISTINCT r.id) as total_resultados,
        COALESCE(AVG(r.confidence_score), 0.0) as confidence_medio,
        COALESCE(SUM(CASE WHEN fp.status IN ('completa', 'erro') THEN 1 ELSE 0 END), 0) as searches_completed,
        COALESCE(SUM(CASE WHEN fp.status = 'processando' THEN 1 ELSE 0 END), 0) as searches_in_progress,
        COALESCE(SUM(CASE WHEN fp.status = 'pendente' THEN 1 ELSE 0 END), 0) as searches_pending,
        COALESCE(SUM(CASE WHEN fp.status IN ('completa', 'erro', 'processando', 'pendente') THEN 1 ELSE 0 END), 0) as total_buscas_enfileiradas,
        COUNT(DISTINCT fp.ferramenta) as num_ferramentas,
        COUNT(DISTINCT fp.idioma) as num_idiomas
    FROM falhas_mercado f
    LEFT JOIN resultados_pesquisa r ON f.id = r.falha_id
    LEFT JOIN fila_pesquisas fp ON f.id = fp.falha_id
    """

    if pilar:
        query += f" WHERE f.pilar LIKE '%{pilar}%'"

    query += " GROUP BY f.id ORDER BY f.id"
    query += f" LIMIT {limit} OFFSET {skip}"

    falhas = await db.fetch_all(query)

    # Adicionar max_searches a cada falha
    result = []
    for falha in falhas:
        falha_dict = dict(falha)
        falha_dict['max_searches'] = settings.MAX_BUSCAS_POR_FALHA
        result.append(falha_dict)

    return result


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
