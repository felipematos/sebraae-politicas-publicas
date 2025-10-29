# -*- coding: utf-8 -*-
"""
Agente para análise de priorização de falhas de mercado
Usa IA para avaliar impacto e esforço de implementação
"""
import json
import asyncio
from typing import Dict, Any, Optional, List
from app.database import (
    get_falha_by_id,
    get_resultados_by_falha,
    criar_priorizacao,
    atualizar_priorizacao,
    obter_priorizacao
)
from app.integracao.openrouter_api import consultar_openrouter
from app.utils.logger import logger

class AgentePriorizador:
    """Agente responsável por analisar e priorizar falhas de mercado"""

    def __init__(self):
        # Usar Tier 1 modelo com alta capacidade de raciocínio
        # Tenta modelo gratuito primeiro (llama-2-70b), depois fallback para Grok 4 Fast
        # Grok 4 Fast oferece extended thinking para análise mais profunda
        self.modelo_principal = "meta-llama/llama-2-70b-chat"  # Modelo gratuito principal
        self.modelo_fallback = "xai/grok-4-fast"  # Tier 1 com extended thinking

    async def analisar_falha(self, falha_id: int) -> Dict[str, Any]:
        """
        Analisa uma falha e retorna scores de impacto e esforço

        Retorna:
        {
            'falha_id': int,
            'impacto': int (0-10),
            'esforco': int (0-10),
            'analise': str,
            'sucesso': bool
        }
        """
        try:
            # Obter dados da falha
            falha = await get_falha_by_id(falha_id)
            if not falha:
                return {
                    'falha_id': falha_id,
                    'sucesso': False,
                    'erro': f'Falha {falha_id} não encontrada'
                }

            # Obter resultados de pesquisa da falha
            resultados = await get_resultados_by_falha(falha_id)

            # Obter contexto RAG da base de conhecimento
            rag_contexto = await self._obter_contexto_rag(falha)

            # Construir contexto para análise
            contexto = self._construir_contexto(falha, resultados, rag_contexto)

            # Chamar IA para análise
            resposta_ia = await self._consultar_ia(contexto, falha)

            # Processar resposta
            scores = self._extrair_scores(resposta_ia)

            # Salvar priorização
            priorization_existente = await obter_priorizacao(falha_id)

            if priorization_existente:
                await atualizar_priorizacao(
                    falha_id,
                    scores['impacto'],
                    scores['esforco'],
                    resposta_ia
                )
            else:
                await criar_priorizacao(
                    falha_id,
                    scores['impacto'],
                    scores['esforco'],
                    resposta_ia
                )

            logger.info(f"✓ Falha {falha_id} analisada: Impacto={scores['impacto']}, Esforço={scores['esforco']}")

            return {
                'falha_id': falha_id,
                'impacto': scores['impacto'],
                'esforco': scores['esforco'],
                'analise': resposta_ia,
                'sucesso': True
            }

        except Exception as e:
            logger.error(f"✗ Erro ao analisar falha {falha_id}: {str(e)}")
            return {
                'falha_id': falha_id,
                'sucesso': False,
                'erro': str(e)
            }

    async def _obter_contexto_rag(self, falha: Dict[str, Any]) -> str:
        """
        Consulta a base de conhecimento (RAG) para obter contexto adicional
        """
        try:
            from app.config import settings, get_chroma_path
            from app.vector.vector_store import get_vector_store
            from app.vector.embeddings import EmbeddingClient

            if not settings.RAG_ENABLED or not settings.USAR_VECTOR_DB:
                return ""

            # Obter vector store
            embedding_client = EmbeddingClient(api_key=settings.OPENAI_API_KEY)
            vector_store = await get_vector_store(
                persist_path=get_chroma_path(),
                embedding_client=embedding_client
            )

            # Query com o título e descrição da falha
            query_text = f"{falha['titulo']} {falha['descricao']}"

            # Buscar documentos similares
            resultados = vector_store.similarity_search(
                query_text,
                k=settings.RAG_TOP_K_RESULTS
            )

            if not resultados:
                return ""

            # Formatar resultados
            contexto_rag = "\nCONTEXTO DA BASE DE CONHECIMENTO:\n"
            for i, resultado in enumerate(resultados, 1):
                contexto_rag += f"\n{i}. {resultado.page_content[:300]}...\n"

            return contexto_rag

        except Exception as e:
            logger.warning(f"Erro ao obter contexto RAG: {str(e)}")
            return ""

    def _construir_contexto(self, falha: Dict[str, Any], resultados: List[Dict[str, Any]], rag_contexto: str = "") -> str:
        """Constrói contexto para análise"""
        contexto = f"""
FALHA DE MERCADO: {falha['titulo']}

PILAR: {falha['pilar']}

DESCRIÇÃO: {falha['descricao']}

ORIENTAÇÕES DE PESQUISA: {falha['dica_busca']}

TOTAL DE POLÍTICAS/ESTUDOS ENCONTRADOS: {len(resultados)}

EXEMPLOS DE POLÍTICAS RELACIONADAS:
"""
        # Incluir top 5 resultados como exemplo
        for resultado in resultados[:5]:
            contexto += f"\n- {resultado['titulo']}\n"
            if resultado.get('descricao'):
                contexto += f"  {resultado['descricao'][:200]}...\n"

        # Incluir contexto RAG se disponível
        if rag_contexto:
            contexto += rag_contexto

        return contexto

    async def _consultar_ia(self, contexto: str, falha: Dict[str, Any]) -> str:
        """Consulta IA para análise com fallback inteligente"""
        prompt = f"""
Você é um especialista em políticas públicas e ecossistema de inovação brasileiro.

Analise a seguinte falha de mercado e atribua:
1. Um score de IMPACTO (0-10): Qual o tamanho do impacto positivo que resolver essa falha pode gerar para o ecossistema de inovação brasileiro?
   - 0-2: Impacto muito pequeno
   - 3-4: Impacto pequeno
   - 5-6: Impacto moderado
   - 7-8: Impacto grande
   - 9-10: Impacto muito grande/crítico

2. Um score de ESFORÇO (0-10): Qual o nível de dificuldade e complexidade de implementação de soluções para essa falha?
   - 0-2: Muito fácil de implementar
   - 3-4: Fácil de implementar
   - 5-6: Moderadamente fácil
   - 7-8: Difícil de implementar
   - 9-10: Muito difícil/complexo

{contexto}

Responda EXATAMENTE no seguinte formato JSON:
{{
    "impacto": <número 0-10>,
    "esforço": <número 0-10>,
    "justificativa": "<explicação breve da análise em português>"
}}

IMPORTANTE: Responda APENAS com o JSON, sem texto adicional.
"""

        try:
            # Tentar com modelo gratuito principal primeiro
            resposta = await consultar_openrouter(prompt, modelo=self.modelo_principal)
            logger.info(f"✓ Análise completada com modelo principal: {self.modelo_principal}")
            return resposta
        except Exception as e:
            logger.warning(f"⚠ Modelo principal falhou: {str(e)[:100]}, tentando Grok 4 Fast...")

            try:
                # Fallback para Tier 1 modelo com extended thinking
                resposta = await consultar_openrouter(prompt, modelo=self.modelo_fallback)
                logger.info(f"✓ Análise completada com Grok 4 Fast (extended thinking)")
                return resposta
            except Exception as e2:
                logger.error(f"✗ Ambos os modelos falharam: {str(e2)}")
                # Retornar valores padrão em caso de erro
                return json.dumps({
                    "impacto": 5,
                    "esforço": 5,
                    "justificativa": f"Erro na análise com ambos os modelos"
                })

    def _extrair_scores(self, resposta_ia: str) -> Dict[str, int]:
        """Extrai scores de impacto e esforço da resposta da IA"""
        try:
            # Tentar parsear como JSON
            dados = json.loads(resposta_ia)
            impacto = int(dados.get('impacto', 5))
            esforco = int(dados.get('esforço', 5)) or int(dados.get('esforco', 5))

            # Validar ranges
            impacto = max(0, min(10, impacto))
            esforco = max(0, min(10, esforco))

            return {
                'impacto': impacto,
                'esforco': esforco
            }
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"Erro ao extrair scores: {str(e)}")
            # Retornar valores padrão
            return {
                'impacto': 5,
                'esforco': 5
            }

    async def analisar_todas_falhas(self) -> Dict[str, Any]:
        """
        Analisa todas as falhas sequencialmente

        Retorna:
        {
            'total_falhas': int,
            'analisadas': int,
            'falhadas': int,
            'erros': List[Dict]
        }
        """
        from app.database import get_falhas_mercado

        falhas = await get_falhas_mercado()

        total = len(falhas)
        analisadas = 0
        falhadas = 0
        erros = []

        logger.info(f"Iniciando análise de {total} falhas...")

        for idx, falha in enumerate(falhas, 1):
            resultado = await self.analisar_falha(falha['id'])

            if resultado['sucesso']:
                analisadas += 1
            else:
                falhadas += 1
                erros.append({
                    'falha_id': falha['id'],
                    'titulo': falha['titulo'],
                    'erro': resultado.get('erro')
                })

            logger.info(f"[{idx}/{total}] Falha #{falha['id']} analisada")

            # Pequeno delay entre requisições para evitar rate limits
            await asyncio.sleep(1)

        return {
            'total_falhas': total,
            'analisadas': analisadas,
            'falhadas': falhadas,
            'erros': erros,
            'sucesso': falhadas == 0
        }

    async def atualizar_scores(self, falha_id: int, impacto: int, esforco: int) -> Dict[str, Any]:
        """
        Atualiza scores de uma falha manualmente

        Recebe:
        - falha_id: ID da falha
        - impacto: score de 0-10
        - esforco: score de 0-10
        """
        try:
            # Validar ranges
            impacto = max(0, min(10, impacto))
            esforco = max(0, min(10, esforco))

            # Atualizar priorização
            await atualizar_priorizacao(falha_id, impacto, esforco)

            logger.info(f"✓ Scores atualizados para falha {falha_id}: Impacto={impacto}, Esforço={esforco}")

            return {
                'sucesso': True,
                'falha_id': falha_id,
                'impacto': impacto,
                'esforco': esforco
            }

        except Exception as e:
            logger.error(f"✗ Erro ao atualizar scores: {str(e)}")
            return {
                'sucesso': False,
                'erro': str(e)
            }
