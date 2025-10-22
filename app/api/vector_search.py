# -*- coding: utf-8 -*-
"""
APIs REST para busca semântica usando banco vetorial
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from app.config import settings
from app.vector.vector_store import get_vector_store

router = APIRouter()


@router.get("/api/search/resultados")
async def search_resultados(
    q: str = Query(..., min_length=1, max_length=1000),
    limit: int = Query(10, ge=1, le=50)
) -> Dict[str, Any]:
    """
    Busca semântica em resultados de pesquisa

    Args:
        q: Query para buscar
        limit: Número máximo de resultados

    Returns:
        Lista de resultados similares com scores
    """
    if not settings.RAG_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Busca semântica não está habilitada"
        )

    try:
        vector_store = await get_vector_store()

        # Buscar resultados similares
        similares = await vector_store.search_resultados(q, n_results=limit)

        # Filtrar por threshold
        resultados = [
            {
                "metadata": meta,
                "similarity": round(sim, 3)
            }
            for meta, sim in similares
            if sim >= settings.RAG_SIMILARITY_THRESHOLD
        ]

        return {
            "query": q,
            "total_results": len(resultados),
            "results": resultados,
            "threshold": settings.RAG_SIMILARITY_THRESHOLD
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")


@router.get("/api/search/falhas")
async def search_falhas(
    q: str = Query(..., min_length=1, max_length=1000),
    limit: int = Query(5, ge=1, le=20)
) -> Dict[str, Any]:
    """
    Busca semântica em falhas de mercado

    Args:
        q: Query para buscar
        limit: Número máximo de resultados

    Returns:
        Lista de falhas similares com scores
    """
    if not settings.RAG_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Busca semântica não está habilitada"
        )

    try:
        vector_store = await get_vector_store()

        # Buscar falhas similares
        similares = await vector_store.search_falhas(q, n_results=limit)

        # Filtrar por threshold
        resultados = [
            {
                "metadata": meta,
                "similarity": round(sim, 3)
            }
            for meta, sim in similares
            if sim >= settings.RAG_SIMILARITY_THRESHOLD
        ]

        return {
            "query": q,
            "total_results": len(resultados),
            "results": resultados,
            "threshold": settings.RAG_SIMILARITY_THRESHOLD
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")


@router.get("/api/search/similar-queries")
async def similar_queries(
    q: str = Query(..., min_length=1, max_length=1000),
    limit: int = Query(3, ge=1, le=10)
) -> Dict[str, Any]:
    """
    Encontra queries similares já executadas

    Args:
        q: Query para comparar
        limit: Número máximo de queries similares

    Returns:
        Lista de queries similares com scores
    """
    if not settings.RAG_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Busca semântica não está habilitada"
        )

    try:
        vector_store = await get_vector_store()

        # Buscar queries similares
        similares = await vector_store.find_similar_queries(q, n_results=limit)

        # Filtrar por threshold
        resultados = [
            {
                "query": query,
                "metadata": meta,
                "similarity": round(sim, 3)
            }
            for query, meta, sim in similares
            if sim >= settings.RAG_SIMILARITY_THRESHOLD
        ]

        return {
            "input_query": q,
            "total_similar": len(resultados),
            "results": resultados,
            "threshold": settings.RAG_SIMILARITY_THRESHOLD
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")


@router.get("/api/falhas/{falha_id}/related")
async def get_related_falhas(
    falha_id: int,
    limit: int = Query(5, ge=1, le=10)
) -> Dict[str, Any]:
    """
    Encontra falhas relacionadas por similaridade semântica

    Args:
        falha_id: ID da falha de referência
        limit: Número máximo de falhas relacionadas

    Returns:
        Lista de falhas relacionadas
    """
    if not settings.RAG_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Busca semântica não está habilitada"
        )

    try:
        vector_store = await get_vector_store()

        # Buscar falha original para usar como query
        # (Implementação simplificada - em produção, buscaria a falha original)
        # Por enquanto, retornando erro didático
        raise HTTPException(
            status_code=501,
            detail="Endpoint ainda não implementado - necessita busca por ID"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")


@router.get("/api/vector-db/stats")
async def get_vector_db_stats() -> Dict[str, Any]:
    """
    Retorna estatísticas do banco vetorial

    Returns:
        Dicionário com contagens e stats
    """
    if not settings.USAR_VECTOR_DB:
        raise HTTPException(
            status_code=503,
            detail="Banco vetorial não está habilitado"
        )

    try:
        vector_store = await get_vector_store()
        stats = vector_store.get_stats()

        return {
            "vector_db_enabled": settings.USAR_VECTOR_DB,
            "rag_enabled": settings.RAG_ENABLED,
            "embedding_model": settings.EMBEDDING_MODEL,
            "similarity_threshold": settings.RAG_SIMILARITY_THRESHOLD,
            "documents": {
                "resultados": stats.get('resultados_count', 0),
                "falhas": stats.get('falhas_count', 0),
                "queries": stats.get('queries_count', 0),
                "total": sum([
                    stats.get('resultados_count', 0),
                    stats.get('falhas_count', 0),
                    stats.get('queries_count', 0)
                ])
            },
            "cache": stats.get('embedding_cache_stats', {})
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter stats: {str(e)}")
