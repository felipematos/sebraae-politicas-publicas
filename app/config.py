# -*- coding: utf-8 -*-
"""
Configuracoes da aplicacao
Carrega variaveis de ambiente do arquivo .env
Persiste configuracoes de canais de pesquisa em arquivo JSON
"""
import os
import json
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
    EXA_API_key: Optional[str] = None  # Para buscas semanticas com Exa AI
    ANTHROPIC_API_KEY: Optional[str] = None  # Para avaliar relevancia com Claude
    OPENAI_API_KEY: Optional[str] = None  # Para gerar embeddings
    OPENROUTER_API_KEY: Optional[str] = None  # Para tradução com modelos gratuitos

    # Canais de pesquisa ativos (pode ser controlado via UI)
    # deep_research está desabilitado por padrão (problemas de integração)
    SEARCH_CHANNELS_ENABLED: dict = {
        "perplexity": True,
        "jina": True,
        "tavily": True,
        "serper": True,
        "exa": False,  # Pode ser habilitado via UI
        "deep_research": False  # Desabilitado por padrão
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
    USAR_BUSCA_ADAPTATIVA: bool = False  # Ativar/desativar busca inteligente [DESATIVADO para acelerar]

    # Idiomas suportados
    IDIOMAS: list[str] = [
        "pt", "en", "es", "fr", "de", "it", "ar", "ja", "ko", "he"
    ]

    # Ferramentas de pesquisa (atualizado dinamicamente com base em SEARCH_CHANNELS_ENABLED)
    # Use get_ferramentas_ativas() para obter lista dinâmica
    FERRAMENTAS: list[str] = ["perplexity", "jina", "tavily", "serper", "exa"]

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


# Arquivo de configuracao persistente (definir antes de instanciar settings)
CONFIG_FILE_PATH = Path(__file__).parent.parent / "config_channels.json"


def get_config_file_path() -> Path:
    """Retorna o caminho do arquivo de configuracao persistente"""
    return CONFIG_FILE_PATH


def load_search_channels_config(default_config: dict) -> dict:
    """
    Carrega configuracao de canais de pesquisa do arquivo JSON.
    Se o arquivo nao existir, retorna a configuracao padrao.
    """
    if CONFIG_FILE_PATH.exists():
        try:
            with open(CONFIG_FILE_PATH, "r") as f:
                config = json.load(f)
                # Validar que todas as chaves conhecidas estao presentes
                for channel in default_config.keys():
                    if channel not in config:
                        config[channel] = default_config[channel]
                print(f"[INFO] Configuracao de canais carregada de {CONFIG_FILE_PATH}")
                return config
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARN] Erro ao carregar config_channels.json: {e}")
            return default_config.copy()
    else:
        print(f"[INFO] Arquivo config_channels.json nao encontrado, usando padrao")
        return default_config.copy()


def save_search_channels_config(config: dict) -> bool:
    """
    Salva configuracao de canais de pesquisa em arquivo JSON.
    Retorna True se salvo com sucesso, False caso contrario.
    """
    try:
        # Criar diretorio se nao existir
        CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(CONFIG_FILE_PATH, "w") as f:
            json.dump(config, f, indent=2)

        print(f"[INFO] Configuracao de canais salva em {CONFIG_FILE_PATH}")
        return True
    except IOError as e:
        print(f"[ERROR] Erro ao salvar config_channels.json: {e}")
        return False


# Instancia global de configuracoes
settings = Settings()

# Carregar configuracao persistente na inicializacao
def initialize_settings():
    """Inicializa as configuracoes carregando do arquivo persistente se existir"""
    loaded_config = load_search_channels_config(settings.SEARCH_CHANNELS_ENABLED)
    # Atualizar dict in-place para garantir que as mudanças persistem
    settings.SEARCH_CHANNELS_ENABLED.clear()
    settings.SEARCH_CHANNELS_ENABLED.update(loaded_config)
    print(f"[CONFIG] Configuracao de canais atualizada: {settings.SEARCH_CHANNELS_ENABLED}")


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


def get_ferramentas_ativas() -> list[str]:
    """
    Retorna lista de ferramentas que estão habilitadas em SEARCH_CHANNELS_ENABLED
    """
    return [
        ferramenta
        for ferramenta, habilitada in settings.SEARCH_CHANNELS_ENABLED.items()
        if habilitada
    ]


# Inicializar configuracoes na importacao
initialize_settings()
