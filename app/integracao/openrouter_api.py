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
