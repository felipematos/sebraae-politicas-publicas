# -*- coding: utf-8 -*-
"""
Endpoints para tradução em lote com background processing
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict
import uuid
from datetime import datetime
import asyncio

from app.database import db
from app.integracao.openrouter_api import OpenRouterClient
from app.utils.logger import logger

router = APIRouter(tags=["Tradução em Lote"])

# Dicionário global para rastrear jobs de tradução em background
traducao_jobs: Dict[str, dict] = {}


class TraduzirLoteRequest(BaseModel):
    """Schema para solicitar tradução em lote"""
    max_concurrent: int = 10  # Máximo de traduções simultâneas


async def processar_traducoes_background(job_id: str, max_concurrent: int = 10):
    """
    Processa traduções em background com atualização de progresso

    Args:
        job_id: ID único do job
        max_concurrent: Número máximo de traduções simultâneas
    """
    try:
        logger.info(f"[JOB {job_id}] Iniciando traduções em background")

        # Buscar resultados sem tradução
        query = """
        SELECT id, falha_id, titulo, descricao, idioma
        FROM resultados_pesquisa
        WHERE idioma != 'pt'
        AND (titulo_pt IS NULL OR titulo_pt = '')
        ORDER BY id
        """

        resultados = await db.fetch_all(query)
        total = len(resultados)

        if total == 0:
            traducao_jobs[job_id].update({
                "status": "concluido",
                "progresso": 100,
                "total_traduzidas": 0,
                "erros": 0,
                "mensagem": "Nenhum resultado para traduzir",
                "concluido_em": datetime.now().isoformat()
            })
            return

        # Atualizar status
        traducao_jobs[job_id].update({
            "status": "processando",
            "total": total,
            "processados": 0,
            "progresso": 0,
            "traduzidas": 0,
            "erros": 0
        })

        traduzidas = 0
        erros = 0
        processados = 0

        # Criar semáforo para controlar concorrência
        semaphore = asyncio.Semaphore(max_concurrent)

        async def traduzir_um_resultado(resultado):
            """Traduz um resultado individualmente"""
            nonlocal traduzidas, erros, processados

            async with semaphore:
                try:
                    resultado_dict = dict(resultado)
                    idioma_origem = resultado_dict.get('idioma', 'en')

                    # Traduzir com OpenRouterClient
                    async with OpenRouterClient() as client:
                        titulo_pt = await client.traduzir_texto(
                            texto=resultado_dict['titulo'],
                            idioma_alvo="pt",
                            idioma_origem=idioma_origem
                        )

                        descricao_pt = await client.traduzir_texto(
                            texto=resultado_dict['descricao'],
                            idioma_alvo="pt",
                            idioma_origem=idioma_origem
                        )

                    # Atualizar no banco
                    if titulo_pt and descricao_pt:
                        await db.execute(
                            """
                            UPDATE resultados_pesquisa
                            SET titulo_pt = ?, descricao_pt = ?, atualizado_em = CURRENT_TIMESTAMP
                            WHERE id = ?
                            """,
                            (titulo_pt.strip(), descricao_pt.strip(), resultado_dict['id'])
                        )
                        traduzidas += 1
                    else:
                        erros += 1

                except Exception as e:
                    erros += 1
                    logger.error(f"[JOB {job_id}] Erro ao traduzir resultado {resultado_dict.get('id')}: {e}")

                finally:
                    processados += 1
                    # Atualizar progresso
                    progresso = int((processados / total) * 100)
                    traducao_jobs[job_id].update({
                        "processados": processados,
                        "progresso": progresso,
                        "traduzidas": traduzidas,
                        "erros": erros
                    })

        # Processar todos os resultados em paralelo (controlado pelo semáforo)
        await asyncio.gather(*[traduzir_um_resultado(r) for r in resultados])

        # Finalizar job
        traducao_jobs[job_id].update({
            "status": "concluido",
            "progresso": 100,
            "total_traduzidas": traduzidas,
            "total_erros": erros,
            "mensagem": f"Tradução concluída! {traduzidas} resultados traduzidos, {erros} erros.",
            "concluido_em": datetime.now().isoformat()
        })

        logger.info(f"[JOB {job_id}] Tradução concluída: {traduzidas}/{total} resultados traduzidos")

    except Exception as e:
        logger.error(f"[JOB {job_id}] Erro fatal na tradução: {e}")
        traducao_jobs[job_id].update({
            "status": "erro",
            "erro": str(e),
            "concluido_em": datetime.now().isoformat()
        })


@router.post("/api/traducao/lote/iniciar")
async def iniciar_traducao_lote(request: TraduzirLoteRequest, background_tasks: BackgroundTasks):
    """
    Inicia tradução em lote de todos os resultados sem tradução

    Args:
        request: Configurações de tradução (max_concurrent)
        background_tasks: FastAPI background tasks

    Returns:
        Job ID para acompanhamento do progresso
    """
    try:
        # Gerar job ID único
        job_id = str(uuid.uuid4())

        # Criar registro do job
        traducao_jobs[job_id] = {
            "job_id": job_id,
            "status": "iniciado",
            "progresso": 0,
            "total": 0,
            "processados": 0,
            "traduzidas": 0,
            "erros": 0,
            "max_concurrent": request.max_concurrent,
            "iniciado_em": datetime.now().isoformat()
        }

        # Adicionar tarefa em background
        background_tasks.add_task(
            processar_traducoes_background,
            job_id,
            request.max_concurrent
        )

        logger.info(f"[JOB {job_id}] Tradução em lote iniciada (max_concurrent={request.max_concurrent})")

        return {
            "job_id": job_id,
            "status": "iniciado",
            "mensagem": "Tradução em lote iniciada. Use o job_id para acompanhar o progresso."
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao iniciar tradução em lote: {str(e)}"
        )


@router.get("/api/traducao/lote/status/{job_id}")
async def obter_status_traducao(job_id: str):
    """
    Obtém o status de um job de tradução em lote

    Args:
        job_id: ID do job de tradução

    Returns:
        Status atual do job
    """
    if job_id not in traducao_jobs:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    return traducao_jobs[job_id]


@router.post("/api/traducao/lote/refazer_todas")
async def refazer_todas_traducoes(background_tasks: BackgroundTasks):
    """
    REFAZ TODAS as traduções de resultados internacionais com:
    1. Detecção corrigida de idioma pelo LLM (maior confiança que heurística)
    2. Tradução usando LLMs gratuitos
    3. Atualização do idioma detectado no banco quando houver discrepância

    IMPORTANTE: Usado especialmente para corrigir casos de PT detectado como ES.

    Returns:
        Job ID para acompanhamento do progresso
    """
    try:
        # Gerar job ID único
        job_id = str(uuid.uuid4())

        # Criar registro do job
        traducao_jobs[job_id] = {
            "job_id": job_id,
            "status": "iniciado",
            "progresso": 0,
            "total": 0,
            "processados": 0,
            "traduzidas": 0,
            "erros": 0,
            "idiomas_corrigidos": 0,
            "max_concurrent": 5,
            "iniciado_em": datetime.now().isoformat()
        }

        # Adicionar tarefa em background
        background_tasks.add_task(
            refazer_todas_traducoes_background,
            job_id
        )

        logger.info(f"[JOB {job_id}] Refazendo TODAS as traduções com detecção de idioma")

        return {
            "job_id": job_id,
            "status": "iniciado",
            "mensagem": "Refazendo todas as traduções. Use o job_id para acompanhar o progresso."
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao iniciar refazer todas as traduções: {str(e)}"
        )


@router.post("/api/traducao/lote/reprocessar")
async def reprocessar_traducoes(background_tasks: BackgroundTasks):
    """
    Reprocessa todas as traduções existentes que estão em lowercase
    para corrigir problemas de capitalização.

    Returns:
        Job ID para acompanhamento do progresso
    """
    try:
        # Gerar job ID único
        job_id = str(uuid.uuid4())

        # Criar registro do job
        traducao_jobs[job_id] = {
            "job_id": job_id,
            "status": "iniciado",
            "progresso": 0,
            "total": 0,
            "processados": 0,
            "traduzidas": 0,
            "erros": 0,
            "max_concurrent": 5,
            "iniciado_em": datetime.now().isoformat()
        }

        # Adicionar tarefa em background
        background_tasks.add_task(
            reprocessar_traducoes_background,
            job_id
        )

        logger.info(f"[JOB {job_id}] Reprocessamento de traduções iniciado")

        return {
            "job_id": job_id,
            "status": "iniciado",
            "mensagem": "Reprocessamento de traduções iniciado. Use o job_id para acompanhar o progresso."
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao iniciar reprocessamento: {str(e)}"
        )


async def refazer_todas_traducoes_background(job_id: str):
    """
    REFAZ TODAS as traduções com detecção corrigida de idioma

    Esta função:
    1. Busca TODOS os resultados não-PT (incluindo os já traduzidos)
    2. Usa o novo método traduzir_texto_com_deteccao() que retorna tradução + idioma real
    3. Atualiza tanto a tradução quanto o idioma no banco quando necessário
    """
    try:
        logger.info(f"[JOB {job_id}] Iniciando refazimento de TODAS as traduções com detecção de idioma")

        # Buscar TODOS os resultados não-PT (incluindo já traduzidos)
        query = """
        SELECT id, falha_id, titulo, descricao, idioma
        FROM resultados_pesquisa
        WHERE idioma != 'pt'
        ORDER BY id
        """

        resultados = await db.fetch_all(query)
        total = len(resultados)

        if total == 0:
            traducao_jobs[job_id].update({
                "status": "concluido",
                "progresso": 100,
                "total_traduzidas": 0,
                "idiomas_corrigidos": 0,
                "erros": 0,
                "mensagem": "Nenhum resultado internacional para processar",
                "concluido_em": datetime.now().isoformat()
            })
            return

        # Atualizar status
        traducao_jobs[job_id].update({
            "status": "processando",
            "total": total,
            "processados": 0,
            "progresso": 0,
            "traduzidas": 0,
            "idiomas_corrigidos": 0,
            "erros": 0
        })

        traduzidas = 0
        idiomas_corrigidos = 0
        erros = 0
        processados = 0

        # Criar semáforo para controlar concorrência
        semaphore = asyncio.Semaphore(5)

        async def refazer_traducao_resultado(resultado):
            """Refaz tradução com detecção de idioma"""
            nonlocal traduzidas, idiomas_corrigidos, erros, processados

            async with semaphore:
                try:
                    resultado_dict = dict(resultado)
                    idioma_assumido = resultado_dict.get('idioma', 'en')

                    # Usar novo método que detecta idioma E traduz
                    async with OpenRouterClient() as client:
                        # Traduzir título com detecção
                        resultado_titulo = await client.traduzir_texto_com_deteccao(
                            texto=resultado_dict['titulo'],
                            idioma_alvo="pt",
                            idioma_origem=idioma_assumido
                        )

                        # Traduzir descrição com detecção
                        resultado_descricao = await client.traduzir_texto_com_deteccao(
                            texto=resultado_dict['descricao'],
                            idioma_alvo="pt",
                            idioma_origem=idioma_assumido
                        )

                    titulo_pt = resultado_titulo.get("traducao")
                    idioma_real_titulo = resultado_titulo.get("idioma_real", idioma_assumido)

                    descricao_pt = resultado_descricao.get("traducao")
                    idioma_real_descricao = resultado_descricao.get("idioma_real", idioma_assumido)

                    # Usar o idioma detectado no título como referência (geralmente mais confiável)
                    idioma_real = idioma_real_titulo

                    # Verificar se o idioma foi corrigido
                    idioma_foi_corrigido = (idioma_real != idioma_assumido)

                    # Atualizar no banco (tradução + idioma se mudou)
                    if titulo_pt and descricao_pt:
                        if idioma_foi_corrigido:
                            # Atualizar tradução E idioma
                            await db.execute(
                                """
                                UPDATE resultados_pesquisa
                                SET titulo_pt = ?, descricao_pt = ?, idioma = ?, atualizado_em = CURRENT_TIMESTAMP
                                WHERE id = ?
                                """,
                                (titulo_pt.strip(), descricao_pt.strip(), idioma_real, resultado_dict['id'])
                            )
                            idiomas_corrigidos += 1
                            logger.info(
                                f"[JOB {job_id}] ✓ ID {resultado_dict['id']}: "
                                f"Idioma corrigido {idioma_assumido} -> {idioma_real}"
                            )
                        else:
                            # Atualizar apenas tradução
                            await db.execute(
                                """
                                UPDATE resultados_pesquisa
                                SET titulo_pt = ?, descricao_pt = ?, atualizado_em = CURRENT_TIMESTAMP
                                WHERE id = ?
                                """,
                                (titulo_pt.strip(), descricao_pt.strip(), resultado_dict['id'])
                            )

                        traduzidas += 1
                    else:
                        erros += 1

                except Exception as e:
                    erros += 1
                    logger.error(f"[JOB {job_id}] Erro ao refazer tradução do resultado {resultado_dict.get('id')}: {e}")

                finally:
                    processados += 1
                    # Atualizar progresso
                    progresso = int((processados / total) * 100)
                    traducao_jobs[job_id].update({
                        "processados": processados,
                        "progresso": progresso,
                        "traduzidas": traduzidas,
                        "idiomas_corrigidos": idiomas_corrigidos,
                        "erros": erros
                    })

        # Processar todos os resultados em paralelo (controlado pelo semáforo)
        await asyncio.gather(*[refazer_traducao_resultado(r) for r in resultados])

        # Finalizar job
        traducao_jobs[job_id].update({
            "status": "concluido",
            "progresso": 100,
            "total_traduzidas": traduzidas,
            "total_idiomas_corrigidos": idiomas_corrigidos,
            "total_erros": erros,
            "mensagem": f"Refazimento concluído! {traduzidas} traduções refeitas, {idiomas_corrigidos} idiomas corrigidos, {erros} erros.",
            "concluido_em": datetime.now().isoformat()
        })

        logger.info(
            f"[JOB {job_id}] Refazimento concluído: "
            f"{traduzidas}/{total} traduções, {idiomas_corrigidos} idiomas corrigidos"
        )

    except Exception as e:
        logger.error(f"[JOB {job_id}] Erro fatal no refazimento: {e}")
        traducao_jobs[job_id].update({
            "status": "erro",
            "erro": str(e),
            "concluido_em": datetime.now().isoformat()
        })


async def reprocessar_traducoes_background(job_id: str):
    """
    Reprocessa traduções em background para corrigir capitalização
    """
    try:
        logger.info(f"[JOB {job_id}] Iniciando reprocessamento de traduções")

        # Buscar resultados com traduções em lowercase (heurística: sem maiúsculas)
        query = """
        SELECT id, falha_id, titulo, descricao, idioma, titulo_pt, descricao_pt
        FROM resultados_pesquisa
        WHERE idioma != 'pt'
        AND titulo_pt IS NOT NULL
        AND titulo_pt != ''
        AND titulo_pt = LOWER(titulo_pt)
        ORDER BY id
        """

        resultados = await db.fetch_all(query)
        total = len(resultados)

        if total == 0:
            traducao_jobs[job_id].update({
                "status": "concluido",
                "progresso": 100,
                "total_traduzidas": 0,
                "erros": 0,
                "mensagem": "Nenhuma tradução para reprocessar",
                "concluido_em": datetime.now().isoformat()
            })
            return

        # Atualizar status
        traducao_jobs[job_id].update({
            "status": "processando",
            "total": total,
            "processados": 0,
            "progresso": 0,
            "traduzidas": 0,
            "erros": 0
        })

        traduzidas = 0
        erros = 0
        processados = 0

        # Criar semáforo para controlar concorrência
        semaphore = asyncio.Semaphore(5)  # Mais conservador para reprocessamento

        async def retraduzir_um_resultado(resultado):
            """Retraduz um resultado individualmente"""
            nonlocal traduzidas, erros, processados

            async with semaphore:
                try:
                    resultado_dict = dict(resultado)
                    idioma_origem = resultado_dict.get('idioma', 'en')

                    # Retraduzir com OpenRouterClient (agora com prompt corrigido)
                    async with OpenRouterClient() as client:
                        titulo_pt = await client.traduzir_texto(
                            texto=resultado_dict['titulo'],
                            idioma_alvo="pt",
                            idioma_origem=idioma_origem
                        )

                        descricao_pt = await client.traduzir_texto(
                            texto=resultado_dict['descricao'],
                            idioma_alvo="pt",
                            idioma_origem=idioma_origem
                        )

                    # Atualizar no banco
                    if titulo_pt and descricao_pt:
                        await db.execute(
                            """
                            UPDATE resultados_pesquisa
                            SET titulo_pt = ?, descricao_pt = ?, atualizado_em = CURRENT_TIMESTAMP
                            WHERE id = ?
                            """,
                            (titulo_pt.strip(), descricao_pt.strip(), resultado_dict['id'])
                        )
                        traduzidas += 1
                        logger.info(f"[JOB {job_id}] Retraduzido resultado {resultado_dict['id']}: '{resultado_dict['titulo_pt'][:50]}' -> '{titulo_pt[:50]}'")
                    else:
                        erros += 1

                except Exception as e:
                    erros += 1
                    logger.error(f"[JOB {job_id}] Erro ao retraduzir resultado {resultado_dict.get('id')}: {e}")

                finally:
                    processados += 1
                    # Atualizar progresso
                    progresso = int((processados / total) * 100)
                    traducao_jobs[job_id].update({
                        "processados": processados,
                        "progresso": progresso,
                        "traduzidas": traduzidas,
                        "erros": erros
                    })

        # Processar todos os resultados em paralelo (controlado pelo semáforo)
        await asyncio.gather(*[retraduzir_um_resultado(r) for r in resultados])

        # Finalizar job
        traducao_jobs[job_id].update({
            "status": "concluido",
            "progresso": 100,
            "total_traduzidas": traduzidas,
            "total_erros": erros,
            "mensagem": f"Reprocessamento concluído! {traduzidas} traduções corrigidas, {erros} erros.",
            "concluido_em": datetime.now().isoformat()
        })

        logger.info(f"[JOB {job_id}] Reprocessamento concluído: {traduzidas}/{total} traduções corrigidas")

    except Exception as e:
        logger.error(f"[JOB {job_id}] Erro fatal no reprocessamento: {e}")
        traducao_jobs[job_id].update({
            "status": "erro",
            "erro": str(e),
            "concluido_em": datetime.now().isoformat()
        })
