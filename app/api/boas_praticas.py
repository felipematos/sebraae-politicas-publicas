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
    get_resultados_by_falha,
    gerar_hash_fonte,
    obter_analise_fonte_cache,
    salvar_analise_fonte_cache,
    obter_analises_fontes_lote
)
from app.agente.analisador_boas_praticas import AnalisadorBoasPraticas
from app.utils.content_fetcher import enrich_sources_with_full_content
from app.utils.logger import logger
from app.integracao.openrouter_api import OpenRouterClient
import asyncio

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
    num_fontes: int  # Quantidade total de fontes disponíveis
    num_fontes_filtradas: Optional[int] = None  # Quantidade após aplicar filtros


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


# ===== FUNÇÕES AUXILIARES =====

async def enriquecer_fontes_com_analises(fontes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enriquece fontes com análises de LLM (usando cache quando possível)

    Para cada fonte:
    1. Gera hash único
    2. Verifica se já existe análise em cache
    3. Se não, chama LLM e salva no cache
    4. Adiciona análise à fonte

    Args:
        fontes: Lista de fontes a enriquecer

    Returns:
        Fontes com campos adicionais: tipo_fonte_llm, tem_implementacao_llm, tem_metricas_llm
    """
    if not fontes:
        return fontes

    logger.info(f"Enriquecendo {len(fontes)} fontes com análises de LLM...")

    # 1. Gerar hashes de todas as fontes
    fonte_hashes = {}
    for fonte in fontes:
        hash_fonte = await gerar_hash_fonte(
            titulo=fonte.get('titulo', ''),
            descricao=fonte.get('descricao', ''),
            url=fonte.get('url', '')
        )
        fonte_hashes[hash_fonte] = fonte
        fonte['_hash'] = hash_fonte

    # 2. Buscar análises em cache (batch)
    analises_cache = await obter_analises_fontes_lote(list(fonte_hashes.keys()))
    logger.info(f"Encontradas {len(analises_cache)} análises em cache")

    # 3. Identificar fontes que precisam de análise
    fontes_para_analisar = []
    for hash_fonte, fonte in fonte_hashes.items():
        if hash_fonte in analises_cache:
            # Usar análise do cache
            analise = analises_cache[hash_fonte]
            fonte['tipo_fonte_llm'] = analise.get('tipo_fonte')
            fonte['tem_implementacao_llm'] = bool(analise.get('tem_implementacao'))
            fonte['tem_metricas_llm'] = bool(analise.get('tem_metricas'))
        else:
            # Precisa analisar
            fontes_para_analisar.append(fonte)

    # 4. Analisar fontes sem cache (em lote com limite de concorrência)
    if fontes_para_analisar:
        logger.info(f"Analisando {len(fontes_para_analisar)} fontes com LLM...")

        async with OpenRouterClient() as client:
            # Limitar concorrência para não sobrecarregar API
            semaphore = asyncio.Semaphore(5)  # Máximo 5 análises simultâneas

            async def analisar_e_cachear(fonte):
                async with semaphore:
                    try:
                        # Usar traduções quando disponíveis para garantir acurácia multilíngue
                        analise = await client.analisar_fonte(
                            titulo=fonte.get('titulo', ''),
                            descricao=fonte.get('descricao', ''),
                            url=fonte.get('url'),
                            titulo_pt=fonte.get('titulo_pt'),
                            descricao_pt=fonte.get('descricao_pt'),
                            idioma=fonte.get('idioma')
                        )

                        # Salvar no cache
                        await salvar_analise_fonte_cache(
                            fonte_hash=fonte['_hash'],
                            tipo_fonte=analise.get('tipo_fonte'),
                            tem_implementacao=analise.get('tem_implementacao', False),
                            tem_metricas=analise.get('tem_metricas', False),
                            analise_llm=json.dumps(analise),
                            modelo_usado='xai/grok-4-fast',
                            fonte_id=fonte.get('id'),
                            fonte_url=fonte.get('url')
                        )

                        # Adicionar à fonte
                        fonte['tipo_fonte_llm'] = analise.get('tipo_fonte')
                        fonte['tem_implementacao_llm'] = analise.get('tem_implementacao', False)
                        fonte['tem_metricas_llm'] = analise.get('tem_metricas', False)

                        logger.info(f"✓ Análise: {fonte.get('titulo', '')[:50]} -> {analise.get('tipo_fonte')}")

                    except Exception as e:
                        logger.error(f"Erro ao analisar fonte: {str(e)}")
                        # Fallback: deixar como desconhecido
                        fonte['tipo_fonte_llm'] = 'desconhecido'
                        fonte['tem_implementacao_llm'] = False
                        fonte['tem_metricas_llm'] = False

            # Executar análises em paralelo (com limite)
            await asyncio.gather(*[analisar_e_cachear(f) for f in fontes_para_analisar])

    logger.info(f"Enriquecimento concluído!")
    return fontes


@router.get("/fase1/listar", response_model=ListarFalhasFase1Response)
async def listar_falhas_fase1(
    # Filtros opcionais (mesmos do endpoint de fontes)
    confianca_minima: float = 0.0,
    peso_sebrae: int = 1,
    tipo_fonte: str = "",
    anos_publicacao: str = "todos",
    regiao: str = "",
    idioma: str = "",
    apenas_com_implementacao: bool = False,
    apenas_com_metricas: bool = False
):
    """
    FASE I: Lista falhas priorizadas sem executar análise de IA

    Retorna apenas a lista de falhas destacadas com suas informações básicas
    e quantidade de fontes disponíveis para análise posterior.

    Se filtros forem fornecidos, também calcula num_fontes_filtradas.
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

        # Verificar se há filtros ativos (além dos defaults)
        filtros_basicos_ativos = (
            confianca_minima > 0.0 or
            peso_sebrae != 1 or
            anos_publicacao != "todos" or
            regiao or
            idioma
        )

        filtros_avancados_ativos = (
            tipo_fonte or
            apenas_com_implementacao or
            apenas_com_metricas
        )

        filtros_ativos = filtros_basicos_ativos or filtros_avancados_ativos

        # Parse de arrays de filtros
        tipos_fonte_selecionados = [t.strip() for t in tipo_fonte.split(',') if t.strip()]
        regioes_selecionadas = [r.strip() for r in regiao.split(',') if r.strip()]
        idiomas_selecionados = [i.strip() for i in idioma.split(',') if i.strip()]

        # Montar resposta apenas com dados básicos
        falhas = []
        for prio in priorizacoes:
            falha_id = prio['falha_id']

            # Contar TODAS as fontes disponíveis (resultados de pesquisa + documentos)
            resultados = await get_resultados_by_falha(falha_id)
            documentos = await obter_fontes_por_falha(falha_id)
            total_fontes = len(resultados) + len([d for d in documentos if d.get('fonte_tipo') == 'documento'])

            # Se há filtros ativos, calcular contagem filtrada
            num_fontes_filtradas = None
            if filtros_ativos:
                # Formatar fontes
                fontes_formatadas = []
                for resultado in resultados:
                    fontes_formatadas.append({
                        "titulo": resultado.get('titulo'),
                        "url": resultado.get('fonte_url'),
                        "confidence_score": resultado.get('confidence_score', 0.5),
                        "pais_origem": resultado.get('pais_origem'),
                        "idioma": resultado.get('idioma')
                    })

                for fonte in documentos:
                    if fonte.get('fonte_tipo') == 'documento':
                        fontes_formatadas.append({
                            "titulo": fonte.get('fonte_titulo'),
                            "url": fonte.get('fonte_url'),
                            "confidence_score": 0.7,
                            "pais_origem": None,
                            "idioma": None
                        })

                # Aplicar filtros
                fontes_filtradas_list = []
                for fonte in fontes_formatadas:
                    # 1. Filtro de confiança mínima
                    if fonte['confidence_score'] < confianca_minima:
                        continue

                    # 2. Filtro de região
                    if regioes_selecionadas:
                        pais = (fonte.get('pais_origem') or '').lower()
                        paises_latam = ['argentina', 'chile', 'colombia', 'mexico', 'peru',
                                       'uruguay', 'venezuela', 'ecuador', 'bolivia', 'paraguay',
                                       'brasil', 'brazil']

                        aceitar_fonte = False
                        if 'brasil' in regioes_selecionadas and pais in ['brasil', 'brazil', 'br']:
                            aceitar_fonte = True
                        if 'latam' in regioes_selecionadas and any(p in pais for p in paises_latam):
                            aceitar_fonte = True
                        if 'global' in regioes_selecionadas:
                            aceitar_fonte = True

                        if not aceitar_fonte:
                            continue

                    # 3. Filtro de idioma
                    if idiomas_selecionados:
                        idioma_fonte = (fonte.get('idioma') or '').lower()
                        if idioma_fonte and idioma_fonte not in idiomas_selecionados:
                            continue

                    fontes_filtradas_list.append(fonte)

                # 4. Aplicar filtros avançados com LLM (se necessário)
                if filtros_avancados_ativos and fontes_filtradas_list:
                    logger.info(f"Aplicando filtros avançados para falha {falha_id}...")

                    # Enriquecer fontes com análises LLM (usa cache quando possível)
                    fontes_filtradas_list = await enriquecer_fontes_com_analises(fontes_filtradas_list)

                    # Aplicar filtros baseados nas análises
                    fontes_filtradas_final = []
                    for fonte in fontes_filtradas_list:
                        # Filtro de tipo de fonte
                        if tipos_fonte_selecionados:
                            tipo_llm = fonte.get('tipo_fonte_llm', 'desconhecido')
                            if tipo_llm not in tipos_fonte_selecionados:
                                continue

                        # Filtro de implementação
                        if apenas_com_implementacao:
                            if not fonte.get('tem_implementacao_llm', False):
                                continue

                        # Filtro de métricas
                        if apenas_com_metricas:
                            if not fonte.get('tem_metricas_llm', False):
                                continue

                        fontes_filtradas_final.append(fonte)

                    fontes_filtradas_list = fontes_filtradas_final

                num_fontes_filtradas = len(fontes_filtradas_list)

            falhas.append(FalhaPriorizadaFase1(
                falha_id=falha_id,
                titulo=prio['titulo'],
                pilar=prio['pilar'],
                descricao=prio.get('descricao', ''),
                num_fontes=total_fontes,
                num_fontes_filtradas=num_fontes_filtradas
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
async def obter_fontes_falha_fase1(
    falha_id: int,
    page: int = 1,
    page_size: int = 20,
    # Filtros
    confianca_minima: float = 0.0,
    peso_sebrae: int = 1,
    tipo_fonte: str = "",  # Array como string separada por vírgulas
    anos_publicacao: str = "todos",
    regiao: str = "",  # Array como string separada por vírgulas
    idioma: str = "",  # Array como string separada por vírgulas
    apenas_com_implementacao: bool = False,
    apenas_com_metricas: bool = False
):
    """
    Obtém as fontes disponíveis para uma falha na Fase I com paginação e filtros

    Retorna todas as fontes (resultados de pesquisa e documentos RAG)
    disponíveis para a falha especificada, ordenadas por score de confiança
    ajustado pelos filtros.

    Args:
        falha_id: ID da falha
        page: Número da página (começa em 1)
        page_size: Número de fontes por página (padrão: 20)
        confianca_minima: Score mínimo de confiança (0.0-1.0)
        peso_sebrae: Multiplicador de peso para fontes Sebrae (1, 2, 5, 10)
        tipo_fonte: Tipos de fonte separados por vírgula
        anos_publicacao: Filtro de período ("todos", "3", "5", "10")
        regiao: Regiões separadas por vírgula
        idioma: Idiomas separados por vírgula
        apenas_com_implementacao: Se True, retorna apenas fontes com casos de implementação
        apenas_com_metricas: Se True, retorna apenas fontes com métricas de impacto
    """
    try:
        logger.info(f"Fase I: Obtendo fontes para falha {falha_id} (page={page}, page_size={page_size})")

        # Buscar TODAS as fontes disponíveis diretamente das tabelas originais
        # 1. Resultados de pesquisa
        resultados_pesquisa = await get_resultados_by_falha(falha_id)

        # 2. Fontes salvas (documentos RAG que foram usados na priorização)
        fontes_salvas = await obter_fontes_por_falha(falha_id)

        # Formatar e consolidar todas as fontes
        fontes_formatadas = []

        # Adicionar resultados de pesquisa com score
        for resultado in resultados_pesquisa:
            fontes_formatadas.append({
                "id": resultado.get('id'),
                "tipo": "resultado_pesquisa",
                "titulo": resultado.get('titulo'),
                "descricao": resultado.get('descricao'),
                "url": resultado.get('fonte_url'),
                "idioma": resultado.get('idioma'),
                "pais_origem": resultado.get('pais_origem'),
                "confidence_score": resultado.get('confidence_score', 0.5),
                "criado_em": resultado.get('criado_em'),
                "titulo_pt": resultado.get('titulo_pt'),
                "descricao_pt": resultado.get('descricao_pt'),
                "titulo_en": resultado.get('titulo_en'),
                "descricao_en": resultado.get('descricao_en')
            })

        # Adicionar documentos RAG salvos (score padrão 0.7 para documentos curados)
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
                    "confidence_score": 0.7,  # Score padrão para documentos curados
                    "criado_em": fonte.get('criado_em')
                })

        # ===== APLICAR FILTROS =====

        # Parse de arrays de filtros (vêm como strings separadas por vírgula)
        tipos_fonte_selecionados = [t.strip() for t in tipo_fonte.split(',') if t.strip()]
        regioes_selecionadas = [r.strip() for r in regiao.split(',') if r.strip()]
        idiomas_selecionados = [i.strip() for i in idioma.split(',') if i.strip()]

        logger.info(f"Filtros aplicados - Confiança: {confianca_minima}, Peso Sebrae: {peso_sebrae}x, "
                   f"Tipos: {tipos_fonte_selecionados}, Regiões: {regioes_selecionadas}, "
                   f"Idiomas: {idiomas_selecionados}")

        # Função auxiliar para verificar se fonte é do Sebrae
        def is_fonte_sebrae(fonte: dict) -> bool:
            """Verifica se a fonte é do Sebrae baseado no título ou URL"""
            titulo = (fonte.get('titulo') or '').lower()
            url = (fonte.get('url') or '').lower()
            return 'sebrae' in titulo or 'sebrae' in url

        # Aplicar filtros e ajustar scores
        fontes_filtradas = []
        for fonte in fontes_formatadas:
            # 1. Filtro de confiança mínima
            score_original = fonte['confidence_score']
            if score_original < confianca_minima:
                continue

            # 2. Aplicar multiplicador Sebrae
            score_ajustado = score_original
            if is_fonte_sebrae(fonte):
                fonte['is_sebrae'] = True
                score_ajustado = min(score_original * peso_sebrae, 1.0)  # Cap em 1.0
            else:
                fonte['is_sebrae'] = False

            fonte['score_ajustado'] = score_ajustado

            # 3. Filtro de tipo de fonte (se especificado)
            if tipos_fonte_selecionados:
                # Mapear tipos - precisa de análise de conteúdo mais sofisticada
                # Por ora, aceitar todas se houver filtros (implementação simplificada)
                pass

            # 4. Filtro de região (se especificado)
            if regioes_selecionadas:
                pais = (fonte.get('pais_origem') or '').lower()
                paises_latam = ['argentina', 'chile', 'colombia', 'mexico', 'peru',
                               'uruguay', 'venezuela', 'ecuador', 'bolivia', 'paraguay',
                               'brasil', 'brazil']

                aceitar_fonte = False

                # Verificar cada região selecionada
                if 'brasil' in regioes_selecionadas:
                    if pais in ['brasil', 'brazil', 'br']:
                        aceitar_fonte = True

                if 'latam' in regioes_selecionadas:
                    if any(p in pais for p in paises_latam):
                        aceitar_fonte = True

                if 'global' in regioes_selecionadas:
                    # Global aceita qualquer país
                    aceitar_fonte = True

                # Se nenhuma região aceitou, pular fonte
                if not aceitar_fonte:
                    continue

            # 5. Filtro de idioma (se especificado)
            if idiomas_selecionados:
                fonte_idioma = (fonte.get('idioma') or '').lower()
                # Mapear códigos de idioma
                if not any(idioma_sel.lower() in fonte_idioma or fonte_idioma in idioma_sel.lower()
                          for idioma_sel in idiomas_selecionados):
                    continue

            # 6. Filtro de período de publicação
            if anos_publicacao != "todos":
                from datetime import datetime, timedelta
                try:
                    anos = int(anos_publicacao)
                    data_limite = datetime.now() - timedelta(days=anos*365)
                    data_criacao = fonte.get('criado_em')

                    if data_criacao:
                        # Tentar parsear a data
                        if isinstance(data_criacao, str):
                            try:
                                data_obj = datetime.fromisoformat(data_criacao.replace('Z', '+00:00'))
                                if data_obj < data_limite:
                                    continue
                            except:
                                pass  # Se não conseguir parsear, aceitar
                except:
                    pass

            fontes_filtradas.append(fonte)

        # 7. Filtros avançados com LLM (se necessário)
        # Aplicar ANTES da paginação para garantir resultados corretos
        if tipos_fonte_selecionados or apenas_com_implementacao or apenas_com_metricas:
            logger.info(f"Aplicando filtros avançados com LLM...")

            # Enriquecer fontes com análises (usa cache quando possível)
            fontes_filtradas = await enriquecer_fontes_com_analises(fontes_filtradas)

            # Aplicar filtros baseados nas análises
            fontes_filtradas_final = []
            for fonte in fontes_filtradas:
                # Filtro de tipo de fonte
                if tipos_fonte_selecionados:
                    tipo_llm = fonte.get('tipo_fonte_llm', 'desconhecido')
                    if tipo_llm not in tipos_fonte_selecionados:
                        continue

                # Filtro de implementação
                if apenas_com_implementacao:
                    if not fonte.get('tem_implementacao_llm', False):
                        continue

                # Filtro de métricas
                if apenas_com_metricas:
                    if not fonte.get('tem_metricas_llm', False):
                        continue

                fontes_filtradas_final.append(fonte)

            fontes_filtradas = fontes_filtradas_final
            logger.info(f"Após filtros avançados: {len(fontes_filtradas)} fontes")

        # Ordenar por score ajustado (maior para menor)
        fontes_filtradas.sort(key=lambda x: x['score_ajustado'], reverse=True)

        # Calcular totais (usando fontes filtradas)
        total_fontes = len(fontes_filtradas)
        total_fontes_original = len(fontes_formatadas)
        total_pages = (total_fontes + page_size - 1) // page_size if total_fontes > 0 else 1

        # Aplicar paginação
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        fontes_pagina = fontes_filtradas[start_idx:end_idx]

        logger.info(f"Fontes filtradas: {total_fontes}/{total_fontes_original} "
                   f"({len(resultados_pesquisa)} pesquisas, "
                   f"{len([f for f in fontes_salvas if f.get('fonte_tipo') == 'documento'])} documentos) - "
                   f"Página {page}/{total_pages}")

        return {
            "falha_id": falha_id,
            "fontes": fontes_pagina,
            "total": total_fontes,
            "total_sem_filtro": total_fontes_original,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "total_pesquisas": len(resultados_pesquisa),
            "total_documentos": len([f for f in fontes_salvas if f.get('fonte_tipo') == 'documento']),
            "filtros_aplicados": {
                "confianca_minima": confianca_minima,
                "peso_sebrae": peso_sebrae,
                "tipos_fonte": tipos_fonte_selecionados,
                "regioes": regioes_selecionadas,
                "idiomas": idiomas_selecionados,
                "anos_publicacao": anos_publicacao,
                "apenas_implementacao": apenas_com_implementacao,
                "apenas_metricas": apenas_com_metricas
            }
        }

    except Exception as e:
        logger.error(f"Erro ao obter fontes da falha {falha_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fase1/estimar-custo/{falha_id}")
async def estimar_custo_analise_fase1(
    falha_id: int,
    # Filtros (mesmos do endpoint principal)
    confianca_minima: float = 0.0,
    peso_sebrae: int = 1,
    tipo_fonte: str = "",
    anos_publicacao: str = "todos",
    regiao: str = "",
    idioma: str = "",
    apenas_com_implementacao: bool = False,
    apenas_com_metricas: bool = False
):
    """
    Estima o custo e tempo de execução de uma análise antes de executá-la

    Calcula:
    - Total de fontes que serão processadas
    - Quantas já estão em cache
    - Quantas precisam de análise LLM
    - Tempo estimado (considerando 5 análises paralelas)
    - Custo estimado (baseado em Grok 4 Fast)

    Returns:
        dict com estimativas detalhadas
    """
    try:
        logger.info(f"Estimando custo de análise para falha {falha_id}")

        # Buscar TODAS as fontes disponíveis (mesma lógica do endpoint principal)
        resultados_pesquisa = await get_resultados_by_falha(falha_id)
        fontes_salvas = await obter_fontes_por_falha(falha_id)

        # Formatar fontes
        fontes_formatadas = []

        for resultado in resultados_pesquisa:
            fontes_formatadas.append({
                "id": resultado.get('id'),
                "tipo": "resultado_pesquisa",
                "titulo": resultado.get('titulo'),
                "descricao": resultado.get('descricao'),
                "url": resultado.get('fonte_url'),
                "idioma": resultado.get('idioma'),
                "pais_origem": resultado.get('pais_origem'),
                "confidence_score": resultado.get('confidence_score', 0.5),
                "criado_em": resultado.get('criado_em'),
                "titulo_pt": resultado.get('titulo_pt'),
                "descricao_pt": resultado.get('descricao_pt'),
                "titulo_en": resultado.get('titulo_en'),
                "descricao_en": resultado.get('descricao_en')
            })

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
                    "confidence_score": 0.7,
                    "criado_em": fonte.get('criado_em')
                })

        # ===== APLICAR MESMOS FILTROS DO ENDPOINT PRINCIPAL =====

        tipos_fonte_selecionados = [t.strip() for t in tipo_fonte.split(',') if t.strip()]
        regioes_selecionadas = [r.strip() for r in regiao.split(',') if r.strip()]
        idiomas_selecionados = [i.strip() for i in idioma.split(',') if i.strip()]

        def is_fonte_sebrae(fonte: dict) -> bool:
            titulo = (fonte.get('titulo') or '').lower()
            url = (fonte.get('url') or '').lower()
            return 'sebrae' in titulo or 'sebrae' in url

        # Aplicar filtros básicos
        fontes_filtradas = []
        for fonte in fontes_formatadas:
            # Filtro de confiança
            if fonte['confidence_score'] < confianca_minima:
                continue

            # Filtro de região
            if regioes_selecionadas:
                pais = (fonte.get('pais_origem') or '').lower()
                paises_latam = ['argentina', 'chile', 'colombia', 'mexico', 'peru',
                               'uruguay', 'venezuela', 'ecuador', 'bolivia', 'paraguay',
                               'brasil', 'brazil']
                aceitar_fonte = False
                if 'brasil' in regioes_selecionadas and pais in ['brasil', 'brazil', 'br']:
                    aceitar_fonte = True
                if 'latam' in regioes_selecionadas and any(p in pais for p in paises_latam):
                    aceitar_fonte = True
                if 'global' in regioes_selecionadas:
                    aceitar_fonte = True
                if not aceitar_fonte:
                    continue

            # Filtro de idioma
            if idiomas_selecionados:
                fonte_idioma = (fonte.get('idioma') or '').lower()
                if not any(idioma_sel.lower() in fonte_idioma or fonte_idioma in idioma_sel.lower()
                          for idioma_sel in idiomas_selecionados):
                    continue

            # Filtro de período
            if anos_publicacao != "todos":
                from datetime import datetime, timedelta
                try:
                    anos = int(anos_publicacao)
                    data_limite = datetime.now() - timedelta(days=anos*365)
                    data_criacao = fonte.get('criado_em')
                    if data_criacao and isinstance(data_criacao, str):
                        try:
                            data_obj = datetime.fromisoformat(data_criacao.replace('Z', '+00:00'))
                            if data_obj < data_limite:
                                continue
                        except:
                            pass
                except:
                    pass

            fontes_filtradas.append(fonte)

        total_fontes_apos_filtros = len(fontes_filtradas)

        # ===== VERIFICAR QUAIS PRECISAM DE ANÁLISE LLM =====

        # Só precisa de análise LLM se houver filtros avançados
        precisa_llm = bool(tipos_fonte_selecionados or apenas_com_implementacao or apenas_com_metricas)

        fontes_em_cache = 0
        fontes_a_analisar = 0

        if precisa_llm and fontes_filtradas:
            # Gerar hashes
            fonte_hashes = []
            for fonte in fontes_filtradas:
                hash_fonte = await gerar_hash_fonte(
                    titulo=fonte.get('titulo', ''),
                    descricao=fonte.get('descricao', ''),
                    url=fonte.get('url', '')
                )
                fonte_hashes.append(hash_fonte)

            # Verificar cache em lote
            analises_cache = await obter_analises_fontes_lote(fonte_hashes)
            fontes_em_cache = len(analises_cache)
            fontes_a_analisar = len(fontes_filtradas) - fontes_em_cache

        # ===== CALCULAR ESTIMATIVAS =====

        # Tempo: Com semaphore de 5, processamos 5 análises em paralelo
        # Cada análise leva ~2-3 segundos
        tempo_por_lote = 2.5  # segundos (média)
        if fontes_a_analisar > 0:
            num_lotes = (fontes_a_analisar + 4) // 5  # Arredonda pra cima
            tempo_estimado_segundos = num_lotes * tempo_por_lote
        else:
            tempo_estimado_segundos = 1  # Apenas busca em cache

        # Custo: Grok 4 Fast é ~$0.0005 por 1K tokens
        # Cada análise usa ~500 tokens (prompt + response)
        # = ~$0.00025 por análise
        custo_por_analise = 0.00025
        custo_estimado_usd = fontes_a_analisar * custo_por_analise

        # Formatar tempo de forma amigável
        if tempo_estimado_segundos < 60:
            tempo_formatado = f"~{int(tempo_estimado_segundos)} segundos"
        else:
            minutos = int(tempo_estimado_segundos // 60)
            segundos = int(tempo_estimado_segundos % 60)
            tempo_formatado = f"~{minutos}m {segundos}s"

        return {
            "falha_id": falha_id,
            "total_fontes_disponiveis": len(fontes_formatadas),
            "total_fontes_apos_filtros": total_fontes_apos_filtros,
            "precisa_analise_llm": precisa_llm,
            "fontes_em_cache": fontes_em_cache,
            "fontes_a_analisar": fontes_a_analisar,
            "tempo_estimado_segundos": tempo_estimado_segundos,
            "tempo_estimado_formatado": tempo_formatado,
            "custo_estimado_usd": round(custo_estimado_usd, 4),
            "custo_estimado_formatado": f"${custo_estimado_usd:.4f} USD",
            "detalhes": {
                "filtros_ativos": {
                    "confianca_minima": confianca_minima,
                    "peso_sebrae": peso_sebrae,
                    "tipos_fonte": tipos_fonte_selecionados,
                    "regioes": regioes_selecionadas,
                    "idiomas": idiomas_selecionados,
                    "anos_publicacao": anos_publicacao,
                    "apenas_implementacao": apenas_com_implementacao,
                    "apenas_metricas": apenas_com_metricas
                },
                "modelo_llm": "xai/grok-4-fast",
                "analises_paralelas": 5
            }
        }

    except Exception as e:
        logger.error(f"Erro ao estimar custo para falha {falha_id}: {str(e)}")
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


@router.get("/analise/estimar")
async def estimar_custo_tempo_reanalisar(
    num_fontes: int,
    modo: str = "gratuito"
):
    """
    Estima custo e tempo para reanalisar fontes com avaliação profunda

    Args:
        num_fontes: Número de fontes a reanalisar
        modo: Modo de avaliação ("premium", "balanceado", "gratuito")

    Returns:
        Estimativa de custo, tempo, modelo usado
    """
    try:
        async with OpenRouterClient() as client:
            estimativa = client.estimar_custo_tempo_avaliacao(num_fontes, modo)
            return estimativa

    except Exception as e:
        logger.error(f"Erro ao estimar custo/tempo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analise/reanalisar")
async def reanalisar_fontes(
    avaliar_profundamente: bool = False,
    modo_avaliacao: str = "gratuito"
):
    """
    Reanalisa todas as fontes existentes com novos critérios de avaliação

    Args:
        avaliar_profundamente: Se deve usar avaliação profunda via LLM
        modo_avaliacao: Modo de avaliação ("premium", "balanceado", "gratuito")

    Returns:
        Total de fontes reanalisadas
    """
    try:
        logger.info(f"Iniciando reanálise de fontes (profunda: {avaliar_profundamente}, modo: {modo_avaliacao})")

        # Obter todas as fontes (resultados de pesquisa)
        from app.database import get_todos_resultados, limpar_cache_analises

        todos_resultados = await get_todos_resultados()

        if not todos_resultados:
            return {"total_reanalisadas": 0, "mensagem": "Nenhuma fonte para reanalisar"}

        # Limpar cache de análises para forçar reavaliação
        await limpar_cache_analises()
        logger.info(f"Cache de análises limpo. Iniciando reanálise de {len(todos_resultados)} fontes...")

        # Formatar fontes para análise
        fontes = []
        for resultado in todos_resultados:
            fontes.append({
                "titulo": resultado.get('titulo'),
                "descricao": resultado.get('descricao', ''),
                "url": resultado.get('fonte_url'),
                "titulo_pt": resultado.get('titulo_pt'),
                "descricao_pt": resultado.get('descricao_pt'),
                "idioma": resultado.get('idioma'),
                "_hash": resultado.get('fonte_hash')
            })

        # Executar análise
        async with OpenRouterClient() as client:
            semaphore = asyncio.Semaphore(5)  # Máximo 5 análises simultâneas

            async def analisar_e_cachear(fonte):
                async with semaphore:
                    try:
                        # Escolher método de análise
                        if avaliar_profundamente:
                            analise = await client.analisar_fonte_profunda(
                                titulo=fonte.get('titulo', ''),
                                descricao=fonte.get('descricao', ''),
                                url=fonte.get('url'),
                                titulo_pt=fonte.get('titulo_pt'),
                                descricao_pt=fonte.get('descricao_pt'),
                                idioma=fonte.get('idioma'),
                                modo=modo_avaliacao
                            )
                        else:
                            analise = await client.analisar_fonte(
                                titulo=fonte.get('titulo', ''),
                                descricao=fonte.get('descricao', ''),
                                url=fonte.get('url'),
                                titulo_pt=fonte.get('titulo_pt'),
                                descricao_pt=fonte.get('descricao_pt'),
                                idioma=fonte.get('idioma')
                            )

                        # Salvar no cache
                        await salvar_analise_fonte_cache(
                            fonte_hash=fonte['_hash'],
                            tipo_fonte=analise.get('tipo_fonte'),
                            tem_implementacao=analise.get('tem_implementacao', False),
                            tem_metricas=analise.get('tem_metricas', False),
                            confianca_analise=analise.get('confianca', 0.0)
                        )

                        return True
                    except Exception as e:
                        logger.error(f"Erro ao reanalisar fonte: {str(e)}")
                        return False

            # Executar reanálises em paralelo
            resultados = await asyncio.gather(*[analisar_e_cachear(f) for f in fontes])

        total_reanalisadas = sum(1 for r in resultados if r)
        logger.info(f"Reanálise concluída: {total_reanalisadas}/{len(fontes)} fontes")

        return {
            "total_reanalisadas": total_reanalisadas,
            "total_fontes": len(fontes),
            "mensagem": f"Reanálise concluída com sucesso!"
        }

    except Exception as e:
        logger.error(f"Erro ao reanalisar fontes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
