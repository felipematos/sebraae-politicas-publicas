# -*- coding: utf-8 -*-
"""
Endpoints para gerenciar configuracoes da aplicacao
Permite habilitar/desabilitar canais de pesquisa
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.config import settings, save_search_channels_config

router = APIRouter(tags=["Config"])


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
