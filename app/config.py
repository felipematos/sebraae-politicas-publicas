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
    ANTHROPIC_API_KEY: Optional[str] = None  # Para avaliar relevancia com Claude

    # Processamento
    MAX_WORKERS: int = 5
    REQUEST_TIMEOUT: int = 60  # segundos
    RATE_LIMIT_DELAY: float = 1.0  # segundos entre requests
    MAX_RETRIES: int = 3

    # Pesquisa
    MIN_CONFIDENCE_THRESHOLD: float = 0.3
    QUERIES_PER_FALHA: int = 5

    # Idiomas suportados
    IDIOMAS: list[str] = [
        "pt", "en", "es", "fr", "de", "it", "ar", "ko", "he"
    ]

    # Ferramentas de pesquisa
    FERRAMENTAS: list[str] = ["perplexity", "jina", "deep_research"]


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
