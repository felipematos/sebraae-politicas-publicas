# -*- coding: utf-8 -*-
"""
Endpoints para gerenciar configuracoes da aplicacao
Permite habilitar/desabilitar canais de pesquisa
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.config import settings

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
    
    return {
        "mensagem": "Canais atualizados com sucesso",
        "status": settings.SEARCH_CHANNELS_ENABLED,
        "timestamp": __import__("datetime").datetime.now().isoformat()
    }
