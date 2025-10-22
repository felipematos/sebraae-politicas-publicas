# -*- coding: utf-8 -*-
"""
Configuracoes da aplicacao
Carrega variaveis de ambiente do arquivo .env
"""
import os
from pathlib import Path
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuracoes globais da aplicacao"""

    model_config = ConfigDict(env_file=".env", case_sensitive=True)

    # Ambiente
    ENV: str = "development"
    DEBUG: bool = True

    # Aplicacao
    APP_NAME: str = "Pesquisa de Politicas Publicas - Sebrae"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # Banco de dados
    DATABASE_PATH: str = "falhas_mercado_v1.db"

    # APIs externas
    JINA_API_KEY: str
    PERPLEXITY_API_KEY: str
    TAVILY_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None  # Para avaliar relevancia com Claude
    OPENAI_API_KEY: Optional[str] = None  # Para gerar embeddings

    # Canais de pesquisa ativos (pode ser controlado via UI)
    SEARCH_CHANNELS_ENABLED: dict = {
        "perplexity": True,
        "jina": True,
        "tavily": True,
        "serper": True,
        "deep_research": True
    }

    # Processamento
    MAX_WORKERS: int = 5
    REQUEST_TIMEOUT: int = 60  # segundos
    RATE_LIMIT_DELAY: float = 1.0  # segundos entre requests
    MAX_RETRIES: int = 3

    # Pesquisa
    MIN_CONFIDENCE_THRESHOLD: float = 0.3
    QUERIES_PER_FALHA: int = 5

    # Busca Adaptativa (inteligente com LLM)
    MIN_BUSCAS_POR_FALHA: int = 2  # Mínimo obrigatório
    MAX_BUSCAS_POR_FALHA: int = 8  # Máximo permitido
    QUALIDADE_MINIMA_PARA_PARAR: float = 0.75  # Score mínimo para parar (0-1)
    USAR_BUSCA_ADAPTATIVA: bool = True  # Ativar/desativar busca inteligente

    # Idiomas suportados
    IDIOMAS: list[str] = [
        "pt", "en", "es", "fr", "de", "it", "ar", "ko", "he"
    ]

    # Ferramentas de pesquisa
    FERRAMENTAS: list[str] = ["perplexity", "jina", "deep_research"]

    # ChromaDB - Banco de dados vetorial para RAG
    CHROMA_PERSIST_PATH: str = "chroma_db"  # Diretório para salvar dados
    EMBEDDING_MODEL: str = "text-embedding-3-small"  # Modelo OpenAI
    EMBEDDING_DIMENSION: int = 1536  # Dimensão dos embeddings
    USAR_VECTOR_DB: bool = True  # Ativar/desativar banco vetorial

    # RAG - Configurações de busca semântica
    RAG_ENABLED: bool = True  # Ativar/desativar RAG
    RAG_SIMILARITY_THRESHOLD: float = 0.7  # Threshold para resultados similares
    RAG_TOP_K_RESULTS: int = 5  # Número de resultados similares a buscar
    RAG_SIMILARITY_THRESHOLD_DEDUP: float = 0.85  # Threshold para deduplicação


# Instancia global de configuracoes
settings = Settings()


def get_database_path() -> Path:
    """Retorna o caminho absoluto do banco de dados"""
    base_dir = Path(__file__).parent.parent
    return base_dir / settings.DATABASE_PATH


def get_static_path() -> Path:
    """Retorna o caminho do diretorio static"""
    base_dir = Path(__file__).parent.parent
    return base_dir / "static"


def get_chroma_path() -> Path:
    """Retorna o caminho absoluto para o ChromaDB"""
    base_dir = Path(__file__).parent.parent
    return base_dir / settings.CHROMA_PERSIST_PATH
