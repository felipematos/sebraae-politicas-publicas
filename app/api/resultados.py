# -*- coding: utf-8 -*-
"""
Endpoints para gerenciamento de resultados de pesquisa
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.database import (
    db,
    get_falha_by_id,
    insert_resultado,
    update_resultado_score,
    delete_resultado
)
from app.utils.hash_utils import gerar_hash_conteudo
from app.schemas import ResultadoCreate, ResultadoUpdate, ResultadoResponse

router = APIRouter(tags=["Resultados"])


@router.get("/resultados", response_model=List[ResultadoResponse])
async def listar_resultados(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    falha_id: Optional[int] = None,
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    max_score: float = Query(1.0, ge=0.0, le=1.0),
    idioma: Optional[str] = None
):
    """
    Listar resultados de pesquisa com filtros
    """
    query = "SELECT * FROM resultados_pesquisa WHERE 1=1"

    if falha_id:
        query += f" AND falha_id = {falha_id}"

    query += f" AND confidence_score BETWEEN {min_score} AND {max_score}"

    if idioma:
        query += f" AND idioma = '{idioma}'"

    query += f" ORDER BY confidence_score DESC LIMIT {limit} OFFSET {skip}"

    resultados = await db.fetch_all(query)
    return resultados


@router.get("/resultados/{resultado_id}", response_model=ResultadoResponse)
async def obter_resultado(resultado_id: int):
    """
    Obter detalhes de um resultado especifico
    """
    resultado = await db.fetch_one(
        "SELECT * FROM resultados_pesquisa WHERE id = ?",
        (resultado_id,)
    )

    if not resultado:
        raise HTTPException(status_code=404, detail="Resultado nao encontrado")

    return resultado


@router.post("/resultados", response_model=ResultadoResponse, status_code=201)
async def criar_resultado(resultado: ResultadoCreate):
    """
    Criar um novo resultado manualmente
    """
    # Verificar se falha existe
    falha = await get_falha_by_id(resultado.falha_id)
    if not falha:
        raise HTTPException(status_code=404, detail="Falha nao encontrada")

    # Gerar hash do conteudo
    hash_conteudo = gerar_hash_conteudo(
        resultado.titulo,
        resultado.descricao or "",
        resultado.fonte_url
    )

    # Criar resultado
    resultado_data = {
        "falha_id": resultado.falha_id,
        "titulo": resultado.titulo,
        "descricao": resultado.descricao,
        "fonte_url": resultado.fonte_url,
        "fonte_tipo": resultado.fonte_tipo,
        "pais_origem": resultado.pais_origem,
        "idioma": resultado.idioma,
        "confidence_score": resultado.confidence_score,
        "ferramenta_origem": "manual",
        "hash_conteudo": hash_conteudo
    }

    resultado_id = await insert_resultado(resultado_data)

    # Retornar resultado criado
    return await db.fetch_one(
        "SELECT * FROM resultados_pesquisa WHERE id = ?",
        (resultado_id,)
    )


@router.put("/resultados/{resultado_id}", response_model=ResultadoResponse)
async def atualizar_resultado(resultado_id: int, atualizacoes: ResultadoUpdate):
    """
    Atualizar um resultado existente
    """
    # Verificar se existe
    resultado = await db.fetch_one(
        "SELECT * FROM resultados_pesquisa WHERE id = ?",
        (resultado_id,)
    )

    if not resultado:
        raise HTTPException(status_code=404, detail="Resultado nao encontrado")

    # Atualizar campos fornecidos
    updates = {}

    if atualizacoes.titulo is not None:
        updates["titulo"] = atualizacoes.titulo

    if atualizacoes.descricao is not None:
        updates["descricao"] = atualizacoes.descricao

    if atualizacoes.confidence_score is not None:
        updates["confidence_score"] = atualizacoes.confidence_score

    if atualizacoes.fonte_tipo is not None:
        updates["fonte_tipo"] = atualizacoes.fonte_tipo

    if atualizacoes.pais_origem is not None:
        updates["pais_origem"] = atualizacoes.pais_origem

    if updates:
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        query = f"UPDATE resultados_pesquisa SET {set_clause}, atualizado_em = CURRENT_TIMESTAMP WHERE id = ?"

        await db.execute(
            query,
            tuple(updates.values()) + (resultado_id,)
        )

    # Retornar resultado atualizado
    return await db.fetch_one(
        "SELECT * FROM resultados_pesquisa WHERE id = ?",
        (resultado_id,)
    )


@router.delete("/resultados/{resultado_id}", status_code=204)
async def deletar_resultado(resultado_id: int):
    """
    Deletar um resultado
    """
    # Verificar se existe
    resultado = await db.fetch_one(
        "SELECT * FROM resultados_pesquisa WHERE id = ?",
        (resultado_id,)
    )

    if not resultado:
        raise HTTPException(status_code=404, detail="Resultado nao encontrado")

    await delete_resultado(resultado_id)
