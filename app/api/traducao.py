# -*- coding: utf-8 -*-
"""
Router FastAPI para endpoint de tradução
"""
from fastapi import APIRouter, HTTPException, Depends
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


@router.post("/api/resultados/{resultado_id}/traduzir")
async def traduzir_resultado(resultado_id: int):
    """
    Traduz título e descrição de um resultado específico para português

    Args:
        resultado_id: ID do resultado a ser traduzido

    Returns:
        Dict com título_pt e descricao_pt traduzidos
    """
    try:
        # Importar dependências aqui para evitar erro de módulo
        from sqlalchemy.orm import Session
        from app.database import get_db
        from app.models import Resultado

        # Criar sessão do banco
        db = next(get_db())

        # Buscar resultado no banco
        resultado = db.query(Resultado).filter(Resultado.id == resultado_id).first()

        if not resultado:
            raise HTTPException(status_code=404, detail="Resultado não encontrado")

        # Se já tem tradução, retornar as traduções existentes
        if resultado.titulo_pt and resultado.descricao_pt:
            logger.info(f"Resultado {resultado_id} já possui traduções")
            return {
                "id": resultado_id,
                "titulo_pt": resultado.titulo_pt,
                "descricao_pt": resultado.descricao_pt,
                "idioma": resultado.idioma,
                "ja_traduzido": True
            }

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

        idioma_origem = resultado.idioma or 'en'
        idioma_origem_nome = idiomas_map.get(idioma_origem.lower(), idioma_origem)

        logger.info(f"Traduzindo resultado {resultado_id} de {idioma_origem} para português")

        # Traduzir título
        prompt_titulo = f"""Traduza o seguinte título de {idioma_origem_nome} para português.

Regras:
1. Mantenha o tom e o estilo do texto original
2. Preserve termos técnicos quando apropriado
3. Retorne APENAS a tradução, sem explicações adicionais
4. Mantenha a formatação do texto original

Texto para traduzir:
{resultado.titulo}

Tradução em português:"""

        client = OpenRouterClient()
        titulo_pt = await client.gerar_texto(
            prompt=prompt_titulo,
            modelo="anthropic/claude-3.5-sonnet",
            temperatura=0.3,
            max_tokens=500
        )

        if not titulo_pt:
            raise HTTPException(status_code=500, detail="Erro ao gerar tradução do título")

        # Traduzir descrição
        prompt_descricao = f"""Traduza a seguinte descrição de {idioma_origem_nome} para português.

Regras:
1. Mantenha o tom e o estilo do texto original
2. Preserve termos técnicos quando apropriado
3. Retorne APENAS a tradução, sem explicações adicionais
4. Mantenha a formatação do texto original

Texto para traduzir:
{resultado.descricao}

Tradução em português:"""

        descricao_pt = await client.gerar_texto(
            prompt=prompt_descricao,
            modelo="anthropic/claude-3.5-sonnet",
            temperatura=0.3,
            max_tokens=2000
        )

        if not descricao_pt:
            raise HTTPException(status_code=500, detail="Erro ao gerar tradução da descrição")

        # Atualizar resultado no banco
        resultado.titulo_pt = titulo_pt.strip()
        resultado.descricao_pt = descricao_pt.strip()
        db.commit()

        logger.info(f"Tradução do resultado {resultado_id} concluída e salva no banco")

        return {
            "id": resultado_id,
            "titulo_pt": titulo_pt.strip(),
            "descricao_pt": descricao_pt.strip(),
            "idioma": resultado.idioma,
            "ja_traduzido": False
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao traduzir resultado {resultado_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao traduzir resultado: {str(e)}")
