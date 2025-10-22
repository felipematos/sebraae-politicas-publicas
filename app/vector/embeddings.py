# -*- coding: utf-8 -*-
"""
Cliente de embeddings para gerar vetores de texto
Usa OpenAI text-embedding-3-small para embeddings
"""
import asyncio
from typing import List, Optional
from openai import AsyncOpenAI


class EmbeddingClient:
    """Cliente para gerar embeddings usando OpenAI"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small"
    ):
        """
        Inicializa cliente de embeddings

        Args:
            api_key: API key da OpenAI (opcional, usa env var se não fornecido)
            model: Modelo a usar para embeddings
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.cache = {}  # Cache simples para evitar requisições duplicadas

    async def embed_text(self, text: str) -> List[float]:
        """
        Gera embedding para um texto

        Args:
            text: Texto para gerar embedding

        Returns:
            Lista de floats representando o embedding (dimensão 1536)
        """
        if not text or not text.strip():
            return [0.0] * 1536

        # Verificar cache
        if text in self.cache:
            return self.cache[text]

        try:
            # Truncar texto se necessário (máx ~8000 tokens)
            text_trunc = text[:8000] if len(text) > 8000 else text

            response = await self.client.embeddings.create(
                input=text_trunc,
                model=self.model
            )

            embedding = response.data[0].embedding

            # Guardar em cache
            self.cache[text] = embedding

            return embedding

        except Exception as e:
            print(f"Erro gerando embedding para '{text[:50]}...': {e}")
            # Retornar embedding zero se falhar
            return [0.0] * 1536

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
