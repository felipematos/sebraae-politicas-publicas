# -*- coding: utf-8 -*-
"""
Cliente OpenRouter para tradução de queries
Utiliza modelos gratuitos com fallback automático
"""
import asyncio
import aiohttp
from typing import Optional
from app.config import settings


class OpenRouterClient:
    """Cliente para OpenRouter com suporte a tradução via LLM gratuito"""

    # Modelos gratuitos da OpenRouter ordenados por preferência (testados e funcionais)
    # Prioridade: modelos rápidos e confiáveis com rate limits generosos
    MODELOS_GRATUITOS = [
        "meta-llama/llama-3.1-70b-instruct:free",  # Llama 3.1 70B - alta qualidade
        "google/gemma-2-27b-it:free",  # Gemma 2 27B - Google, muito bom
        "mistralai/mixtral-8x7b-instruct:free",  # Mixtral 8x7B - Mistral AI
        "qwen/qwen-2-72b-instruct:free",  # Qwen 2 72B - rápido e eficiente
    ]

    # Modelos especializados para tarefas específicas
    MODELOS_ESPECIALIZADOS = {
        "avaliacao": "xai/grok-4-fast",  # Avaliação de qualidade (rápido e preciso)
        "traducao": "meta-llama/llama-3.1-70b-instruct:free",  # Llama 3.1 70B - excelente para tradução
        "deteccao_idioma": "xai/grok-4-fast",  # Detecção de idioma (muito preciso)
    }

    # Modelos para avaliação profunda (em ordem de prioridade)
    # Usado quando usuário solicita análise mais detalhada
    MODELOS_AVALIACAO_PROFUNDA = [
        # Tier 1: Modelos premium (mais caros, melhor qualidade)
        {
            "nome": "xai/grok-4",
            "descricao": "Grok 4 - Análise profunda de alta qualidade",
            "custo_por_1k_tokens": 0.015,  # Estimativa
            "qualidade": "premium",
            "velocidade": "média"
        },
        {
            "nome": "openai/gpt-4",
            "descricao": "GPT-4 - Análise robusta e confiável",
            "custo_por_1k_tokens": 0.03,
            "qualidade": "premium",
            "velocidade": "média"
        },
        # Tier 2: Modelos balanceados (bom custo-benefício)
        {
            "nome": "xai/grok-4-fast",
            "descricao": "Grok 4 Fast - Rápido com boa qualidade",
            "custo_por_1k_tokens": 0.005,
            "qualidade": "alta",
            "velocidade": "rápida"
        },
        {
            "nome": "anthropic/claude-3-sonnet",
            "descricao": "Claude 3 Sonnet - Análise balanceada",
            "custo_por_1k_tokens": 0.008,
            "qualidade": "alta",
            "velocidade": "média"
        },
        # Tier 3: Modelos gratuitos de alta qualidade (com rate limit)
        {
            "nome": "mistralai/mixtral-8x7b-instruct:free",
            "descricao": "Mixtral 8x7B - Gratuito, alta capacidade",
            "custo_por_1k_tokens": 0.0,
            "qualidade": "boa",
            "velocidade": "média"
        },
        {
            "nome": "google/gemma-2-27b-it:free",
            "descricao": "Gemma 2 27B - Gratuito, Google",
            "custo_por_1k_tokens": 0.0,
            "qualidade": "boa",
            "velocidade": "média"
        },
        {
            "nome": "meta-llama/llama-3.1-70b-instruct:free",
            "descricao": "Llama 3.1 70B - Gratuito, Meta",
            "custo_por_1k_tokens": 0.0,
            "qualidade": "boa",
            "velocidade": "lenta"
        },
        {
            "nome": "qwen/qwen-2-72b-instruct:free",
            "descricao": "Qwen 2 72B - Gratuito, Alibaba",
            "custo_por_1k_tokens": 0.0,
            "qualidade": "boa",
            "velocidade": "média"
        }
    ]

    BASE_URL = "https://openrouter.io/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa cliente OpenRouter

        Args:
            api_key: Chave da API (usa settings.OPENROUTER_API_KEY se não fornecido)
        """
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        self.modelo_atual = 0  # Índice do modelo atual para fallback

    async def __aenter__(self):
        """Context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()

    async def detectar_idioma(
        self,
        texto: str
    ) -> str:
        """
        Detecta o idioma real do texto usando Grok-4-fast

        Args:
            texto: Texto para detectar idioma

        Returns:
            Código do idioma (pt, en, es, it, etc) ou 'unknown'
        """
        if not self.api_key:
            return "unknown"

        if not texto or len(texto.strip()) < 10:
            return "unknown"

        prompt = f"""Detect the language of the following text and return ONLY the ISO 639-1 language code (like 'pt', 'en', 'es', 'it', 'fr', 'de', 'ar', 'ja', 'ko', 'he', etc).

Text to analyze:
{texto[:500]}"""

        try:
            modelo = self.MODELOS_ESPECIALIZADOS.get("deteccao_idioma", "xai/grok-4-fast")
            resultado = await self._chamar_modelo(modelo, prompt)
            if resultado:
                # Extrair código de idioma (geralmente 2 letras)
                codigo = resultado.strip().lower()[:2]
                if codigo in [
                    "pt", "en", "es", "fr", "de", "it", "ar", "ja", "ko", "he"
                ]:
                    return codigo
            return "unknown"
        except Exception as e:
            print(f"[WARN] Detecção de idioma falhou: {str(e)[:100]}")
            return "unknown"

    async def avaliar_qualidade_resultado(
        self,
        titulo: str,
        descricao: str,
        url: str,
        idioma_esperado: str
    ) -> dict:
        """
        Avalia a qualidade de um resultado usando Grok-4-fast

        Args:
            titulo: Título do resultado
            descricao: Descrição do resultado
            url: URL do resultado
            idioma_esperado: Idioma esperado

        Returns:
            Dict com scores e recomendações
        """
        if not self.api_key:
            return {
                "score": 0.5,
                "idioma_correto": None,
                "recomendacao": "MANTER",  # Sem API, manter resultado
                "motivo": "API key não disponível"
            }

        prompt = f"""Evaluate the quality of this research result:

Title: {titulo[:200]}
Description: {descricao[:500] if descricao else 'N/A'}
URL: {url}
Expected Language: {idioma_esperado}

Respond in JSON format (no markdown):
{{
  "idioma_real": "<pt|en|es|it|fr|de|ar|ja|ko|he|unknown>",
  "idioma_correto": <true/false if matches expected>,
  "relevancia_score": <0.0-1.0>,
  "qualidade_score": <0.0-1.0>,
  "recomendacao": "<MANTER|DELETAR>",
  "motivo": "<brief reason>"
}}"""

        try:
            modelo = self.MODELOS_ESPECIALIZADOS.get("avaliacao", "xai/grok-4-fast")
            resultado = await self._chamar_modelo(modelo, prompt)
            if resultado:
                # Parser JSON simples
                import json
                try:
                    dados = json.loads(resultado)
                    return dados
                except:
                    pass

            return {
                "score": 0.5,
                "idioma_correto": None,
                "recomendacao": "REVISAR",
                "motivo": "Falha ao avaliar"
            }
        except Exception as e:
            print(f"[WARN] Avaliação de qualidade falhou: {str(e)[:100]}")
            return {
                "score": 0.5,
                "recomendacao": "REVISAR",
                "motivo": f"Erro: {str(e)[:50]}"
            }

    async def traduzir_texto_com_deteccao(
        self,
        texto: str,
        idioma_alvo: str,
        idioma_origem: str = "pt"
    ) -> dict:
        """
        Traduz texto E detecta o idioma real usando LLM gratuito

        IMPORTANTE: O LLM tem maior confiança na detecção de idioma do que heurísticas,
        então sempre retorna o idioma detectado para atualização no banco.

        Args:
            texto: Texto a traduzir
            idioma_alvo: Código do idioma alvo (en, es, it, ja, etc)
            idioma_origem: Código do idioma origem estimado (padrão: pt)

        Returns:
            Dict com:
                - traducao: str (texto traduzido)
                - idioma_real: str (idioma real detectado pelo LLM)
        """
        if not self.api_key:
            print("[WARN] OPENROUTER_API_KEY não configurada, usando fallback")
            return {"traducao": texto, "idioma_real": idioma_origem}

        # Mapear código de idioma para nome completo
        nomes_idiomas = {
            "pt": "Portuguese",
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "ar": "Arabic",
            "ja": "Japanese",
            "ko": "Korean",
            "he": "Hebrew",
        }

        idioma_alvo_nome = nomes_idiomas.get(idioma_alvo, idioma_alvo)

        prompt = f"""Analyze and translate the following text to {idioma_alvo_nome}.

IMPORTANT INSTRUCTIONS:
1. First, detect the ACTUAL language of the source text (it might be different from what was assumed)
2. Translate to {idioma_alvo_nome}
3. Preserve original capitalization, formatting, and structure
4. Return ONLY in this exact JSON format (no markdown, no explanation):

{{"idioma_real": "<2-letter ISO code like pt, en, es, it, fr, de>", "traducao": "<translated text>"}}

Text to analyze and translate:
{texto}"""

        # Tentar com cada modelo (fallback automático)
        for tentativa, modelo in enumerate(self.MODELOS_GRATUITOS):
            try:
                resultado = await self._chamar_modelo(modelo, prompt)
                if resultado and resultado.strip():
                    # Tentar parsear JSON
                    import json
                    try:
                        # Limpar possíveis marcadores de código
                        resultado_limpo = resultado.strip()
                        if resultado_limpo.startswith("```"):
                            resultado_limpo = resultado_limpo.split("```")[1]
                            if resultado_limpo.startswith("json"):
                                resultado_limpo = resultado_limpo[4:]
                        resultado_limpo = resultado_limpo.strip()

                        dados = json.loads(resultado_limpo)

                        # Validar campos
                        if "traducao" in dados and "idioma_real" in dados:
                            idioma_detectado = dados["idioma_real"].lower()[:2]
                            print(f"[TRADUÇÃO+DETECÇÃO] ✓ Modelo: {modelo} | Idioma detectado: {idioma_detectado}")
                            return {
                                "traducao": dados["traducao"].strip(),
                                "idioma_real": idioma_detectado
                            }
                    except json.JSONDecodeError:
                        # Se falhar o parse, tentar próximo modelo
                        print(f"[TRADUÇÃO+DETECÇÃO] ✗ Falha ao parsear JSON do modelo {modelo}")
                        continue

            except Exception as e:
                print(
                    f"[TRADUÇÃO+DETECÇÃO] ✗ Tentativa {tentativa + 1}/{len(self.MODELOS_GRATUITOS)} "
                    f"com {modelo}: {str(e)[:100]}"
                )
                if tentativa < len(self.MODELOS_GRATUITOS) - 1:
                    await asyncio.sleep(1.0)
                continue

        # Se todas as tentativas falharem, retornar original com idioma estimado
        print(f"[TRADUÇÃO+DETECÇÃO] ✗ Todas as tentativas falharam, retornando texto original")
        return {"traducao": texto, "idioma_real": idioma_origem}

    async def traduzir_texto(
        self,
        texto: str,
        idioma_alvo: str,
        idioma_origem: str = "pt"
    ) -> str:
        """
        Traduz texto para o idioma alvo usando LLM gratuito

        Args:
            texto: Texto a traduzir
            idioma_alvo: Código do idioma alvo (en, es, it, ja, etc)
            idioma_origem: Código do idioma origem (padrão: pt)

        Returns:
            Texto traduzido ou texto original em caso de falha
        """
        if not self.api_key:
            print("[WARN] OPENROUTER_API_KEY não configurada, usando fallback")
            return texto

        if idioma_origem == idioma_alvo:
            return texto

        # Mapear código de idioma para nome completo
        nomes_idiomas = {
            "pt": "Portuguese",
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "ar": "Arabic",
            "ja": "Japanese",
            "ko": "Korean",
            "he": "Hebrew",
        }

        idioma_origem_nome = nomes_idiomas.get(idioma_origem, idioma_origem)
        idioma_alvo_nome = nomes_idiomas.get(idioma_alvo, idioma_alvo)

        prompt = f"""Translate the following {idioma_origem_nome} text to {idioma_alvo_nome}.

IMPORTANT: Preserve the original capitalization, formatting, and structure of the text.
Do NOT change uppercase/lowercase letters unless grammatically required in the target language.
Return ONLY the translated text, without any explanation or additional text.

Text to translate:
{texto}"""

        # Tentar com cada modelo (fallback automático)
        for tentativa, modelo in enumerate(self.MODELOS_GRATUITOS):
            try:
                resultado = await self._chamar_modelo(modelo, prompt)
                if resultado and resultado.strip():
                    print(f"[TRADUÇÃO] ✓ Modelo: {modelo}")
                    return resultado.strip()
            except Exception as e:
                print(
                    f"[TRADUÇÃO] ✗ Tentativa {tentativa + 1}/{len(self.MODELOS_GRATUITOS)} "
                    f"com {modelo}: {str(e)[:100]}"
                )
                if tentativa < len(self.MODELOS_GRATUITOS) - 1:
                    # Aguardar um pouco antes de tentar próximo modelo
                    await asyncio.sleep(1.0)
                continue

        # Se todas as tentativas falharem, retornar original
        print(f"[TRADUÇÃO] ✗ Todas as tentativas falharam, retornando texto original")
        return texto

    async def analisar_fonte(
        self,
        titulo: str,
        descricao: str,
        url: str = None,
        titulo_pt: str = None,
        descricao_pt: str = None,
        idioma: str = None
    ) -> dict:
        """
        Analisa uma fonte para determinar tipo, se tem implementação e métricas

        IMPORTANTE: Para garantir acurácia multilíngue, esta função:
        1. Usa prompt em inglês (idioma universal para LLMs)
        2. Prioriza traduções para português quando disponíveis
        3. Fornece contexto de idioma para o LLM

        Args:
            titulo: Título da fonte (idioma original)
            descricao: Descrição/resumo da fonte (idioma original)
            url: URL da fonte (opcional)
            titulo_pt: Tradução do título para português (opcional)
            descricao_pt: Tradução da descrição para português (opcional)
            idioma: Código do idioma da fonte (opcional, ex: 'en', 'es', 'pt')

        Returns:
            dict com:
                - tipo_fonte: str (academica, governamental, tecnico, caso_sucesso)
                - tem_implementacao: bool
                - tem_metricas: bool
                - confianca: float (0.0-1.0)
        """
        if not self.api_key:
            return {
                "tipo_fonte": "desconhecido",
                "tem_implementacao": False,
                "tem_metricas": False,
                "confianca": 0.0
            }

        # MELHORIA: Tradução automática quando necessário
        # Se o idioma não é português e não há tradução disponível, traduzir automaticamente
        if idioma and idioma != 'pt':
            # Traduzir título se não houver tradução
            if not titulo_pt and titulo:
                print(f"[TRADUÇÃO] Traduzindo título de {idioma} para pt...")
                titulo_pt = await self._traduzir_texto(titulo, idioma)

            # Traduzir descrição se não houver tradução
            if not descricao_pt and descricao:
                print(f"[TRADUÇÃO] Traduzindo descrição de {idioma} para pt...")
                descricao_pt = await self._traduzir_texto(descricao, idioma)

        # Priorizar traduções para português quando disponíveis
        # Isso garante acurácia consistente independente do idioma original
        titulo_para_analise = titulo_pt if titulo_pt else titulo
        descricao_para_analise = descricao_pt if descricao_pt else descricao

        # Truncar texto para não exceder limites
        titulo_trunc = (titulo_para_analise or '')[:200]
        descricao_trunc = (descricao_para_analise or '')[:800]
        url_info = f"\nURL: {url}" if url else ""

        # Adicionar informação de idioma se disponível
        idioma_info = ""
        if idioma:
            idioma_map = {
                "pt": "Portuguese", "en": "English", "es": "Spanish",
                "fr": "French", "de": "German", "it": "Italian",
                "ja": "Japanese", "ar": "Arabic", "ko": "Korean", "he": "Hebrew"
            }
            idioma_nome = idioma_map.get(idioma, idioma)
            idioma_info = f"\nOriginal Language: {idioma_nome}"

        # Se há tradução, indicar isso no prompt
        traducao_info = ""
        if titulo_pt or descricao_pt:
            traducao_info = "\n(Text has been translated to Portuguese for analysis)"

        # Prompt em inglês para melhor acurácia multilíngue
        prompt = f"""Analyze the following document and classify it according to the criteria below.
Return ONLY a valid JSON object, without additional explanations.

Document:
Title: {titulo_trunc}
Description: {descricao_trunc}{url_info}{idioma_info}{traducao_info}

Classification Criteria:

1. tipo_fonte (choose ONLY ONE option):
   - "academica": Scientific articles, academic research, university studies
   - "governamental": Laws, decrees, government programs, official public policies
   - "tecnico": Technical reports, white papers, market studies, analyses
   - "caso_sucesso": Success cases, successful implementation stories

2. tem_implementacao (true/false):
   - true: If it describes practical implementation cases, real experiences, concrete examples
   - false: If it is only theoretical, conceptual, or propositional

3. tem_metricas (true/false):
   - true: If it presents quantifiable data, impact metrics, numbers, measurable results
   - false: If it does not have quantitative data

4. confianca (0.0 to 1.0):
   - Your confidence level in the classification (0.0 = uncertain, 1.0 = very confident)

Response Format (JSON only):
{{
  "tipo_fonte": "academica|governamental|tecnico|caso_sucesso",
  "tem_implementacao": true|false,
  "tem_metricas": true|false,
  "confianca": 0.0-1.0
}}"""

        try:
            modelo = self.MODELOS_ESPECIALIZADOS.get("avaliacao", "xai/grok-4-fast")
            resultado = await self._chamar_modelo(modelo, prompt)

            if resultado:
                # Tentar parsear JSON
                import json
                # Remover possíveis marcadores de código
                resultado_limpo = resultado.strip()
                if resultado_limpo.startswith("```"):
                    resultado_limpo = resultado_limpo.split("```")[1]
                    if resultado_limpo.startswith("json"):
                        resultado_limpo = resultado_limpo[4:]
                resultado_limpo = resultado_limpo.strip()

                analise = json.loads(resultado_limpo)

                # Validar campos
                tipo_valido = analise.get("tipo_fonte") in [
                    "academica", "governamental", "tecnico", "caso_sucesso"
                ]

                if tipo_valido:
                    return {
                        "tipo_fonte": analise.get("tipo_fonte", "desconhecido"),
                        "tem_implementacao": bool(analise.get("tem_implementacao", False)),
                        "tem_metricas": bool(analise.get("tem_metricas", False)),
                        "confianca": float(analise.get("confianca", 0.5))
                    }

        except Exception as e:
            print(f"[ANÁLISE] ✗ Erro ao analisar fonte: {str(e)[:100]}")

        # Fallback: tentar classificar baseado em palavras-chave
        return self._classificar_heuristico(titulo, descricao, url)

    def _classificar_heuristico(self, titulo: str, descricao: str, url: str = None) -> dict:
        """Classificação heurística multilíngue com score dinâmico

        MELHORIAS IMPLEMENTADAS:
        1. Score dinâmico baseado em contagem de keywords (não apenas boolean)
        2. Boost para múltiplas evidências convergentes
        3. Detecção de domínios autoritativos (.gov, .edu, etc)
        4. Densidade de palavras-chave (TF-IDF simplificado)
        5. Tamanho do texto como fator de relevância

        IMPORTANTE: Usa palavras-chave em TODOS os idiomas suportados (pt, en, es, fr, de, it, ja, ar, ko, he)
        para garantir acurácia consistente independente do idioma do texto.
        """
        texto = f"{titulo or ''} {descricao or ''} {url or ''}".lower()

        # Calcular tamanho do texto (palavras)
        palavras_total = len(texto.split())

        # Keywords organizadas por categoria e idioma
        keywords_governamental = [
            # Português
            "lei", "decreto", "portaria", "gov.br", "planalto", "programa nacional",
            "governo", "ministerio", "ministério", "política pública",
            # English
            "law", "decree", "government program", "national program", "policy",
            "ministry", "public policy", "government",
            # Español
            "ley", "decreto", "programa nacional", "programa gubernamental",
            "gobierno", "ministerio", "política pública",
            # Français
            "loi", "décret", "programme national", "gouvernement",
            "ministère", "politique publique",
            # Deutsch
            "gesetz", "verordnung", "regierung", "ministerium",
            "nationale programm", "öffentliche politik",
            # Italiano
            "legge", "decreto", "governo", "ministero",
            "programma nazionale", "politica pubblica",
            # 日本語 (Japonês - romanizado)
            "hōritsu", "seifu", "kōkyō seisaku",
            # العربية (Árabe - romanizado)
            "qanun", "hukuma", "wizara", "barnamaj watani",
            # 한국어 (Coreano - romanizado)
            "beob", "jeongbu", "gukga peurogeulaem",
            # עברית (Hebraico - romanizado)
            "hok", "memshala", "misrad", "tochnit leumit"
        ]

        keywords_academica = [
            # Português
            "universidade", "pesquisa", "estudo", "paper", "journal", "revista científica",
            "artigo científico", "tese", "dissertação",
            # English
            "university", "research", "study", "scientific", "journal", "article",
            "thesis", "dissertation", "academic",
            # Español
            "universidad", "investigación", "estudio", "revista científica",
            "artículo científico", "tesis",
            # Français
            "université", "recherche", "étude", "revue scientifique",
            "article scientifique", "thèse",
            # Deutsch
            "universität", "forschung", "studie", "wissenschaftlich",
            "zeitschrift", "dissertation",
            # Italiano
            "università", "ricerca", "studio", "rivista scientifica",
            "articolo scientifico", "tesi",
            # 日本語 (Japonês - romanizado)
            "daigaku", "kenkyū", "ronbun", "gakujutsu",
            # العربية (Árabe - romanizado)
            "jami'a", "bahth", "majalat ilmiya",
            # 한국어 (Coreano - romanizado)
            "daehak", "yeongu", "nonmun", "haksul",
            # עברית (Hebraico - romanizado)
            "universita", "mehkar", "ma'amar", "akademi"
        ]

        keywords_caso_sucesso = [
            # Português
            "caso", "sucesso", "exemplo", "implementação bem-sucedida", "história de",
            # English
            "success case", "success story", "successful implementation", "case study",
            # Español
            "caso de éxito", "historia de", "implementación exitosa",
            # Français
            "cas de succès", "histoire de", "mise en œuvre réussie",
            # Deutsch
            "erfolgsfall", "erfolgsgeschichte", "erfolgreiche umsetzung",
            # Italiano
            "caso di successo", "storia di successo", "implementazione riuscita",
            # 日本語 (Japonês - romanizado)
            "seikō jirei", "jisshi jirei",
            # العربية (Árabe - romanizado)
            "halat najah", "qissat najah",
            # 한국어 (Coreano - romanizado)
            "seong-gong sa-rye",
            # עברית (Hebraico - romanizado)
            "sippur hatzlacha", "mikreh matzliach"
        ]

        keywords_implementacao = [
            # Português
            "implementou", "implementado", "implementação", "aplicou", "executou",
            "caso prático", "experiência", "projeto piloto", "iniciativa",
            "resultou", "resultando", "apoiou", "criação de", "criou",
            # English
            "implemented", "implementation", "applied", "executed", "supported",
            "resulted", "resulting", "creation of", "created", "pilot project",
            # Español
            "implementó", "implementado", "implementación", "aplicó", "ejecutó",
            "apoyó", "resultó", "creación de", "creó", "proyecto piloto",
            # Français
            "mis en œuvre", "implémenté", "appliqué", "exécuté",
            "projet pilote", "initiative", "résulté",
            # Deutsch
            "implementiert", "umgesetzt", "angewendet", "pilotprojekt",
            "initiative", "resultierte",
            # Italiano
            "implementato", "applicato", "eseguito", "progetto pilota",
            "iniziativa", "risultato",
            # 日本語 (Japonês - romanizado)
            "jisshi", "tekiyo", "pairotto", "kekka",
            # العربية (Árabe - romanizado)
            "tanfidh", "tatbiq", "mashru' tajarubi", "natija",
            # 한국어 (Coreano - romanizado)
            "silhaeng", "jeog-yong", "pailleot", "gyeolgwa",
            # עברית (Hebraico - romanizado)
            "miyum", "hechel", "pilo't", "totsa'a"
        ]

        keywords_metricas = [
            # Símbolos e números universais
            "%", "r$", "$", "€", "¥", "£",
            # Português
            "percentual", "milhão", "milhões", "bilhão", "bilhões",
            "crescimento", "aumento", "redução", "impacto mensurável",
            "dados", "estatísticas", "resultados quantificáveis", "indicadores",
            "empregos", "faturamento", "investimento",
            # English
            "percent", "million", "billion", "growth", "increase", "reduction",
            "measurable impact", "data", "statistics", "quantifiable results",
            "indicators", "jobs", "revenue", "investment",
            # Español
            "millones", "millón", "crecimiento", "aumento", "reducción",
            "impacto mensurable", "datos", "estadísticas",
            "resultados cuantificables", "indicadores", "empleos", "ingresos",
            # Français
            "pour cent", "millions", "croissance", "augmentation", "réduction",
            "impact mesurable", "données", "statistiques", "indicateurs",
            "emplois", "revenus", "investissement",
            # Deutsch
            "prozent", "millionen", "wachstum", "zunahme", "reduzierung",
            "messbare auswirkung", "daten", "statistiken", "indikatoren",
            # Italiano
            "per cento", "milioni", "crescita", "aumento", "riduzione",
            "impatto misurabile", "dati", "statistiche", "indicatori",
            # 日本語 (Japonês - romanizado)
            "pāsento", "man", "oku", "zōka", "genshō", "dēta", "shihyō",
            # العربية (Árabe - romanizado)
            "bi'l-mi'a", "milyun", "numuwa", "bianat", "mu'ashshirat",
            # 한국어 (Coreano - romanizado)
            "peosenteu", "baeg-man", "seong-jang", "jeungga", "data", "jihyo",
            # עברית (Hebraico - romanizado)
            "achuz", "milyon", "tzmikha", "ne'tanim", "ma'arachim"
        ]

        # MELHORIA #1: Contar matches de keywords (não apenas boolean)
        count_gov = sum(1 for k in keywords_governamental if k in texto)
        count_acad = sum(1 for k in keywords_academica if k in texto)
        count_sucesso = sum(1 for k in keywords_caso_sucesso if k in texto)
        count_impl = sum(1 for k in keywords_implementacao if k in texto)
        count_metricas = sum(1 for k in keywords_metricas if k in texto)

        # Determinar tipo de fonte (maior contagem)
        tipo_fonte = "tecnico"  # padrão
        max_count = max(count_gov, count_acad, count_sucesso)

        if max_count > 0:
            if count_gov == max_count:
                tipo_fonte = "governamental"
            elif count_acad == max_count:
                tipo_fonte = "academica"
            elif count_sucesso == max_count:
                tipo_fonte = "caso_sucesso"

        # Determinar tem_implementacao e tem_metricas
        tem_implementacao = count_impl > 0
        tem_metricas = count_metricas > 0

        # CALCULAR SCORE DE CONFIANÇA (0.0 a 1.0)
        confianca = 0.3  # baseline para heurística

        # MELHORIA #1: Ajustar baseado em número de matches
        # Normalizar por categoria (mais matches = maior confiança)
        tipo_score = min(max_count * 0.05, 0.3)  # até +0.3
        impl_score = min(count_impl * 0.03, 0.15)  # até +0.15
        metricas_score = min(count_metricas * 0.03, 0.15)  # até +0.15

        confianca += tipo_score + impl_score + metricas_score

        # MELHORIA #2: Boost para evidências convergentes
        # Se tem tipo_fonte identificado + implementação + métricas = forte evidência
        categorias_presentes = sum([
            max_count > 0,  # tipo identificado
            tem_implementacao,
            tem_metricas
        ])

        if categorias_presentes == 3:
            confianca += 0.15  # Boost significativo para evidência tripla
        elif categorias_presentes == 2:
            confianca += 0.05  # Boost moderado para evidência dupla

        # MELHORIA #4: Boost para domínios autoritativos
        # Domínios confiáveis dos países com idiomas suportados
        dominios_autoritativos = [
            # Genéricos globais
            '.gov', '.edu', '.org', '.ac',

            # Brasil (pt)
            'gov.br', 'planalto.gov.br', 'bndes.gov.br',
            'sebrae.com.br', 'cnpq.br', 'capes.gov.br',
            'finep.gov.br', 'mctic.gov.br', 'mdic.gov.br',
            'ipea.gov.br', 'ibge.gov.br', '.edu.br',

            # Portugal (pt)
            'gov.pt', 'parlamento.pt', 'presidencia.pt',
            'iapmei.pt', 'ani.pt', 'fct.pt', '.edu.pt',

            # Estados Unidos (en)
            'gov', 'senate.gov', 'house.gov', 'whitehouse.gov',
            'nsf.gov', 'nih.gov', 'sba.gov', 'commerce.gov',
            'mit.edu', 'stanford.edu', 'harvard.edu',

            # Reino Unido (en)
            'gov.uk', 'parliament.uk', 'innovateuk.org',
            'ox.ac.uk', 'cam.ac.uk', '.ac.uk',

            # Espanha (es)
            'gob.es', 'congreso.es', 'boe.es',
            'mineco.gob.es', 'cdti.es', '.edu.es',

            # México (es)
            'gob.mx', 'conacyt.mx', 'economia.gob.mx',
            'inadem.gob.mx', '.edu.mx',

            # Argentina (es)
            'argentina.gob.ar', 'conicet.gov.ar',
            'produccion.gob.ar', '.edu.ar',

            # Chile (es)
            'gob.cl', 'corfo.cl', 'conicyt.cl', '.edu.cl',

            # Colômbia (es)
            'gov.co', 'minciencias.gov.co',
            'innpulsacolombia.com', '.edu.co',

            # França (fr)
            'gouv.fr', 'assemblee-nationale.fr',
            'bpifrance.fr', 'cnrs.fr', '.edu.fr',

            # Alemanha (de)
            'bund.de', 'bundesregierung.de', 'bundestag.de',
            'bmwi.de', 'dlr.de', 'fraunhofer.de', '.edu.de',

            # Itália (it)
            'gov.it', 'governo.it', 'camera.it',
            'mise.gov.it', 'cnr.it', '.edu.it',

            # Japão (ja)
            'go.jp', 'meti.go.jp', 'mext.go.jp',
            'jst.go.jp', 'nedo.go.jp', '.ac.jp',

            # Coreia do Sul (ko)
            'go.kr', 'moef.go.kr', 'msit.go.kr',
            'nrf.re.kr', 'kista.re.kr', '.ac.kr',

            # Israel (he)
            'gov.il', 'knesset.gov.il', 'economy.gov.il',
            'innovationisrael.org.il', '.ac.il',

            # Emirados Árabes (ar)
            'gov.ae', 'u.ae', '.ac.ae',

            # Arábia Saudita (ar)
            'gov.sa', 'kacst.edu.sa', '.edu.sa',

            # Organizações internacionais
            'oecd.org', 'worldbank.org', 'un.org',
            'wipo.int', 'europa.eu', 'ec.europa.eu'
        ]

        if url:
            url_lower = url.lower()
            if any(dom in url_lower for dom in dominios_autoritativos):
                confianca += 0.1  # Boost por domínio autoritativo

        # MELHORIA #7: Densidade de keywords (TF-IDF simplificado)
        if palavras_total > 0:
            total_keywords = count_gov + count_acad + count_sucesso + count_impl + count_metricas
            densidade = total_keywords / palavras_total

            # Normalizar densidade (valores típicos: 0.01 a 0.1)
            densidade_score = min(densidade * 2, 0.1)  # até +0.1
            confianca += densidade_score

        # MELHORIA #5: Tamanho do texto como fator de relevância
        # Textos mais longos tendem a ser mais relevantes (até um cap)
        if palavras_total >= 500:
            confianca += 0.1  # Texto substancial (pesquisa/estudo)
        elif palavras_total >= 200:
            confianca += 0.05  # Texto médio (artigo)
        # Abaixo de 200 palavras = notícia curta, sem boost
        # Cap máximo: acima de 500 palavras não aumenta mais

        # Garantir que confiança fique entre 0.0 e 1.0
        confianca = min(max(confianca, 0.0), 1.0)

        return {
            "tipo_fonte": tipo_fonte,
            "tem_implementacao": tem_implementacao,
            "tem_metricas": tem_metricas,
            "confianca": round(confianca, 2)
        }

    async def _traduzir_texto(self, texto: str, idioma_origem: str) -> str:
        """Traduz texto para português usando LLM

        Args:
            texto: Texto a ser traduzido
            idioma_origem: Código do idioma de origem (en, es, fr, etc.)

        Returns:
            Texto traduzido para português
        """
        if not texto or not texto.strip():
            return ""

        # Mapear idioma para nome legível
        idioma_map = {
            "en": "English", "es": "Spanish", "fr": "French",
            "de": "German", "it": "Italian", "ja": "Japanese",
            "ar": "Arabic", "ko": "Korean", "he": "Hebrew"
        }
        idioma_nome = idioma_map.get(idioma_origem, idioma_origem)

        # Prompt de tradução simples e direto
        prompt = f"""Translate the following text from {idioma_nome} to Portuguese (Brazilian).

IMPORTANT: Preserve the original capitalization, formatting, and structure of the text.
Return ONLY the translated text, without any additional explanations or comments.

Text to translate:
{texto[:1000]}"""  # Limitar tamanho

        try:
            # Usar modelo rápido e barato para tradução
            modelo = "meta-llama/llama-3.2-3b-instruct:free"
            traducao = await self._chamar_modelo(modelo, prompt)
            return traducao.strip()
        except Exception as e:
            print(f"[TRADUÇÃO] ✗ Erro ao traduzir de {idioma_origem}: {str(e)[:100]}")
            # Em caso de erro, retornar texto original
            return texto

    def selecionar_modelos_avaliacao(
        self,
        modo: str = "gratuito",
        max_modelos: int = 3
    ) -> list:
        """Seleciona modelos para avaliação profunda baseado no modo escolhido

        Args:
            modo: "premium", "balanceado" ou "gratuito"
            max_modelos: Número máximo de modelos a retornar

        Returns:
            Lista de modelos selecionados
        """
        if modo == "premium":
            # Usar apenas modelos premium (pagos de alta qualidade)
            modelos = [m for m in self.MODELOS_AVALIACAO_PROFUNDA
                      if m["qualidade"] == "premium"]
        elif modo == "balanceado":
            # Usar modelos premium + alta qualidade
            modelos = [m for m in self.MODELOS_AVALIACAO_PROFUNDA
                      if m["qualidade"] in ["premium", "alta"]]
        else:  # gratuito
            # Usar apenas modelos gratuitos
            modelos = [m for m in self.MODELOS_AVALIACAO_PROFUNDA
                      if m["custo_por_1k_tokens"] == 0.0]

        return modelos[:max_modelos]

    def estimar_custo_tempo_avaliacao(
        self,
        num_fontes: int,
        modo: str = "gratuito"
    ) -> dict:
        """Estima custo e tempo para avaliação profunda

        Args:
            num_fontes: Número de fontes a analisar
            modo: Modo de avaliação ("premium", "balanceado", "gratuito")

        Returns:
            Dict com estimativas de custo e tempo
        """
        modelos = self.selecionar_modelos_avaliacao(modo, max_modelos=1)

        if not modelos:
            return {
                "custo_estimado": 0.0,
                "tempo_estimado_segundos": num_fontes * 3,
                "modo": modo,
                "modelo": "heurístico"
            }

        modelo = modelos[0]

        # Estimativas (baseado em experiência)
        tokens_por_fonte = 1200  # Prompt + resposta
        tempo_por_fonte = 5 if modelo["velocidade"] == "rápida" else 8 if modelo["velocidade"] == "média" else 12

        custo_total = (num_fontes * tokens_por_fonte / 1000) * modelo["custo_por_1k_tokens"]
        tempo_total = num_fontes * tempo_por_fonte

        return {
            "custo_estimado": round(custo_total, 3),
            "tempo_estimado_segundos": tempo_total,
            "modo": modo,
            "modelo": modelo["descricao"]
        }

    async def analisar_fonte_profunda(
        self,
        titulo: str,
        descricao: str,
        url: str = None,
        titulo_pt: str = None,
        descricao_pt: str = None,
        idioma: str = None,
        modo: str = "gratuito"
    ) -> dict:
        """Avaliação profunda usando LLMs de alta qualidade com fallback automático

        Args:
            titulo: Título da fonte
            descricao: Descrição da fonte
            url: URL da fonte (opcional)
            titulo_pt: Tradução do título (opcional)
            descricao_pt: Tradução da descrição (opcional)
            idioma: Código do idioma (opcional)
            modo: "premium", "balanceado" ou "gratuito"

        Returns:
            Dict com análise profunda e maior confiança
        """
        # Traduzir se necessário (mesma lógica do método regular)
        if idioma and idioma != 'pt':
            if not titulo_pt and titulo:
                titulo_pt = await self._traduzir_texto(titulo, idioma)
            if not descricao_pt and descricao:
                descricao_pt = await self._traduzir_texto(descricao, idioma)

        titulo_analise = titulo_pt if titulo_pt else titulo
        descricao_analise = descricao_pt if descricao_pt else descricao

        # Selecionar modelos para tentar
        modelos = self.selecionar_modelos_avaliacao(modo, max_modelos=3)

        if not modelos:
            # Fallback para análise heurística
            print("[AVALIAÇÃO PROFUNDA] Nenhum modelo disponível, usando heurística")
            return self._classificar_heuristico(titulo_analise, descricao_analise, url)

        # Prompt mais detalhado para avaliação profunda
        prompt = f"""You are an expert analyst evaluating innovation ecosystem documents.

Analyze this document in depth and provide a detailed classification.

Document:
Title: {titulo_analise[:300]}
Description: {descricao_analise[:1500]}
URL: {url or 'N/A'}

Provide a thorough analysis considering:
1. Document type and source credibility
2. Presence of concrete implementation cases
3. Availability of quantifiable metrics and data
4. Overall quality and relevance

Return ONLY a JSON object with:
{{
  "tipo_fonte": "academica|governamental|tecnico|caso_sucesso",
  "tem_implementacao": true|false,
  "tem_metricas": true|false,
  "confianca": 0.0-1.0,
  "justificativa": "Brief explanation of classification (max 200 chars)"
}}"""

        # Tentar cada modelo com fallback automático
        for i, modelo_info in enumerate(modelos):
            modelo_nome = modelo_info["nome"]
            try:
                print(f"[AVALIAÇÃO PROFUNDA] Tentando modelo {i+1}/{len(modelos)}: {modelo_info['descricao']}")
                resultado = await self._chamar_modelo(modelo_nome, prompt)

                if resultado:
                    import json
                    # Remover marcadores de código
                    resultado_limpo = resultado.strip()
                    if resultado_limpo.startswith("```"):
                        resultado_limpo = resultado_limpo.split("```")[1]
                        if resultado_limpo.startswith("json"):
                            resultado_limpo = resultado_limpo[4:]
                    resultado_limpo = resultado_limpo.strip()

                    analise = json.loads(resultado_limpo)

                    # Validar e retornar
                    if analise.get("tipo_fonte") in ["academica", "governamental", "tecnico", "caso_sucesso"]:
                        print(f"[AVALIAÇÃO PROFUNDA] ✓ Análise concluída com {modelo_info['descricao']}")
                        return {
                            "tipo_fonte": analise.get("tipo_fonte", "tecnico"),
                            "tem_implementacao": bool(analise.get("tem_implementacao", False)),
                            "tem_metricas": bool(analise.get("tem_metricas", False)),
                            "confianca": float(analise.get("confianca", 0.7)),
                            "justificativa": analise.get("justificativa", ""),
                            "modelo_usado": modelo_info["descricao"]
                        }

            except Exception as e:
                print(f"[AVALIAÇÃO PROFUNDA] ✗ Erro com {modelo_nome}: {str(e)[:100]}")
                # Continuar para próximo modelo
                if i < len(modelos) - 1:
                    print(f"[AVALIAÇÃO PROFUNDA] Tentando próximo modelo...")
                    await asyncio.sleep(1)  # Pequena pausa antes do fallback
                continue

        # Se todos os modelos falharam, usar heurística
        print("[AVALIAÇÃO PROFUNDA] Todos os modelos falharam, usando heurística")
        resultado_heuristico = self._classificar_heuristico(titulo_analise, descricao_analise, url)
        resultado_heuristico["modelo_usado"] = "Heurística (fallback)"
        return resultado_heuristico

    async def _chamar_modelo(self, modelo: str, prompt: str) -> str:
        """
        Chama um modelo específico da OpenRouter

        Args:
            modelo: Nome do modelo
            prompt: Prompt para o modelo

        Returns:
            Resposta do modelo
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://sebrae-politicas.app",
            "X-Title": "Sebrae Research Agent",
            "Content-Type": "application/json",
        }

        data = {
            "model": modelo,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,  # Baixa temperatura para traduções consistentes
            "max_tokens": 500,
            "timeout": 30,
        }

        async with self.session.post(
            f"{self.BASE_URL}/chat/completions",
            json=data,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=45),
        ) as resp:
            if resp.status == 200:
                resultado = await resp.json()
                if resultado.get("choices") and len(resultado["choices"]) > 0:
                    return resultado["choices"][0]["message"]["content"]
                raise Exception("Resposta vazia do modelo")
            elif resp.status == 429:
                raise Exception(f"Rate limit atingido (429)")
            else:
                texto_erro = await resp.text()
                raise Exception(f"HTTP {resp.status}: {texto_erro[:200]}")


# Cliente global para reutilização
_cliente_openrouter: Optional[OpenRouterClient] = None


async def get_openrouter_client() -> OpenRouterClient:
    """
    Retorna instância do cliente OpenRouter (singleton)
    """
    global _cliente_openrouter
    if _cliente_openrouter is None:
        _cliente_openrouter = OpenRouterClient()
    return _cliente_openrouter


async def traduzir_com_openrouter(
    texto: str,
    idioma_alvo: str,
    idioma_origem: str = "pt"
) -> str:
    """
    Função auxiliar para tradução com OpenRouter

    Args:
        texto: Texto a traduzir
        idioma_alvo: Idioma alvo
        idioma_origem: Idioma origem (padrão: português)

    Returns:
        Texto traduzido
    """
    cliente = await get_openrouter_client()
    return await cliente.traduzir_texto(texto, idioma_alvo, idioma_origem)


async def consultar_openrouter(
    prompt: str,
    modelo: Optional[str] = None
) -> str:
    """
    Função auxiliar para consultar OpenRouter com um prompt específico

    Args:
        prompt: Prompt/pergunta para o modelo
        modelo: Nome do modelo a usar (opcional, usa padrão se não especificado)

    Returns:
        Resposta do modelo
    """
    cliente = await get_openrouter_client()

    # Usar modelo especificado ou usar o primeiro modelo gratuito como padrão
    modelo_usar = modelo or cliente.MODELOS_GRATUITOS[0]

    try:
        resposta = await cliente._chamar_modelo(modelo_usar, prompt)
        return resposta
    except Exception as e:
        print(f"[ERRO] Consulta OpenRouter falhou com modelo {modelo_usar}: {str(e)[:100]}")
        # Tentar com modelos alternativos como fallback
        for modelo_alt in cliente.MODELOS_GRATUITOS:
            if modelo_alt != modelo_usar:
                try:
                    print(f"[FALLBACK] Tentando com modelo alternativo: {modelo_alt}")
                    resposta = await cliente._chamar_modelo(modelo_alt, prompt)
                    return resposta
                except Exception as e2:
                    print(f"[FALLBACK FALHOU] {modelo_alt}: {str(e2)[:100]}")
                    continue

        # Se todas as tentativas falharem, lançar exceção original
        raise e
