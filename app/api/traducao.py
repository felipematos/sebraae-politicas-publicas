# -*- coding: utf-8 -*-
"""
Router FastAPI para endpoint de tradução
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.integracao.openrouter_api import OpenRouterClient
from app.utils.logger import logger

router = APIRouter()


class TraduzirRequest(BaseModel):
    texto: str
    idioma_origem: str
    idioma_destino: str = "pt"


class TraduzirResponse(BaseModel):
    traducao: str
    idioma_origem: str
    idioma_destino: str


@router.post("/api/traduzir", response_model=TraduzirResponse)
async def traduzir_texto(request: TraduzirRequest):
    """
    Traduz um texto de um idioma para outro usando LLM

    Args:
        texto: Texto a ser traduzido
        idioma_origem: Código do idioma de origem (ex: 'en', 'es', 'fr')
        idioma_destino: Código do idioma de destino (padrão: 'pt')

    Returns:
        TraduzirResponse com a tradução
    """
    try:
        logger.info(f"Traduzindo texto de {request.idioma_origem} para {request.idioma_destino}")

        # Mapear códigos de idioma para nomes
        idiomas_map = {
            'pt': 'português',
            'en': 'inglês',
            'es': 'espanhol',
            'fr': 'francês',
            'de': 'alemão',
            'it': 'italiano',
            'zh': 'chinês',
            'ja': 'japonês',
            'ko': 'coreano',
            'ar': 'árabe',
            'ru': 'russo',
            'hi': 'hindi'
        }

        idioma_origem_nome = idiomas_map.get(request.idioma_origem.lower(), request.idioma_origem)
        idioma_destino_nome = idiomas_map.get(request.idioma_destino.lower(), request.idioma_destino)

        # Criar prompt para tradução
        prompt = f"""Traduza o seguinte texto de {idioma_origem_nome} para {idioma_destino_nome}.

Regras:
1. Mantenha o tom e o estilo do texto original
2. Preserve termos técnicos quando apropriado
3. Retorne APENAS a tradução, sem explicações adicionais
4. Mantenha a formatação do texto original

Texto para traduzir:
{request.texto}

Tradução em {idioma_destino_nome}:"""

        # Usar OpenRouter para traduzir
        client = OpenRouterClient()
        traducao = await client.gerar_texto(
            prompt=prompt,
            modelo="anthropic/claude-3.5-sonnet",  # Modelo eficiente para tradução
            temperatura=0.3,  # Baixa temperatura para tradução mais precisa
            max_tokens=2000
        )

        if not traducao:
            raise HTTPException(status_code=500, detail="Erro ao gerar tradução")

        logger.info(f"Tradução concluída com sucesso ({len(traducao)} caracteres)")

        return TraduzirResponse(
            traducao=traducao.strip(),
            idioma_origem=request.idioma_origem,
            idioma_destino=request.idioma_destino
        )

    except Exception as e:
        logger.error(f"Erro ao traduzir texto: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao traduzir texto: {str(e)}")
