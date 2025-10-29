# -*- coding: utf-8 -*-
"""
Router FastAPI para endpoints de priorização de falhas de mercado
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.database import (
    obter_priorizacao,
    listar_priorizacoes,
    listar_priorizacoes_sem_analise,
    gerar_matriz_2x2,
    obter_quadrantes_matriz,
    atualizar_priorizacao,
    criar_priorizacao,
    get_falhas_mercado
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
    """Model para análise em lote"""
    incluir_analisadas: bool = False  # Se False, analisa apenas as sem análise


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
async def obter_priorizacao_endpoint(falha_id: int) -> Dict[str, Any]:
    """
    Retorna a priorização de uma falha específica
    """
    try:
        priorizacao = await obter_priorizacao(falha_id)
        if not priorizacao:
            raise HTTPException(status_code=404, detail=f"Priorização para falha {falha_id} não encontrada")

        return {
            'sucesso': True,
            'dados': priorizacao
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


@router.post("/analisar-todas")
async def analisar_todas_falhas_endpoint(request: AnalisarTodasRequest = None) -> Dict[str, Any]:
    """
    Analisa todas as falhas usando IA
    Por padrão analisa apenas as que ainda não têm análise
    """
    try:
        resultado = await priorizador.analisar_todas_falhas()

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
    - quick_wins: Alto impacto, Baixo esforço (impacto >= 6, esforço <= 4)
    - strategic: Alto impacto, Alto esforço (impacto >= 6, esforço > 4)
    - fill_in: Baixo impacto, Baixo esforço (impacto < 6, esforço <= 4)
    - low_priority: Baixo impacto, Alto esforço (impacto < 6, esforço > 4)
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
