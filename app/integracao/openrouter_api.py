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

    # Modelos gratuitos da OpenRouter ordenados por preferência
    # Prioridade: modelos rápidos e confiáveis com rate limits generosos
    MODELOS_GRATUITOS = [
        "mistralai/mistral-7b-instruct",  # Bom custo-benefício
        "microsoft/phi-3-mini",  # Muito rápido
        "openchat/openchat-3.5",  # Bom para tarefas simples
        "gpt-3.5-turbo",  # Fallback mais confiável (rate limit generoso)
    ]

    # Modelos especializados para tarefas específicas
    MODELOS_ESPECIALIZADOS = {
        "avaliacao": "xai/grok-4-fast",  # Avaliação de qualidade (rápido e preciso)
        "traducao": "mistralai/mistral-7b-instruct",  # Tradução
        "deteccao_idioma": "xai/grok-4-fast",  # Detecção de idioma (muito preciso)
    }

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
