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
    delete_resultado,
    deletar_resultado_com_restauracao,
    validar_url,
    validar_urls_em_lote
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
    Inclui informacoes da falha (titulo e pilar) via JOIN
    """
    query = """
    SELECT
        r.id,
        r.falha_id,
        r.titulo,
        r.descricao,
        r.fonte_url,
        r.fonte_tipo,
        r.pais_origem,
        r.idioma,
        r.query,
        r.confidence_score,
        r.num_ocorrencias,
        r.ferramenta_origem,
        r.criado_em,
        r.atualizado_em,
        r.url_valida,
        f.titulo as falha_titulo,
        f.pilar
    FROM resultados_pesquisa r
    JOIN falhas_mercado f ON r.falha_id = f.id
    WHERE 1=1
    """

    if falha_id:
        query += f" AND r.falha_id = {falha_id}"

    query += f" AND r.confidence_score BETWEEN {min_score} AND {max_score}"

    if idioma:
        query += f" AND r.idioma = '{idioma}'"

    query += f" ORDER BY r.confidence_score DESC LIMIT {limit} OFFSET {skip}"

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

    if atualizacoes.titulo_pt is not None:
        updates["titulo_pt"] = atualizacoes.titulo_pt

    if atualizacoes.descricao_pt is not None:
        updates["descricao_pt"] = atualizacoes.descricao_pt

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


@router.delete("/resultados/{resultado_id}", status_code=200)
async def deletar_resultado_endpoint(resultado_id: int):
    """
    Deletar um resultado e restaurar fila automaticamente se necessário
    Retorna informações sobre a deleção e restauração
    """
    # Verificar se existe
    resultado = await db.fetch_one(
        "SELECT * FROM resultados_pesquisa WHERE id = ?",
        (resultado_id,)
    )

    if not resultado:
        raise HTTPException(status_code=404, detail="Resultado nao encontrado")

    # Deletar com restauração automática da fila se score < 0.7
    info = await deletar_resultado_com_restauracao(resultado_id)

    if not info['deletado']:
        raise HTTPException(status_code=500, detail=info.get('erro', 'Erro ao deletar'))

    return {
        "deletado": True,
        "resultado_id": resultado_id,
        "falha_id": info.get('falha_id'),
        "score_anterior": info.get('score_anterior'),
        "restaurou_fila": info['restaurou_fila'],
        "entradas_adicionadas": info['entradas_adicionadas'],
        "mensagem": f"Resultado deletado. Fila restaurada com {info['entradas_adicionadas']} entradas." if info['restaurou_fila'] else "Resultado deletado (score já era satisfatório)."
    }


@router.post("/resultados/validar-urls", status_code=200)
async def validar_urls_endpoint():
    """
    Valida todas as URLs dos resultados e deleta os inválidos
    Restaura a fila automaticamente para falhas com score < 0.7
    """
    resultado = await validar_urls_em_lote()

    return {
        "total_verificadas": resultado['total_verificadas'],
        "invalidas_encontradas": resultado['invalidas_encontradas'],
        "deletadas": resultado['deletadas'],
        "mensagem": f"Validação concluída: {resultado['invalidas_encontradas']} URLs inválidas encontradas, {resultado['deletadas']} resultados deletados e fila restaurada."
    }


@router.patch("/resultados/{resultado_id}/idioma", status_code=200)
async def atualizar_idioma(resultado_id: int, idioma: str = Query(..., min_length=2, max_length=2)):
    """
    Atualiza o idioma de um resultado específico

    Args:
        resultado_id: ID do resultado
        idioma: Código ISO 639-1 do idioma (pt, en, es, fr, de, it, ja, ar, ko, he)

    Returns:
        Resultado atualizado
    """
    # Verificar se existe
    resultado = await db.fetch_one(
        "SELECT * FROM resultados_pesquisa WHERE id = ?",
        (resultado_id,)
    )

    if not resultado:
        raise HTTPException(status_code=404, detail="Resultado não encontrado")

    # Validar idioma
    idiomas_validos = ['pt', 'en', 'es', 'fr', 'de', 'it', 'ja', 'ar', 'ko', 'he']
    if idioma.lower() not in idiomas_validos:
        raise HTTPException(
            status_code=400,
            detail=f"Idioma inválido. Use um dos seguintes: {', '.join(idiomas_validos)}"
        )

    # Atualizar idioma
    await db.execute(
        "UPDATE resultados_pesquisa SET idioma = ?, atualizado_em = CURRENT_TIMESTAMP WHERE id = ?",
        (idioma.lower(), resultado_id)
    )

    # Retornar resultado atualizado
    return await db.fetch_one(
        "SELECT * FROM resultados_pesquisa WHERE id = ?",
        (resultado_id,)
    )
