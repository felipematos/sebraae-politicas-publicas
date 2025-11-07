# -*- coding: utf-8 -*-
"""
Endpoints para gerenciar configuracoes da aplicacao
Permite habilitar/desabilitar canais de pesquisa, controlar modo teste e gerenciar chaves de API
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
import os
from pathlib import Path
from app.config import settings, save_search_channels_config, save_test_mode_config
from app.database import get_estatisticas_gerais

router = APIRouter(tags=["Config"])


# ==================== CHAVES DE API ====================

class APIKeysRequest(BaseModel):
    perplexity_api_key: Optional[str] = None
    jina_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None
    serper_api_key: Optional[str] = None
    exa_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None


def _get_env_file_path() -> Path:
    """Retorna o caminho do arquivo .env"""
    env_file = Path(__file__).parent.parent.parent / ".env"
    return env_file


def _read_env_file() -> Dict[str, str]:
    """Lê o arquivo .env e retorna um dicionário com as variáveis"""
    env_file = _get_env_file_path()
    env_vars = {}

    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"\'')

    return env_vars


def _write_env_file(env_vars: Dict[str, str]) -> None:
    """Escreve as variáveis no arquivo .env"""
    env_file = _get_env_file_path()

    # Criar arquivo se não existir
    if not env_file.exists():
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.touch()

    # Ler arquivo existente para preservar outras variáveis
    existing_vars = _read_env_file()

    # Mesclar com novas variáveis
    existing_vars.update(env_vars)

    # Escrever arquivo
    with open(env_file, 'w', encoding='utf-8') as f:
        for key, value in sorted(existing_vars.items()):
            if key and not key.startswith('#'):
                f.write(f'{key}={value}\n')


@router.post("/config/api-keys")
async def save_api_keys(request: APIKeysRequest) -> Dict[str, Any]:
    """
    Salva as chaves de API no arquivo .env

    Args:
        request: Objeto com as chaves de API

    Returns:
        Status da operação
    """
    try:
        env_vars = {}

        # Adicionar apenas as chaves que foram fornecidas
        if request.perplexity_api_key:
            env_vars['PERPLEXITY_API_KEY'] = request.perplexity_api_key

        if request.jina_api_key:
            env_vars['JINA_API_KEY'] = request.jina_api_key

        if request.tavily_api_key:
            env_vars['TAVILY_API_KEY'] = request.tavily_api_key

        if request.serper_api_key:
            env_vars['SERPER_API_KEY'] = request.serper_api_key

        if request.exa_api_key:
            env_vars['EXA_API_KEY'] = request.exa_api_key

        if request.openai_api_key:
            env_vars['OPENAI_API_KEY'] = request.openai_api_key

        if request.openrouter_api_key:
            env_vars['OPENROUTER_API_KEY'] = request.openrouter_api_key

        # Escrever no arquivo .env
        _write_env_file(env_vars)

        # Atualizar variáveis de ambiente da aplicação
        for key, value in env_vars.items():
            os.environ[key] = value

        return {
            "sucesso": True,
            "mensagem": "Chaves de API salvas com sucesso",
            "chaves_atualizadas": list(env_vars.keys()),
            "timestamp": __import__("datetime").datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao salvar chaves de API: {str(e)}"
        )


def _mascarar_chave(chave: str) -> str:
    """Mascara uma chave mostrando apenas os primeiros 4 e últimos 4 caracteres"""
    if not chave or len(chave) < 8:
        return "***"
    return f"{chave[:4]}...{chave[-4:]}"


@router.get("/config/api-keys")
async def get_api_keys_status() -> Dict[str, Any]:
    """
    Retorna o status das chaves de API com valores mascarados

    Returns:
        Status de cada chave (null se não configurada, ou valor mascarado)
    """
    try:
        env_vars = _read_env_file()

        api_keys_values = {
            "perplexity_api_key": _mascarar_chave(env_vars.get("PERPLEXITY_API_KEY", "")) if "PERPLEXITY_API_KEY" in env_vars else None,
            "jina_api_key": _mascarar_chave(env_vars.get("JINA_API_KEY", "")) if "JINA_API_KEY" in env_vars else None,
            "tavily_api_key": _mascarar_chave(env_vars.get("TAVILY_API_KEY", "")) if "TAVILY_API_KEY" in env_vars else None,
            "serper_api_key": _mascarar_chave(env_vars.get("SERPER_API_KEY", "")) if "SERPER_API_KEY" in env_vars else None,
            "exa_api_key": _mascarar_chave(env_vars.get("EXA_API_KEY", "")) if "EXA_API_KEY" in env_vars else None,
            "openai_api_key": _mascarar_chave(env_vars.get("OPENAI_API_KEY", "")) if "OPENAI_API_KEY" in env_vars else None,
            "openrouter_api_key": _mascarar_chave(env_vars.get("OPENROUTER_API_KEY", "")) if "OPENROUTER_API_KEY" in env_vars else None
        }

        return {
            "sucesso": True,
            "chaves": api_keys_values,
            "total_configuradas": sum(1 for v in api_keys_values.values() if v is not None),
            "timestamp": __import__("datetime").datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao ler status das chaves de API: {str(e)}"
        )


@router.get("/config/channels")
async def get_search_channels() -> Dict[str, Any]:
    """
    Retorna status dos canais de pesquisa habilitados
    
    Returns:
        Dicionario com status de cada canal
    """
    return {
        "channels": settings.SEARCH_CHANNELS_ENABLED,
        "canais_ativos": sum(
            1 for v in settings.SEARCH_CHANNELS_ENABLED.values() if v
        ),
        "total_canais": len(settings.SEARCH_CHANNELS_ENABLED)
    }


@router.post("/config/channels/{channel_name}")
async def toggle_channel(channel_name: str, enabled: bool) -> Dict[str, Any]:
    """
    Habilita ou desabilita um canal de pesquisa
    
    Args:
        channel_name: Nome do canal (perplexity, jina, tavily, serper, deep_research)
        enabled: True para habilitar, False para desabilitar
    
    Returns:
        Novo status do canal
    """
    # Validar nome do canal
    valid_channels = list(settings.SEARCH_CHANNELS_ENABLED.keys())
    if channel_name not in valid_channels:
        raise HTTPException(
            status_code=400,
            detail=f"Canal invalido. Canais disponiveis: {valid_channels}"
        )
    
    # Atualizar
    settings.SEARCH_CHANNELS_ENABLED[channel_name] = enabled

    # Persistir configuracao
    save_search_channels_config(settings.SEARCH_CHANNELS_ENABLED)

    return {
        "canal": channel_name,
        "ativo": enabled,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "status_todos": settings.SEARCH_CHANNELS_ENABLED
    }


@router.post("/config/channels/reset")
async def reset_channels() -> Dict[str, Any]:
    """
    Reseta todos os canais para a configuracao padrao (todos habilitados)

    Returns:
        Status atualizado de todos os canais
    """
    for channel in settings.SEARCH_CHANNELS_ENABLED:
        settings.SEARCH_CHANNELS_ENABLED[channel] = True

    # Persistir configuracao
    save_search_channels_config(settings.SEARCH_CHANNELS_ENABLED)

    return {
        "mensagem": "Todos os canais foram reabilitados",
        "status": settings.SEARCH_CHANNELS_ENABLED,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }


@router.post("/config/channels/bulk")
async def bulk_update_channels(channels: Dict[str, bool]) -> Dict[str, Any]:
    """
    Atualiza multiplos canais de uma vez

    Args:
        channels: Dicionario com {canal_name: enabled}

    Returns:
        Novo status de todos os canais
    """
    # Validar todos os canais
    valid_channels = list(settings.SEARCH_CHANNELS_ENABLED.keys())
    for channel in channels.keys():
        if channel not in valid_channels:
            raise HTTPException(
                status_code=400,
                detail=f"Canal invalido: {channel}"
            )

    # Atualizar
    for channel, enabled in channels.items():
        settings.SEARCH_CHANNELS_ENABLED[channel] = enabled

    # Persistir configuracao
    save_search_channels_config(settings.SEARCH_CHANNELS_ENABLED)

    return {
        "mensagem": "Canais atualizados com sucesso",
        "status": settings.SEARCH_CHANNELS_ENABLED,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }


@router.get("/config/search-channels")
async def get_search_channels_config() -> Dict[str, Any]:
    """
    Retorna a configuracao das ferramentas de pesquisa

    Returns:
        Configuracao atual das ferramentas (perplexity, jina, tavily, serper, deep_research)
    """
    return {
        "search_channels_enabled": settings.SEARCH_CHANNELS_ENABLED,
        "total_habilitadas": sum(1 for v in settings.SEARCH_CHANNELS_ENABLED.values() if v),
        "total_ferramentas": len(settings.SEARCH_CHANNELS_ENABLED)
    }


@router.put("/config/search-channels")
async def update_search_channels_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Atualiza a configuracao das ferramentas de pesquisa

    Args:
        config: Dicionario contendo 'search_channels_enabled' com {ferramenta: enabled}

    Returns:
        Nova configuracao salva
    """
    if "search_channels_enabled" not in config:
        raise HTTPException(
            status_code=400,
            detail="Campo 'search_channels_enabled' obrigatorio"
        )

    search_channels = config["search_channels_enabled"]

    # Validar todas as ferramentas
    valid_channels = list(settings.SEARCH_CHANNELS_ENABLED.keys())
    for channel in search_channels.keys():
        if channel not in valid_channels:
            raise HTTPException(
                status_code=400,
                detail=f"Ferramenta invalida: {channel}. Ferramentas validas: {valid_channels}"
            )

    # Detectar quais ferramentas foram habilitadas (não estavam antes)
    ferramentas_novas = [
        canal for canal, novo_status in search_channels.items()
        if novo_status and not settings.SEARCH_CHANNELS_ENABLED.get(canal, False)
    ]

    # Atualizar configuracao
    for channel, enabled in search_channels.items():
        settings.SEARCH_CHANNELS_ENABLED[channel] = enabled

    # Persistir configuracao
    save_search_channels_config(settings.SEARCH_CHANNELS_ENABLED)

    resultado = {
        "mensagem": "Configuracao das ferramentas atualizada com sucesso",
        "search_channels_enabled": settings.SEARCH_CHANNELS_ENABLED,
        "total_habilitadas": sum(1 for v in settings.SEARCH_CHANNELS_ENABLED.values() if v),
        "ferramentas_novas": ferramentas_novas,
        "requer_repopulacao": len(ferramentas_novas) > 0,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }

    return resultado


# ==================== MODO TESTE ====================

@router.get("/config/test-mode")
async def get_test_mode() -> Dict[str, Any]:
    """
    Retorna status do modo teste

    Returns:
        Status atual do modo teste e limit de queries
    """
    return {
        "test_mode_enabled": settings.TEST_MODE,
        "test_mode_limit": settings.TEST_MODE_LIMIT,
        "descricao": "Quando ativado, processa apenas as primeiras N queries para testes"
    }


@router.post("/config/test-mode/{enabled}")
async def toggle_test_mode(enabled: bool) -> Dict[str, Any]:
    """
    Ativa ou desativa o modo teste

    Args:
        enabled: True para ativar, False para desativar

    Returns:
        Novo status do modo teste
    """
    settings.TEST_MODE = enabled
    # Persistir configuracao em arquivo JSON
    save_test_mode_config(settings.TEST_MODE, settings.TEST_MODE_LIMIT)

    return {
        "mensagem": f"Modo teste {'ATIVADO' if enabled else 'DESATIVADO'}",
        "test_mode_enabled": settings.TEST_MODE,
        "test_mode_limit": settings.TEST_MODE_LIMIT,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }


@router.post("/config/test-mode/limit/{limit}")
async def set_test_mode_limit(limit: int) -> Dict[str, Any]:
    """
    Define o número máximo de queries para processar em modo teste

    Args:
        limit: Número de queries (ex: 10, 20, 50)

    Returns:
        Novo limite configurado
    """
    if limit < 1:
        raise HTTPException(
            status_code=400,
            detail="Limite deve ser maior que 0"
        )

    if limit > 1000:
        raise HTTPException(
            status_code=400,
            detail="Limite não pode exceder 1000 queries"
        )

    settings.TEST_MODE_LIMIT = limit
    # Persistir configuracao em arquivo JSON
    save_test_mode_config(settings.TEST_MODE, settings.TEST_MODE_LIMIT)

    return {
        "mensagem": f"Limite do modo teste atualizado para {limit} queries",
        "test_mode_enabled": settings.TEST_MODE,
        "test_mode_limit": settings.TEST_MODE_LIMIT,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }


# ==================== ESTATÍSTICAS ====================

@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """
    Retorna estatísticas gerais do sistema

    Returns:
        - total_falhas: Total de falhas de mercado
        - total_resultados: Total de resultados de pesquisa
        - pesquisas_concluidas: Pesquisas processadas
        - pesquisas_pendentes: Pesquisas aguardando processamento
        - confidence_medio: Confiança média das análises
    """
    try:
        stats = await get_estatisticas_gerais()
        return {
            "sucesso": True,
            "dados": stats
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": str(e),
            "dados": {
                "total_falhas": 0,
                "total_resultados": 0,
                "pesquisas_concluidas": 0,
                "pesquisas_pendentes": 0,
                "confidence_medio": 0.0
            }
        }
