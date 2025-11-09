# -*- coding: utf-8 -*-
"""
Configuração de modelos de embedding disponíveis
Suporta OpenAI e Jina AI
"""
from typing import Dict, Any, List
from enum import Enum


class EmbeddingProvider(str, Enum):
    """Provedores de embedding disponíveis"""
    OPENAI = "openai"
    JINA = "jina"


# Configuração de modelos de embedding disponíveis
MODELOS_EMBEDDING: Dict[str, Dict[str, Any]] = {
    # ========== OpenAI Models ==========
    "text-embedding-3-small": {
        "provider": EmbeddingProvider.OPENAI,
        "nome_exibicao": "OpenAI text-embedding-3-small",
        "descricao": "Modelo compacto e eficiente para embeddings de texto",
        "dimensoes": 1536,
        "custo_por_1k_tokens": 0.00002,  # USD
        "custo_estimado_brl": "R$ 0,0001 por 1.000 tokens (~R$ 0,01 por 10 páginas)",
        "max_tokens": 8191,
        "performance": "Alta velocidade e qualidade",
        "recomendado": True,
        "disponivel": True
    },
    "text-embedding-3-large": {
        "provider": EmbeddingProvider.OPENAI,
        "nome_exibicao": "OpenAI text-embedding-3-large",
        "descricao": "Modelo premium para máxima qualidade de embeddings",
        "dimensoes": 3072,
        "custo_por_1k_tokens": 0.00013,  # USD
        "custo_estimado_brl": "R$ 0,00065 por 1.000 tokens (~R$ 0,065 por 10 páginas)",
        "max_tokens": 8191,
        "performance": "Máxima qualidade, velocidade moderada",
        "recomendado": False,
        "disponivel": True
    },
    "text-embedding-ada-002": {
        "provider": EmbeddingProvider.OPENAI,
        "nome_exibicao": "OpenAI text-embedding-ada-002 (Legacy)",
        "descricao": "Modelo anterior da OpenAI, mantido por compatibilidade",
        "dimensoes": 1536,
        "custo_por_1k_tokens": 0.0001,  # USD
        "custo_estimado_brl": "R$ 0,0005 por 1.000 tokens (~R$ 0,05 por 10 páginas)",
        "max_tokens": 8191,
        "performance": "Boa qualidade, velocidade moderada",
        "recomendado": False,
        "disponivel": True
    },

    # ========== Jina AI Models ==========
    "jina-embeddings-v2-base-en": {
        "provider": EmbeddingProvider.JINA,
        "nome_exibicao": "Jina Embeddings v2 Base EN",
        "descricao": "Modelo base da Jina para embeddings em inglês, alta qualidade",
        "dimensoes": 768,
        "custo_por_1k_tokens": 0.00002,  # USD (aproximado)
        "custo_estimado_brl": "R$ 0,0001 por 1.000 tokens (~R$ 0,01 por 10 páginas)",
        "max_tokens": 8192,
        "performance": "Alta qualidade, otimizado para busca semântica",
        "recomendado": True,
        "disponivel": True
    },
    "jina-embeddings-v2-small-en": {
        "provider": EmbeddingProvider.JINA,
        "nome_exibicao": "Jina Embeddings v2 Small EN",
        "descricao": "Modelo compacto da Jina, mais rápido e econômico",
        "dimensoes": 512,
        "custo_por_1k_tokens": 0.00001,  # USD (aproximado)
        "custo_estimado_brl": "R$ 0,00005 por 1.000 tokens (~R$ 0,005 por 10 páginas)",
        "max_tokens": 8192,
        "performance": "Velocidade alta, boa qualidade",
        "recomendado": False,
        "disponivel": True
    },
    "jina-embeddings-v2-base-multilingual": {
        "provider": EmbeddingProvider.JINA,
        "nome_exibicao": "Jina Embeddings v2 Base Multilingual",
        "descricao": "Modelo multilíngue da Jina, suporta português e 100+ idiomas",
        "dimensoes": 768,
        "custo_por_1k_tokens": 0.00002,  # USD (aproximado)
        "custo_estimado_brl": "R$ 0,0001 por 1.000 tokens (~R$ 0,01 por 10 páginas)",
        "max_tokens": 8192,
        "performance": "Excelente para textos em português",
        "recomendado": True,
        "disponivel": True
    },
    "jina-clip-v1": {
        "provider": EmbeddingProvider.JINA,
        "nome_exibicao": "Jina CLIP v1",
        "descricao": "Modelo multimodal (texto + imagem) da Jina",
        "dimensoes": 768,
        "custo_por_1k_tokens": 0.00003,  # USD (aproximado)
        "custo_estimado_brl": "R$ 0,00015 por 1.000 tokens (~R$ 0,015 por 10 páginas)",
        "max_tokens": 8192,
        "performance": "Suporta texto e imagens",
        "recomendado": False,
        "disponivel": True
    }
}


def get_modelo_info(modelo_id: str) -> Dict[str, Any]:
    """
    Retorna informações sobre um modelo de embedding

    Args:
        modelo_id: ID do modelo (ex: "text-embedding-3-small")

    Returns:
        Dicionário com informações do modelo
    """
    return MODELOS_EMBEDDING.get(modelo_id, {})


def get_modelos_por_provider(provider: EmbeddingProvider) -> Dict[str, Dict[str, Any]]:
    """
    Retorna modelos de um provedor específico

    Args:
        provider: Provedor (OpenAI ou Jina)

    Returns:
        Dicionário com modelos do provedor
    """
    return {
        modelo_id: info
        for modelo_id, info in MODELOS_EMBEDDING.items()
        if info["provider"] == provider
    }


def get_modelos_recomendados() -> List[str]:
    """
    Retorna lista de modelos recomendados

    Returns:
        Lista de IDs dos modelos recomendados
    """
    return [
        modelo_id
        for modelo_id, info in MODELOS_EMBEDDING.items()
        if info.get("recomendado", False)
    ]


def get_dimensoes_modelo(modelo_id: str) -> int:
    """
    Retorna número de dimensões do modelo

    Args:
        modelo_id: ID do modelo

    Returns:
        Número de dimensões
    """
    info = get_modelo_info(modelo_id)
    return info.get("dimensoes", 1536)  # Default: 1536 (OpenAI small)


def get_provider_modelo(modelo_id: str) -> EmbeddingProvider:
    """
    Retorna o provedor de um modelo

    Args:
        modelo_id: ID do modelo

    Returns:
        Provedor do modelo
    """
    info = get_modelo_info(modelo_id)
    return info.get("provider", EmbeddingProvider.OPENAI)
