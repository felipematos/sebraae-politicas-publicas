# -*- coding: utf-8 -*-
"""
Agente para análise de priorização de falhas de mercado
Usa IA para avaliar impacto e esforço de implementação
"""
import json
import asyncio
import re
from typing import Dict, Any, Optional, List, Tuple
from app.database import (
    get_falha_by_id,
    get_resultados_by_falha,
    criar_priorizacao,
    atualizar_priorizacao,
    obter_priorizacao,
    inserir_fonte_priorizacao,
    limpar_fontes_priorizacao
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

    async def analisar_falha(
        self,
        falha_id: int,
        usar_rag: bool = True,
        usar_resultados_pesquisa: bool = True,
        temperatura: float = 0.3,
        max_tokens: int = 4000,
        modelo: str = "google/gemini-2.5-pro"
    ) -> Dict[str, Any]:
        """
        Analisa uma falha e retorna scores de impacto, esforço e fontes utilizadas

        Args:
            falha_id: ID da falha a ser analisada
            usar_rag: Se True, usa contexto da base de conhecimento RAG
            usar_resultados_pesquisa: Se True, usa resultados de pesquisa
            temperatura: Temperatura do modelo (0.0-1.0, padrão 0.3)
            max_tokens: Máximo de tokens na resposta (padrão 4000)

        Retorna:
        {
            'falha_id': int,
            'impacto': int (0-10),
            'esforco': int (0-10),
            'analise': str,
            'fontes': List[Dict] (fontes utilizadas),
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

            # Obter resultados de pesquisa da falha (se configurado)
            resultados = await get_resultados_by_falha(falha_id) if usar_resultados_pesquisa else []

            # Obter contexto RAG da base de conhecimento (se configurado)
            rag_contexto = await self._obter_contexto_rag(falha) if usar_rag else ""

            # Construir contexto para análise (agora retorna contexto E fontes)
            contexto, fontes = self._construir_contexto(falha, resultados, rag_contexto)

            # Chamar IA para análise com parâmetros configuráveis
            resposta_ia = await self._consultar_ia(contexto, falha, fontes, temperatura, max_tokens, modelo)

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
                priorizacao_id = priorization_existente['id']
            else:
                priorizacao_id = await criar_priorizacao(
                    falha_id,
                    scores['impacto'],
                    scores['esforco'],
                    resposta_ia
                )

            # Extrair e salvar fontes utilizadas pela IA
            fontes_utilizadas = self._extrair_fontes_resposta(resposta_ia, fontes)

            if priorizacao_id:
                # Limpar fontes antigas
                await limpar_fontes_priorizacao(priorizacao_id)
                # Salvar novas fontes
                for fonte in fontes_utilizadas:
                    await inserir_fonte_priorizacao(
                        priorizacao_id=priorizacao_id,
                        falha_id=falha_id,
                        fonte_tipo=fonte['tipo'],
                        fonte_id=fonte.get('id'),
                        fonte_titulo=fonte['titulo'],
                        fonte_descricao=fonte.get('descricao'),
                        fonte_url=fonte.get('url'),
                        fonte_conteudo=fonte.get('conteudo')
                    )

            logger.info(f"✓ Falha {falha_id} analisada: Impacto={scores['impacto']}, Esforço={scores['esforco']}, Fontes={len(fontes_utilizadas)}")

            return {
                'falha_id': falha_id,
                'impacto': scores['impacto'],
                'esforco': scores['esforco'],
                'analise': resposta_ia,
                'fontes': fontes_utilizadas,
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

            # Buscar documentos similares (método assíncrono)
            resultados = await vector_store.similarity_search(
                query_text,
                k=settings.RAG_TOP_K_RESULTS
            )

            if not resultados:
                return ""

            # Formatar resultados
            contexto_rag = "\nCONTEXTO DA BASE DE CONHECIMENTO:\n"
            for i, resultado in enumerate(resultados, 1):
                # VectorStore retorna dict com 'text', não objeto com 'page_content'
                texto = resultado.get('text', '') if isinstance(resultado, dict) else str(resultado)
                contexto_rag += f"\n{i}. {texto[:300]}...\n"

            return contexto_rag

        except Exception as e:
            logger.warning(f"Erro ao obter contexto RAG: {str(e)}")
            return ""

    def _construir_contexto(self, falha: Dict[str, Any], resultados: List[Dict[str, Any]], rag_contexto: str = "") -> Tuple[str, List[Dict[str, Any]]]:
        """
        Constrói contexto para análise com rastreamento de fontes

        Retorna:
            Tuple[str, List[Dict]]: (contexto, lista de fontes numeradas)
        """
        fontes = []
        numero_fonte = 1

        contexto = f"""
FALHA DE MERCADO: {falha['titulo']}

PILAR: {falha['pilar']}

DESCRIÇÃO: {falha['descricao']}

ORIENTAÇÕES DE PESQUISA: {falha['dica_busca']}

TOTAL DE POLÍTICAS/ESTUDOS ENCONTRADOS: {len(resultados)}

EXEMPLOS DE POLÍTICAS RELACIONADAS:
"""
        # Incluir top 5 resultados como exemplo com numeração de fontes
        for resultado in resultados[:5]:
            fonte_info = {
                'numero': numero_fonte,
                'tipo': 'pesquisa',
                'id': resultado.get('id'),
                'titulo': resultado['titulo'],
                'descricao': resultado.get('descricao', ''),
                'url': resultado.get('url'),
                'conteudo': resultado.get('conteudo', resultado.get('descricao', ''))
            }
            fontes.append(fonte_info)

            contexto += f"\n[FONTE-{numero_fonte}] {resultado['titulo']}\n"
            if resultado.get('descricao'):
                contexto += f"  {resultado['descricao'][:200]}...\n"
            numero_fonte += 1

        # Incluir contexto RAG se disponível
        if rag_contexto:
            contexto += "\nCONTEXTO DA BASE DE CONHECIMENTO (DOCUMENTOS):\n"
            # Parse RAG context que já tem numeração (vem de _obter_contexto_rag)
            contexto += rag_contexto

        return contexto, fontes

    async def _consultar_ia(
        self,
        contexto: str,
        falha: Dict[str, Any],
        fontes: List[Dict[str, Any]] = None,
        temperatura: float = 0.3,
        max_tokens: int = 4000,
        modelo: str = "google/gemini-2.5-pro"
    ) -> str:
        """Consulta IA para análise com fallback inteligente e rastreamento de fontes"""
        from app.agente.criterios_calibragem import get_prompt_calibrado
        from app.config import settings
        import aiohttp

        # Usar prompt calibrado com critérios objetivos
        prompt = get_prompt_calibrado(contexto)

        try:
            # Usar Gemini 2.0 Flash via OpenRouter
            # 1M tokens de contexto + raciocínio avançado
            headers = {
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://sebrae-politicas.app",
                "X-Title": "Sebrae Priorization Agent",
                "Content-Type": "application/json",
            }

            data = {
                "model": modelo,
                "messages": [
                    {
                        "role": "system",
                        "content": "Você é um especialista em políticas públicas e ecossistema de inovação brasileiro. Responda SEMPRE em formato JSON válido, sem markdown ou texto adicional."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": temperatura,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"}
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120)  # 2 minutos timeout
                ) as resp:
                    if resp.status == 200:
                        resultado = await resp.json()
                        if resultado.get("choices") and len(resultado["choices"]) > 0:
                            resposta = resultado["choices"][0]["message"]["content"]
                            logger.info(f"✓ Análise completada com modelo: {modelo}")
                            return resposta
                        else:
                            raise Exception("Resposta vazia do modelo")
                    else:
                        texto_erro = await resp.text()
                        raise Exception(f"HTTP {resp.status}: {texto_erro[:200]}")

        except Exception as e:
            logger.error(f"✗ Erro na análise com modelo {modelo}: {str(e)[:100]}")
            # Retornar valores padrão em caso de erro
            return json.dumps({
                "impacto": {
                    "abrangencia": 1,
                    "magnitude": 1,
                    "maturidade": 1,
                    "multiplicador": 1,
                    "total": 4
                },
                "esforco": {
                    "stakeholders": 1,
                    "investimento": 1,
                    "tempo": 1,
                    "estrutural": 1,
                    "total": 4
                },
                "justificativa": f"Erro na análise: {str(e)[:50]}",
                "fontes_utilizadas": []
            })

    def _extrair_scores(self, resposta_ia: str) -> Dict[str, int]:
        """Extrai scores de impacto e esforço da resposta da IA"""
        try:
            # Limpar markdown (```json ... ```) se existir
            resposta_limpa = resposta_ia.strip()
            if resposta_limpa.startswith('```'):
                # Remover markdown code blocks
                resposta_limpa = resposta_limpa.split('```')[1]
                if resposta_limpa.startswith('json'):
                    resposta_limpa = resposta_limpa[4:]
                resposta_limpa = resposta_limpa.strip()

            # Tentar parsear como JSON
            dados = json.loads(resposta_limpa)

            # Novo formato com dimensões detalhadas
            if isinstance(dados.get('impacto'), dict):
                impacto = int(dados['impacto'].get('total', 5))
            else:
                # Formato antigo (retrocompatibilidade)
                impacto = int(dados.get('impacto', 5))

            if isinstance(dados.get('esforco'), dict) or isinstance(dados.get('esforço'), dict):
                esforco_dict = dados.get('esforco') or dados.get('esforço')
                esforco = int(esforco_dict.get('total', 5))
            else:
                # Formato antigo (retrocompatibilidade)
                esforco = int(dados.get('esforço', 5)) or int(dados.get('esforco', 5))

            # Validar ranges
            impacto = max(0, min(10, impacto))
            esforco = max(0, min(10, esforco))

            logger.info(f"Scores extraídos - Impacto: {impacto}, Esforço: {esforco}")

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

    def _extrair_fontes_resposta(self, resposta_ia: str, fontes_disponiveis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extrai as fontes citadas pela IA na resposta

        Retorna:
            Lista de fontes que foram utilizadas pela IA
        """
        try:
            # Tentar parsear como JSON
            dados = json.loads(resposta_ia)
            fontes_utilizadas_numeros = dados.get('fontes_utilizadas', [])

            if not fontes_utilizadas_numeros:
                # Se não houver fontes explícitas, tentar extrair da justificativa
                justificativa = dados.get('justificativa', '')
                fontes_utilizadas_numeros = self._extrair_numeros_fonte_texto(justificativa)

            # Mapear números para objetos de fonte
            fontes_mapeadas = []
            for numero in fontes_utilizadas_numeros:
                for fonte in fontes_disponiveis:
                    if fonte['numero'] == numero:
                        fontes_mapeadas.append(fonte)
                        break

            return fontes_mapeadas

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"Erro ao extrair fontes: {str(e)}")
            # Retornar lista vazia se houver erro
            return []

    def _extrair_numeros_fonte_texto(self, texto: str) -> List[int]:
        """
        Extrai números de fontes citadas no formato [FONTE-X] do texto

        Retorna:
            Lista de números de fontes encontrados
        """
        try:
            # Procurar por padrão [FONTE-X] ou [FONTE-0-9]
            pattern = r'\[FONTE-(\d+)\]'
            matches = re.findall(pattern, texto)
            # Converter para int e remover duplicatas
            return sorted(list(set(int(m) for m in matches)))
        except Exception as e:
            logger.warning(f"Erro ao extrair números de fonte do texto: {str(e)}")
            return []

    async def analisar_todas_falhas(
        self,
        usar_rag: bool = True,
        usar_resultados_pesquisa: bool = True,
        temperatura: float = 0.3,
        max_tokens: int = 4000,
        modelo: str = "google/gemini-2.5-pro"
    ) -> Dict[str, Any]:
        """
        Analisa todas as falhas sequencialmente com configurações customizadas

        Args:
            usar_rag: Se True, usa contexto da base de conhecimento RAG
            usar_resultados_pesquisa: Se True, usa resultados de pesquisa
            temperatura: Temperatura do modelo (0.0-1.0)
            max_tokens: Máximo de tokens na resposta
            modelo: Modelo de IA a ser usado

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

        logger.info(f"Iniciando análise de {total} falhas com configurações customizadas...")
        logger.info(f"RAG={usar_rag}, Pesquisa={usar_resultados_pesquisa}, Modelo={modelo}")

        for idx, falha in enumerate(falhas, 1):
            resultado = await self.analisar_falha(
                falha['id'],
                usar_rag=usar_rag,
                usar_resultados_pesquisa=usar_resultados_pesquisa,
                temperatura=temperatura,
                max_tokens=max_tokens,
                modelo=modelo
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
