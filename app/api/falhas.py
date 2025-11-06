# -*- coding: utf-8 -*-
"""
Endpoints para gerenciamento de falhas de mercado
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any

from app.database import (
    get_falhas_mercado,
    get_falha_by_id,
    get_resultados_by_falha,
    get_estatisticas_falha,
    db
)
from app.schemas import FalhaResponse, FalhaComResultados, EstatisticasFalhaResponse

router = APIRouter(tags=["Falhas"])


@router.get("/falhas")
async def listar_falhas(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    pilar: Optional[str] = None
) -> Dict[str, Any]:
    """
    Listar todas as falhas de mercado com paginacao, filtros e estatisticas de resultados

    - **skip**: Numero de registros a pular (default: 0)
    - **limit**: Numero maximo de registros a retornar (default: 50, max: 100)
    - **pilar**: Filtrar por pilar especifico (opcional)

    Retorna um objeto com 'dados' contendo array de falhas com:
    - id, titulo, pilar, descricao, dica_busca
    - total_resultados: quantidade de resultados encontrados
    - confidence_medio: score mediano dos resultados (mais robusto que média)
    - searches_completed: numero de buscas completadas ou com erro
    - searches_in_progress: numero de buscas em processamento
    - searches_pending: numero de buscas pendentes
    - total_buscas_enfileiradas: total de buscas enfileiradas (para calculo de progresso)
    - max_searches: numero maximo de buscas esperado (configuracao geral)
    - num_ferramentas: numero distinct de ferramentas que efetivamente encontraram resultados
    - num_idiomas: numero distinct de idiomas em que resultados foram encontrados
    - num_queries_processadas: numero distinct de queries unicas que foram completadas
      (0 para falhas nao iniciadas, cresce conforme buscas sao executadas)
    """
    from app.config import settings
    import statistics

    query = """
    SELECT
        f.id,
        f.titulo,
        f.pilar,
        f.descricao,
        f.dica_busca,
        COUNT(DISTINCT r.id) as total_resultados,
        COALESCE(SUM(CASE WHEN fp.status IN ('completa', 'erro') THEN 1 ELSE 0 END), 0) as searches_completed,
        COALESCE(SUM(CASE WHEN fp.status = 'processando' THEN 1 ELSE 0 END), 0) as searches_in_progress,
        COALESCE(SUM(CASE WHEN fp.status = 'pendente' THEN 1 ELSE 0 END), 0) as searches_pending,
        COALESCE(SUM(CASE WHEN fp.status IN ('completa', 'erro', 'processando', 'pendente') THEN 1 ELSE 0 END), 0) as total_buscas_enfileiradas,
        (SELECT COUNT(*) FROM (
            SELECT DISTINCT ferramenta_origem FROM resultados_pesquisa WHERE falha_id = f.id
            UNION
            SELECT DISTINCT ferramenta FROM fila_pesquisas WHERE falha_id = f.id
        )) as num_ferramentas,
        COUNT(DISTINCT CASE WHEN r.id IS NOT NULL THEN r.idioma END) as num_idiomas,
        (SELECT COUNT(DISTINCT query) FROM fila_pesquisas WHERE falha_id = f.id AND status IN ('completa', 'erro', 'processando', 'pendente')) as num_queries_processadas
    FROM falhas_mercado f
    LEFT JOIN resultados_pesquisa r ON f.id = r.falha_id
    LEFT JOIN fila_pesquisas fp ON f.id = fp.falha_id
    """

    if pilar:
        query += f" WHERE f.pilar LIKE '%{pilar}%'"

    query += " GROUP BY f.id ORDER BY f.id"
    query += f" LIMIT {limit} OFFSET {skip}"

    falhas = await db.fetch_all(query)

    # Calcular mediana de confidence_score para cada falha
    result = []
    for falha in falhas:
        falha_dict = dict(falha)
        falha_dict['max_searches'] = settings.MAX_BUSCAS_POR_FALHA

        # Buscar scores para calcular mediana
        scores_query = """
        SELECT confidence_score
        FROM resultados_pesquisa
        WHERE falha_id = ?
        AND confidence_score IS NOT NULL
        """
        scores_result = await db.fetch_all(scores_query, (falha['id'],))

        if scores_result and len(scores_result) > 0:
            scores = [float(row['confidence_score']) for row in scores_result]
            falha_dict['confidence_medio'] = round(statistics.median(scores), 3)
        else:
            falha_dict['confidence_medio'] = 0.0

        result.append(falha_dict)

    # Retornar wrapped em "dados" para compatibilidade com frontend
    return {"dados": result}


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
async def obter_resultados_falha(
    falha_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    Obter resultados de pesquisa para uma falha com paginação

    - **page**: Número da página (começa em 1)
    - **page_size**: Quantidade de resultados por página (default: 20, max: 100)
    """
    # Verificar se falha existe
    falha = await get_falha_by_id(falha_id)
    if not falha:
        raise HTTPException(status_code=404, detail=f"Falha {falha_id} nao encontrada")

    # Calcular offset
    offset = (page - 1) * page_size

    # Obter contagem total
    query_count = """
    SELECT COUNT(*) as total
    FROM resultados_pesquisa
    WHERE falha_id = :falha_id
    """
    total_result = await db.fetch_one(query_count, {"falha_id": falha_id})
    total = total_result["total"] if total_result else 0

    # Obter resultados paginados
    query_resultados = """
    SELECT
        id,
        falha_id,
        titulo,
        descricao,
        fonte_url,
        fonte_tipo,
        pais_origem,
        idioma,
        confidence_score,
        num_ocorrencias,
        ferramenta_origem,
        criado_em,
        titulo_pt,
        descricao_pt,
        titulo_en,
        descricao_en
    FROM resultados_pesquisa
    WHERE falha_id = :falha_id
    ORDER BY confidence_score DESC, id DESC
    LIMIT :limit OFFSET :offset
    """

    resultados = await db.fetch_all(
        query_resultados,
        {"falha_id": falha_id, "limit": page_size, "offset": offset}
    )

    # Calcular total de páginas
    total_pages = (total + page_size - 1) // page_size

    return {
        "falha": falha,
        "resultados": [dict(r) for r in resultados],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }
