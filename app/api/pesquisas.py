# -*- coding: utf-8 -*-
"""
Endpoints para controle de pesquisas e jobs
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
import uuid

from app.database import db
from app.schemas import PesquisaIniciar, PesquisaCustom, StatusPesquisa, JobResponse

router = APIRouter(tags=["Pesquisas"])


@router.post("/pesquisas/iniciar", response_model=JobResponse)
async def iniciar_pesquisa(pesquisa: PesquisaIniciar):
    """
    Iniciar pesquisa automatizada de politicas publicas

    Se falhas_ids nao for fornecido, pesquisa todas as 50 falhas.
    Se idiomas nao for fornecido, usa os 8 idiomas configurados.
    """
    # IDs das falhas a pesquisar
    if pesquisa.falhas_ids:
        falhas_ids = pesquisa.falhas_ids
    else:
        # Obter todas as falhas
        falhas = await db.fetch_all("SELECT id FROM falhas_mercado")
        falhas_ids = [f["id"] for f in falhas]

    # Idiomas a usar
    if pesquisa.idiomas:
        idiomas = pesquisa.idiomas
    else:
        idiomas = ["pt", "en", "es", "fr", "de", "it", "ar", "ko", "he"]

    # Ferramentas a usar
    if pesquisa.ferramentas:
        ferramentas = pesquisa.ferramentas
    else:
        ferramentas = ["perplexity", "jina", "deep_research"]

    # Gerar queries (por enquanto, um placeholder - sera implementado no agente)
    num_queries = 5
    total_queries = len(falhas_ids) * len(idiomas) * len(ferramentas) * num_queries

    # Criar entradas na fila (AQUI sera chamado AgentePesquisador.popular_fila())
    # Por enquanto, apenas retornamos um job ID
    job_id = str(uuid.uuid4())

    tempo_estimado = (total_queries * 5) // 60  # 5 segundos por query (com rate limiting)

    return {
        "job_id": job_id,
        "status": "pendente",
        "queries_criadas": total_queries,
        "tempo_estimado_minutos": max(1, tempo_estimado)
    }


@router.post("/pesquisas/custom", response_model=JobResponse)
async def pesquisa_customizada(pesquisa: PesquisaCustom):
    """
    Executar pesquisa customizada com instrucoes especiais
    """
    # Verificar se falha existe
    falha = await db.fetch_one(
        "SELECT * FROM falhas_mercado WHERE id = ?",
        (pesquisa.falha_id,)
    )

    if not falha:
        raise HTTPException(status_code=404, detail="Falha nao encontrada")

    # Gerar queries customizadas
    if pesquisa.queries_customizadas:
        queries = pesquisa.queries_customizadas
    else:
        # Sera gerado pelo AgentePesquisador
        queries = [pesquisa.instrucoes]

    total_queries = len(queries) * len(pesquisa.idiomas) * len(pesquisa.ferramentas)
    job_id = str(uuid.uuid4())
    tempo_estimado = (total_queries * 5) // 60

    return {
        "job_id": job_id,
        "status": "pendente",
        "queries_criadas": total_queries,
        "tempo_estimado_minutos": max(1, tempo_estimado)
    }


@router.get("/pesquisas/status", response_model=StatusPesquisa)
async def status_pesquisa():
    """
    Obter status atual do processamento de pesquisas
    """
    # Contar pesquisas em cada estado
    pendentes = await db.fetch_one(
        "SELECT COUNT(*) as total FROM fila_pesquisas WHERE status = 'pendente'"
    )
    processando = await db.fetch_one(
        "SELECT COUNT(*) as total FROM fila_pesquisas WHERE status = 'processando'"
    )
    concluidas = await db.fetch_one(
        "SELECT COUNT(*) as total FROM historico_pesquisas WHERE status = 'concluido'"
    )
    erros = await db.fetch_one(
        "SELECT COUNT(*) as total FROM historico_pesquisas WHERE status = 'erro'"
    )

    total_pendentes = pendentes["total"]
    total_processando = processando["total"]
    total_concluidas = concluidas["total"]
    total_erros = erros["total"]
    total_tarefas = total_pendentes + total_processando + total_concluidas

    if total_tarefas == 0:
        porcentagem = 0.0
    else:
        porcentagem = (total_concluidas / total_tarefas) * 100

    # Determinar mensagem e se ainda esta ativo
    ativo = total_pendentes + total_processando > 0

    if ativo:
        mensagem = f"Processando: {total_processando} em andamento, {total_pendentes} pendentes"
    elif total_tarefas > 0:
        mensagem = f"Concluido: {total_concluidas} resultados, {total_erros} erros"
    else:
        mensagem = "Nenhuma pesquisa em progresso"

    return {
        "ativo": ativo,
        "porcentagem": round(porcentagem, 1),
        "mensagem": mensagem,
        "total_pendentes": total_pendentes,
        "total_processando": total_processando,
        "total_concluidas": total_concluidas,
        "total_erros": total_erros
    }


@router.get("/pesquisas/historico")
async def historico_pesquisas(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None
):
    """
    Obter historico de pesquisas executadas
    """
    query = "SELECT * FROM historico_pesquisas WHERE 1=1"

    if status:
        query += f" AND status = '{status}'"

    query += f" ORDER BY executado_em DESC LIMIT {limit} OFFSET {skip}"

    historico = await db.fetch_all(query)

    return {
        "total": len(historico),
        "items": historico
    }
