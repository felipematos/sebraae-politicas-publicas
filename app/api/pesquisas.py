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
    from app.agente.pesquisador import AgentePesquisador

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
        idiomas = ["pt", "en", "es", "fr", "de", "it", "ar", "ko"]

    # Ferramentas a usar
    if pesquisa.ferramentas:
        ferramentas = pesquisa.ferramentas
    else:
        ferramentas = ["perplexity", "jina", "deep_research"]

    # Criar agente pesquisador
    agente = AgentePesquisador()

    # Popular fila de pesquisas
    try:
        total_queries = await agente.popular_fila(
            falhas_ids=falhas_ids,
            idiomas_filtro=idiomas,
            ferramentas_filtro=ferramentas
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao popular fila: {str(e)}"
        )

    # Calcular tempo estimado (5 segundos por query com rate limiting)
    tempo_estimado = max(1, (total_queries * 5) // 60)
    job_id = str(uuid.uuid4())

    return {
        "job_id": job_id,
        "status": "iniciada",
        "queries_criadas": total_queries,
        "tempo_estimado_minutos": tempo_estimado
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
    try:
        pendentes = await db.fetch_one(
            "SELECT COUNT(*) as total FROM fila_pesquisas WHERE status = 'pendente'"
        )
        processando = await db.fetch_one(
            "SELECT COUNT(*) as total FROM fila_pesquisas WHERE status = 'processando'"
        )
        completas = await db.fetch_one(
            "SELECT COUNT(*) as total FROM fila_pesquisas WHERE status = 'completa'"
        )
        erros_fila = await db.fetch_one(
            "SELECT COUNT(*) as total FROM fila_pesquisas WHERE status = 'erro'"
        )

        # Contar resultados encontrados
        resultados = await db.fetch_one(
            "SELECT COUNT(*) as total FROM resultados_pesquisa"
        )

        total_pendentes = pendentes["total"] if pendentes else 0
        total_processando = processando["total"] if processando else 0
        total_completas = completas["total"] if completas else 0
        total_erros = erros_fila["total"] if erros_fila else 0
        total_resultados = resultados["total"] if resultados else 0
        total_tarefas = total_pendentes + total_processando + total_completas + total_erros

        if total_tarefas == 0:
            porcentagem = 0.0
        else:
            porcentagem = ((total_completas + total_erros) / total_tarefas) * 100

        # Determinar mensagem e se ainda esta ativo
        ativo = total_pendentes + total_processando > 0

        if ativo:
            mensagem = f"Processando: {total_processando} em andamento, {total_pendentes} na fila, {total_resultados} resultados encontrados"
        elif total_tarefas > 0:
            mensagem = f"Concluído: {total_resultados} resultados encontrados, {total_erros} erros"
        else:
            mensagem = "Nenhuma pesquisa em progresso"

        return {
            "ativo": ativo,
            "porcentagem": round(porcentagem, 1),
            "mensagem": mensagem,
            "total_pendentes": total_pendentes,
            "total_processando": total_processando,
            "total_concluidas": total_completas,
            "total_erros": total_erros
        }
    except Exception as e:
        # Se erro na consulta, retornar valores padrao
        return {
            "ativo": False,
            "porcentagem": 0.0,
            "mensagem": f"Erro ao obter status: {str(e)}",
            "total_pendentes": 0,
            "total_processando": 0,
            "total_concluidas": 0,
            "total_erros": 0
        }


@router.post("/pesquisas/pausar")
async def pausar_pesquisa():
    """
    Pausar pesquisas em andamento (pausa o worker e marca como 'pendente' novamente)
    """
    try:
        # Pausar o worker do processador
        from app.main import processador_global

        if processador_global:
            processador_global.ativo = False
            print("[PAUSA] Processador pausado")
        else:
            print("[PAUSA] Aviso: Processador global não inicializado")

        # Atualizar todos os itens 'processando' de volta para 'pendente'
        await db.execute(
            "UPDATE fila_pesquisas SET status = 'pendente' WHERE status = 'processando'"
        )

        return {
            "status": "sucesso",
            "mensagem": "Pesquisas pausadas com sucesso",
            "processador_pausado": processador_global is not None and not processador_global.ativo
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao pausar pesquisas: {str(e)}"
        )


@router.post("/pesquisas/retomar")
async def retomar_pesquisa():
    """
    Retomar pesquisas pausadas (o worker as processará novamente)
    """
    try:
        # Retomar o worker do processador
        from app.main import processador_global

        if processador_global:
            processador_global.ativo = True
            print("[RETOMAR] Processador retomado")
        else:
            print("[RETOMAR] Aviso: Processador global não inicializado")

        # Contar items pendentes
        pendentes = await db.fetch_one(
            "SELECT COUNT(*) as total FROM fila_pesquisas WHERE status = 'pendente'"
        )
        return {
            "status": "sucesso",
            "mensagem": f"Pesquisas retomadas. {pendentes['total']} itens na fila.",
            "total_pendentes": pendentes['total'],
            "processador_ativo": processador_global is not None and processador_global.ativo
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao retomar pesquisas: {str(e)}"
        )


@router.post("/pesquisas/reiniciar")
async def reiniciar_pesquisas():
    """
    Reiniciar pesquisas (limpa fila e resultados)
    """
    try:
        # Limpar fila
        await db.execute("DELETE FROM fila_pesquisas")

        # Limpar resultados
        await db.execute("DELETE FROM resultados_pesquisa")

        return {
            "status": "sucesso",
            "mensagem": "Pesquisas reiniciadas. Fila e resultados limpos."
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao reiniciar pesquisas: {str(e)}"
        )


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
