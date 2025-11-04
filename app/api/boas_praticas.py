# -*- coding: utf-8 -*-
"""
Router FastAPI para endpoints de boas práticas
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json

from app.database import (
    get_falhas_mercado,
    listar_priorizacoes,
    obter_fontes_por_falha,
    listar_boas_praticas_por_falha,
    salvar_boa_pratica,
    limpar_boas_praticas_fase,
    get_resultados_by_falha
)
from app.agente.analisador_boas_praticas import AnalisadorBoasPraticas
from app.utils.content_fetcher import enrich_sources_with_full_content
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/boas-praticas",
    tags=["boas-praticas"]
)

analisador = AnalisadorBoasPraticas()


# Models Pydantic
class BoaPratica(BaseModel):
    """Model para uma boa prática"""
    titulo: str
    descricao: Optional[str] = None
    is_sebrae: bool = False
    fonte: Optional[str] = None


class FalhaPriorizadaFase1(BaseModel):
    """Model para falha priorizada na Fase I (apenas listagem)"""
    falha_id: int
    titulo: str
    pilar: str
    descricao: str
    num_fontes: int  # Quantidade de fontes disponíveis


class ListarFalhasFase1Response(BaseModel):
    """Response da Fase I - listagem de falhas priorizadas"""
    falhas: List[FalhaPriorizadaFase1]
    total: int


class BoasPraticasFalha(BaseModel):
    """Model para boas práticas de uma falha (Fase II)"""
    falha_id: int
    titulo: str
    pilar: str
    praticas: List[BoaPratica]


class AnalisarFase2Response(BaseModel):
    """Response da Fase II - análise com IA"""
    falha_id: int
    titulo: str
    pilar: str
    praticas: List[BoaPratica]
    total_praticas: int


@router.get("/fase1/listar", response_model=ListarFalhasFase1Response)
async def listar_falhas_fase1():
    """
    FASE I: Lista falhas priorizadas sem executar análise de IA

    Retorna apenas a lista de falhas destacadas com suas informações básicas
    e quantidade de fontes disponíveis para análise posterior.
    """
    try:
        logger.info("Fase I: Listando falhas priorizadas")

        # Obter falhas priorizadas (apenas destacadas)
        todas_priorizacoes = await listar_priorizacoes()
        priorizacoes = [p for p in todas_priorizacoes if p.get('destacada')]

        if not priorizacoes:
            logger.warning("Nenhuma falha destacada encontrada")
            return ListarFalhasFase1Response(falhas=[], total=0)

        logger.info(f"Encontradas {len(priorizacoes)} falhas destacadas")

        # Montar resposta apenas com dados básicos
        falhas = []
        for prio in priorizacoes:
            falha_id = prio['falha_id']

            # Contar fontes disponíveis
            fontes = await obter_fontes_por_falha(falha_id)

            falhas.append(FalhaPriorizadaFase1(
                falha_id=falha_id,
                titulo=prio['titulo'],
                pilar=prio['pilar'],
                descricao=prio.get('descricao', ''),
                num_fontes=len(fontes)
            ))

        return ListarFalhasFase1Response(
            falhas=falhas,
            total=len(falhas)
        )

    except Exception as e:
        logger.error(f"Erro na Fase I: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fase2/analisar/{falha_id}", response_model=AnalisarFase2Response)
async def analisar_falha_fase2(falha_id: int, reprocessar: bool = False):
    """
    FASE II: Executa análise com IA para uma falha específica

    Processo:
    1. Obtém fontes (resultados de pesquisa + documentos)
    2. Enriquece fontes com conteúdo completo via Jina.ai
    3. Extrai trechos de documentos com soft cut
    4. Executa análise com LLM
    5. Salva boas práticas identificadas no banco

    Args:
        falha_id: ID da falha a analisar
        reprocessar: Se True, limpa práticas existentes e reanalisa
    """
    try:
        logger.info(f"Fase II: Analisando falha {falha_id}")

        # Verificar se falha existe
        falhas = await get_falhas_mercado()
        falha = next((f for f in falhas if f['id'] == falha_id), None)

        if not falha:
            raise HTTPException(status_code=404, detail="Falha não encontrada")

        # Se reprocessar, limpar práticas existentes
        if reprocessar:
            await limpar_boas_praticas_fase(falha_id, 'fase_2')
            logger.info(f"Práticas existentes limpas para reprocessamento")

        # 1. Obter fontes básicas
        fontes = await obter_fontes_por_falha(falha_id)
        logger.info(f"Obtidas {len(fontes)} fontes para análise")

        if not fontes:
            logger.warning(f"Nenhuma fonte disponível para falha {falha_id}")
            return AnalisarFase2Response(
                falha_id=falha_id,
                titulo=falha['titulo'],
                pilar=falha['pilar'],
                praticas=[],
                total_praticas=0
            )

        # 2. Enriquecer fontes com conteúdo completo
        logger.info("Enriquecendo fontes com conteúdo completo...")
        fontes_enriquecidas = await enrich_sources_with_full_content(fontes)

        # 3. Analisar com LLM
        logger.info("Executando análise com IA...")
        praticas_extraidas = await analisador.analisar_boas_praticas(
            falha=falha,
            fontes=fontes_enriquecidas
        )

        # 4. Salvar no banco
        for pratica in praticas_extraidas:
            await salvar_boa_pratica(
                falha_id=falha_id,
                titulo=pratica.get('titulo'),
                descricao=pratica.get('descricao'),
                is_sebrae=pratica.get('is_sebrae', False),
                fonte_referencia=pratica.get('fonte'),
                fase='fase_2'
            )

        logger.info(f"Análise concluída: {len(praticas_extraidas)} práticas identificadas")

        # Converter para Pydantic models
        praticas_models = [
            BoaPratica(
                titulo=p.get('titulo'),
                descricao=p.get('descricao'),
                is_sebrae=p.get('is_sebrae', False),
                fonte=p.get('fonte')
            )
            for p in praticas_extraidas
        ]

        return AnalisarFase2Response(
            falha_id=falha_id,
            titulo=falha['titulo'],
            pilar=falha['pilar'],
            praticas=praticas_models,
            total_praticas=len(praticas_models)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na Fase II para falha {falha_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fase1/fontes/{falha_id}")
async def obter_fontes_falha_fase1(falha_id: int, limit: int = 20):
    """
    Obtém as fontes disponíveis para uma falha na Fase I

    Retorna todas as fontes (resultados de pesquisa e documentos RAG)
    disponíveis para a falha especificada.

    Args:
        falha_id: ID da falha
        limit: Número máximo de fontes a retornar (padrão: 20)
    """
    try:
        logger.info(f"Fase I: Obtendo fontes para falha {falha_id} (limit={limit})")

        # Buscar TODAS as fontes disponíveis diretamente das tabelas originais
        # 1. Resultados de pesquisa
        resultados_pesquisa = await get_resultados_by_falha(falha_id)

        # 2. Fontes salvas (documentos RAG que foram usados na priorização)
        fontes_salvas = await obter_fontes_por_falha(falha_id)

        # Formatar resultados de pesquisa
        fontes_formatadas = []

        # Adicionar resultados de pesquisa (limitando)
        for resultado in resultados_pesquisa[:limit]:
            fontes_formatadas.append({
                "id": resultado.get('id'),
                "tipo": "resultado_pesquisa",
                "titulo": resultado.get('titulo'),
                "descricao": resultado.get('descricao'),
                "url": resultado.get('fonte_url'),
                "idioma": resultado.get('idioma'),
                "pais_origem": resultado.get('pais_origem'),
                "criado_em": resultado.get('criado_em')
            })

        # Adicionar documentos RAG salvos
        for fonte in fontes_salvas:
            if fonte.get('fonte_tipo') == 'documento':
                fontes_formatadas.append({
                    "id": fonte.get('id'),
                    "tipo": "documento",
                    "titulo": fonte.get('fonte_titulo'),
                    "descricao": fonte.get('fonte_descricao'),
                    "url": fonte.get('fonte_url'),
                    "idioma": None,
                    "pais_origem": None,
                    "criado_em": fonte.get('criado_em')
                })

        logger.info(f"Fontes encontradas: {len(fontes_formatadas)} ({len(resultados_pesquisa)} pesquisas, {len([f for f in fontes_salvas if f.get('fonte_tipo') == 'documento'])} documentos)")

        return {
            "falha_id": falha_id,
            "fontes": fontes_formatadas,
            "total": len(fontes_formatadas),
            "total_pesquisas": len(resultados_pesquisa),
            "total_documentos": len([f for f in fontes_salvas if f.get('fonte_tipo') == 'documento'])
        }

    except Exception as e:
        logger.error(f"Erro ao obter fontes da falha {falha_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/falha/{falha_id}")
async def obter_boas_praticas_falha(falha_id: int):
    """
    Obtém boas práticas para uma falha específica
    """
    try:
        # Obter detalhes da falha
        falhas = await get_falhas_mercado()
        falha = next((f for f in falhas if f['id'] == falha_id), None)

        if not falha:
            raise HTTPException(status_code=404, detail="Falha não encontrada")

        # Obter fontes
        fontes = await obter_fontes_por_falha(falha_id)

        # Analisar
        praticas = await analisador.analisar_boas_praticas(
            falha=falha,
            fontes=fontes
        )

        return {
            "falha_id": falha_id,
            "titulo": falha['titulo'],
            "pilar": falha['pilar'],
            "praticas": praticas
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter boas práticas da falha {falha_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
