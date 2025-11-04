# -*- coding: utf-8 -*-
"""
Router FastAPI para endpoints de priorização de falhas de mercado
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
from app.database import (
    obter_priorizacao,
    listar_priorizacoes,
    listar_priorizacoes_sem_analise,
    gerar_matriz_2x2,
    obter_quadrantes_matriz,
    atualizar_priorizacao,
    criar_priorizacao,
    get_falhas_mercado,
    obter_fontes_por_falha
)
from app.agente.priorizador import AgentePriorizador
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/priorizacoes",
    tags=["priorizacoes"]
)

priorizador = AgentePriorizador()


# Models Pydantic
class PriorizacaoUpdate(BaseModel):
    """Model para atualização de priorização"""
    impacto: int  # 0-10
    esforco: int  # 0-10


class AnalisarFalhaRequest(BaseModel):
    """Model para requisição de análise"""
    falha_id: int


class AnalisarTodasRequest(BaseModel):
    """Model para análise em lote com configurações"""
    incluir_analisadas: bool = False  # Se False, analisa apenas as sem análise
    usar_rag: bool = True  # Usar base de conhecimento RAG
    usar_resultados_pesquisa: bool = True  # Usar resultados de pesquisa
    temperatura: float = 0.3  # Temperatura do modelo (0.0-1.0)
    max_tokens: int = 4000  # Máximo de tokens na resposta
    modelo: str = "google/gemini-2.5-pro"  # Modelo a ser usado


class AnalisarIndividualRequest(BaseModel):
    """Model para análise individual com configurações"""
    falha_id: int
    usar_rag: bool = True  # Usar base de conhecimento RAG
    usar_resultados_pesquisa: bool = True  # Usar resultados de pesquisa
    temperatura: float = 0.3  # Temperatura do modelo (0.0-1.0)
    max_tokens: int = 4000  # Máximo de tokens na resposta
    modelo: str = "google/gemini-2.5-pro"  # Modelo a ser usado


# Endpoints

@router.get("/")
async def listar_priorizacoes_endpoint() -> Dict[str, Any]:
    """
    Retorna todas as priorizações com dados das falhas
    """
    try:
        priorizacoes = await listar_priorizacoes()
        return {
            'sucesso': True,
            'total': len(priorizacoes),
            'dados': priorizacoes
        }
    except Exception as e:
        logger.error(f"Erro ao listar priorizações: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{falha_id}")
async def obter_priorizacao_endpoint(falha_id: int, incluir_fontes: bool = True) -> Dict[str, Any]:
    """
    Retorna a priorização de uma falha específica

    Query params:
    - incluir_fontes: bool (default=True) - Incluir fontes utilizadas na análise
    """
    try:
        priorizacao = await obter_priorizacao(falha_id)
        if not priorizacao:
            raise HTTPException(status_code=404, detail=f"Priorização para falha {falha_id} não encontrada")

        # Obter fontes utilizadas se solicitado
        fontes = []
        if incluir_fontes:
            fontes = await obter_fontes_por_falha(falha_id)

        return {
            'sucesso': True,
            'dados': {
                **priorizacao,
                'fontes': fontes
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter priorização: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inicializar/padrao")
async def inicializar_priorizacoes_padrao() -> Dict[str, Any]:
    """
    Inicializa priorizações padrão para todas as falhas que não têm
    Retorna True se já existem, False se foram criadas
    """
    try:
        falhas = await get_falhas_mercado()
        criadas = 0
        ja_existentes = 0

        for falha in falhas:
            existente = await obter_priorizacao(falha['id'])
            if not existente:
                await criar_priorizacao(falha['id'], impacto=5, esforco=5)
                criadas += 1
            else:
                ja_existentes += 1

        logger.info(f"Priorizações inicializadas: {criadas} criadas, {ja_existentes} já existentes")

        return {
            'sucesso': True,
            'total_falhas': len(falhas),
            'criadas': criadas,
            'ja_existentes': ja_existentes
        }
    except Exception as e:
        logger.error(f"Erro ao inicializar priorizações: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analisar")
async def analisar_falha_endpoint(request: AnalisarFalhaRequest) -> Dict[str, Any]:
    """
    Analisa uma falha específica usando IA
    Retorna impacto, esforço e análise
    """
    try:
        resultado = await priorizador.analisar_falha(request.falha_id)

        if not resultado['sucesso']:
            raise HTTPException(status_code=400, detail=resultado.get('erro'))

        return {
            'sucesso': True,
            'dados': resultado
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao analisar falha: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analisar-todas-stream")
async def analisar_todas_falhas_stream(request: AnalisarTodasRequest):
    """
    Analisa todas as falhas usando IA com Server-Sent Events (SSE) para progresso em tempo real
    """
    async def event_generator():
        try:
            falhas = await get_falhas_mercado()
            total = len(falhas)

            # Enviar evento de início
            yield f"data: {json.dumps({'tipo': 'inicio', 'total': total})}\n\n"

            analisadas = 0
            falhadas = 0
            erros = []

            for idx, falha in enumerate(falhas, 1):
                # Enviar progresso antes de analisar
                yield f"data: {json.dumps({'tipo': 'progresso', 'atual': idx, 'total': total, 'falha_atual': falha['titulo']})}\n\n"

                # Analisar falha
                resultado = await priorizador.analisar_falha(
                    falha['id'],
                    usar_rag=request.usar_rag,
                    usar_resultados_pesquisa=request.usar_resultados_pesquisa,
                    temperatura=request.temperatura,
                    max_tokens=request.max_tokens,
                    modelo=request.modelo
                )

                if resultado['sucesso']:
                    analisadas += 1
                else:
                    falhadas += 1
                    erros.append({
                        'falha_id': falha['id'],
                        'titulo': falha['titulo'],
                        'erro': resultado.get('erro')
                    })

                # Pequeno delay entre requisições
                await asyncio.sleep(1)

            # Enviar evento de conclusão
            yield f"data: {json.dumps({'tipo': 'completo', 'analisadas': analisadas, 'falhadas': falhadas, 'erros': erros})}\n\n"

        except Exception as e:
            logger.error(f"Erro no stream de análise: {str(e)}")
            yield f"data: {json.dumps({'tipo': 'erro', 'mensagem': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/analisar-todas")
async def analisar_todas_falhas_endpoint(request: AnalisarTodasRequest) -> Dict[str, Any]:
    """
    Analisa todas as falhas usando IA com configurações customizadas
    Por padrão analisa apenas as que ainda não têm análise
    """
    try:
        logger.info(f"Iniciando análise em lote de todas as falhas")
        logger.info(f"Configurações: RAG={request.usar_rag}, Pesquisa={request.usar_resultados_pesquisa}, "
                   f"Temp={request.temperatura}, MaxTokens={request.max_tokens}, Modelo={request.modelo}")

        resultado = await priorizador.analisar_todas_falhas(
            usar_rag=request.usar_rag,
            usar_resultados_pesquisa=request.usar_resultados_pesquisa,
            temperatura=request.temperatura,
            max_tokens=request.max_tokens,
            modelo=request.modelo
        )

        return {
            'sucesso': resultado['sucesso'],
            'total_falhas': resultado['total_falhas'],
            'analisadas': resultado['analisadas'],
            'falhadas': resultado['falhadas'],
            'erros': resultado.get('erros', [])
        }
    except Exception as e:
        logger.error(f"Erro ao analisar todas as falhas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analisar-individual")
async def analisar_individual_endpoint(request: AnalisarIndividualRequest) -> Dict[str, Any]:
    """
    Analisa uma falha específica com configurações customizadas
    """
    try:
        logger.info(f"Iniciando análise individual da falha {request.falha_id}")
        logger.info(f"Configurações: RAG={request.usar_rag}, Pesquisa={request.usar_resultados_pesquisa}, "
                   f"Temp={request.temperatura}, MaxTokens={request.max_tokens}, Modelo={request.modelo}")

        resultado = await priorizador.analisar_falha(
            falha_id=request.falha_id,
            usar_rag=request.usar_rag,
            usar_resultados_pesquisa=request.usar_resultados_pesquisa,
            temperatura=request.temperatura,
            max_tokens=request.max_tokens,
            modelo=request.modelo
        )

        return {
            'sucesso': resultado['sucesso'],
            'falha_id': request.falha_id,
            'impacto': resultado.get('impacto'),
            'esforco': resultado.get('esforco'),
            'fontes': resultado.get('fontes', []),
            'erro': resultado.get('erro')
        }
    except Exception as e:
        logger.error(f"Erro ao analisar falha {request.falha_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{falha_id}")
async def atualizar_priorizacao_endpoint(falha_id: int, request: PriorizacaoUpdate) -> Dict[str, Any]:
    """
    Atualiza os scores de impacto e esforço de uma falha
    Chamada manualmente pelo usuário após revisão
    """
    try:
        # Validar ranges
        if not (0 <= request.impacto <= 10 and 0 <= request.esforco <= 10):
            raise HTTPException(
                status_code=400,
                detail="Impacto e esforço devem estar entre 0 e 10"
            )

        await atualizar_priorizacao(falha_id, request.impacto, request.esforco)

        resultado = await obter_priorizacao(falha_id)

        return {
            'sucesso': True,
            'mensagem': f'Priorização da falha {falha_id} atualizada com sucesso',
            'dados': resultado
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar priorização: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sem-analise/listar")
async def listar_sem_analise() -> Dict[str, Any]:
    """
    Retorna lista de priorizações que ainda não têm análise de IA
    """
    try:
        priorizacoes = await listar_priorizacoes_sem_analise()

        return {
            'sucesso': True,
            'total': len(priorizacoes),
            'dados': priorizacoes
        }
    except Exception as e:
        logger.error(f"Erro ao listar sem análise: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/matriz/dados")
async def obter_dados_matriz() -> Dict[str, Any]:
    """
    Retorna dados para plotagem da matriz 2x2
    Cada ponto é uma falha com suas coordenadas (impacto, esforço)
    """
    try:
        dados = await gerar_matriz_2x2()

        return {
            'sucesso': True,
            'total': len(dados),
            'dados': dados
        }
    except Exception as e:
        logger.error(f"Erro ao gerar dados da matriz: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/matriz/quadrantes")
async def obter_quadrantes() -> Dict[str, Any]:
    """
    Retorna falhas agrupadas por quadrante da matriz 2x2:
    - quick_wins: Alto impacto, Baixo esforço (impacto > 5, esforço <= 5)
    - strategic: Alto impacto, Alto esforço (impacto > 5, esforço > 5)
    - fill_in: Baixo impacto, Baixo esforço (impacto <= 5, esforço <= 5)
    - low_priority: Baixo impacto, Alto esforço (impacto <= 5, esforço > 5)

    Usa limiar de 5 (ponto médio da escala 0-10) para consistência com visualização
    """
    try:
        quadrantes = await obter_quadrantes_matriz()

        return {
            'sucesso': True,
            'quick_wins': {
                'total': len(quadrantes['quick_wins']),
                'descricao': 'Alto impacto, Baixo esforço',
                'dados': quadrantes['quick_wins']
            },
            'strategic': {
                'total': len(quadrantes['strategic']),
                'descricao': 'Alto impacto, Alto esforço',
                'dados': quadrantes['strategic']
            },
            'fill_in': {
                'total': len(quadrantes['fill_in']),
                'descricao': 'Baixo impacto, Baixo esforço',
                'dados': quadrantes['fill_in']
            },
            'low_priority': {
                'total': len(quadrantes['low_priority']),
                'descricao': 'Baixo impacto, Alto esforço',
                'dados': quadrantes['low_priority']
            }
        }
    except Exception as e:
        logger.error(f"Erro ao obter quadrantes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
