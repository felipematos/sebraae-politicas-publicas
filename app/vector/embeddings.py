# -*- coding: utf-8 -*-
"""
Cliente de embeddings para gerar vetores de texto
Suporta OpenAI e Jina AI
"""
import asyncio
from typing import List, Optional
from openai import AsyncOpenAI
import httpx

from app.vector.modelos_embedding import (
    get_modelo_info,
    get_dimensoes_modelo,
    get_provider_modelo,
    EmbeddingProvider
)


class EmbeddingClient:
    """Cliente para gerar embeddings usando OpenAI ou Jina AI"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        jina_api_key: Optional[str] = None
    ):
        """
        Inicializa cliente de embeddings

        Args:
            api_key: API key da OpenAI (opcional, usa env var se não fornecido)
            model: Modelo a usar para embeddings
            jina_api_key: API key da Jina AI (opcional, só necessário para modelos Jina)
        """
        self.model = model
        self.cache = {}  # Cache simples para evitar requisições duplicadas

        # Detectar provedor do modelo
        self.provider = get_provider_modelo(model)
        self.model_info = get_modelo_info(model)
        self.dimensoes = get_dimensoes_modelo(model)

        # Inicializar cliente apropriado
        if self.provider == EmbeddingProvider.OPENAI:
            self.client = AsyncOpenAI(api_key=api_key)
            self.jina_client = None
            self.jina_api_key = None
        elif self.provider == EmbeddingProvider.JINA:
            self.client = None
            self.jina_client = httpx.AsyncClient(timeout=60.0)
            self.jina_api_key = jina_api_key
        else:
            raise ValueError(f"Provedor desconhecido: {self.provider}")

    async def embed_text(self, text: str) -> List[float]:
        """
        Gera embedding para um texto

        Args:
            text: Texto para gerar embedding

        Returns:
            Lista de floats representando o embedding (dimensão variável conforme modelo)
        """
        if not text or not text.strip():
            return [0.0] * self.dimensoes

        # Verificar cache
        if text in self.cache:
            return self.cache[text]

        try:
            # Truncar texto se necessário (máx ~8000 tokens)
            max_chars = self.model_info.get("max_tokens", 8191) * 4  # ~4 chars por token
            text_trunc = text[:max_chars] if len(text) > max_chars else text

            # Gerar embedding baseado no provedor
            if self.provider == EmbeddingProvider.OPENAI:
                embedding = await self._embed_openai(text_trunc)
            elif self.provider == EmbeddingProvider.JINA:
                embedding = await self._embed_jina(text_trunc)
            else:
                raise ValueError(f"Provedor não suportado: {self.provider}")

            # Guardar em cache
            self.cache[text] = embedding

            return embedding

        except Exception as e:
            print(f"Erro gerando embedding para '{text[:50]}...': {e}")
            # Retornar embedding zero se falhar
            return [0.0] * self.dimensoes

    async def _embed_openai(self, text: str) -> List[float]:
        """Gera embedding usando OpenAI"""
        response = await self.client.embeddings.create(
            input=text,
            model=self.model
        )
        return response.data[0].embedding

    async def _embed_jina(self, text: str) -> List[float]:
        """Gera embedding usando Jina AI"""
        if not self.jina_api_key:
            raise ValueError("Jina API key não configurada")

        url = "https://api.jina.ai/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.jina_api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "input": [text]
        }

        response = await self.jina_client.post(url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        return result["data"][0]["embedding"]

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 20
    ) -> List[List[float]]:
        """
        Gera embeddings para múltiplos textos em paralelo

        Args:
            texts: Lista de textos
            batch_size: Tamanho do batch para requisições

        Returns:
            Lista de embeddings
        """
        embeddings = []

        # Processar em batches para evitar limites de taxa
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # Gerar em paralelo dentro do batch
            tasks = [self.embed_text(text) for text in batch]
            batch_embeddings = await asyncio.gather(*tasks)

            embeddings.extend(batch_embeddings)

        return embeddings

    def clear_cache(self):
        """Limpa o cache de embeddings"""
        self.cache.clear()

    def get_cache_stats(self) -> dict:
        """Retorna estatísticas do cache"""
        return {
            "cached_texts": len(self.cache),
            "cache_size_mb": sum(len(str(v)) for v in self.cache.values()) / (1024 * 1024)
        }


# Singleton global para reutilizar cliente
_embedding_client: Optional[EmbeddingClient] = None


async def get_embedding_client(api_key: Optional[str] = None) -> EmbeddingClient:
    """
    Retorna instância global do cliente de embeddings

    Args:
        api_key: API key (opcional, usado na primeira inicialização)

    Returns:
        EmbeddingClient
    """
    global _embedding_client

    if _embedding_client is None:
        _embedding_client = EmbeddingClient(api_key=api_key)

    return _embedding_client
