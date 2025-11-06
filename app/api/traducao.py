# -*- coding: utf-8 -*-
"""
Router FastAPI para endpoint de tradução
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.integracao.openrouter_api import OpenRouterClient
from app.utils.logger import logger
from app.database import db

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
        # Buscar resultado no banco
        resultado = await db.fetch_one(
            "SELECT * FROM resultados_pesquisa WHERE id = ?",
            (resultado_id,)
        )

        if not resultado:
            raise HTTPException(status_code=404, detail="Resultado não encontrado")

        # Se já tem tradução (e não está vazia), retornar as traduções existentes
        titulo_pt = resultado.get('titulo_pt')
        descricao_pt = resultado.get('descricao_pt')

        if titulo_pt and titulo_pt.strip() and descricao_pt and descricao_pt.strip():
            logger.info(f"Resultado {resultado_id} já possui traduções")
            return {
                "id": resultado_id,
                "titulo_pt": resultado['titulo_pt'],
                "descricao_pt": resultado['descricao_pt'],
                "idioma": resultado.get('idioma', 'en'),
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

        idioma_origem = resultado.get('idioma') or 'en'
        idioma_origem_nome = idiomas_map.get(idioma_origem.lower(), idioma_origem)

        logger.info(f"Traduzindo resultado {resultado_id} de {idioma_origem} para português")

        # Traduzir título e descrição usando OpenRouterClient
        async with OpenRouterClient() as client:
            titulo_pt = await client.traduzir_texto(
                texto=resultado['titulo'],
                idioma_alvo="pt",
                idioma_origem=idioma_origem
            )

            if not titulo_pt:
                # Se falhou completamente, usar original
                titulo_pt = resultado['titulo']

            descricao_pt = await client.traduzir_texto(
                texto=resultado['descricao'],
                idioma_alvo="pt",
                idioma_origem=idioma_origem
            )

            if not descricao_pt:
                # Se falhou completamente, usar original
                descricao_pt = resultado['descricao']

        # Atualizar resultado no banco
        await db.execute(
            "UPDATE resultados_pesquisa SET titulo_pt = ?, descricao_pt = ? WHERE id = ?",
            (titulo_pt.strip(), descricao_pt.strip(), resultado_id)
        )

        logger.info(f"Tradução do resultado {resultado_id} concluída e salva no banco")

        return {
            "id": resultado_id,
            "titulo_pt": titulo_pt.strip(),
            "descricao_pt": descricao_pt.strip(),
            "idioma": resultado.get('idioma', 'en'),
            "ja_traduzido": False
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao traduzir resultado {resultado_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao traduzir resultado: {str(e)}")
