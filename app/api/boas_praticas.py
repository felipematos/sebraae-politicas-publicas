# -*- coding: utf-8 -*-
"""
Router FastAPI para endpoints de boas práticas
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json

from app.database import get_falhas_mercado, listar_priorizacoes, obter_fontes_por_falha
from app.agente.analisador_boas_praticas import AnalisadorBoasPraticas
from app.utils.logger import logger

router = APIRouter(
    prefix="/api/boas-praticas",
    tags=["boas-praticas"]
)

analisador = AnalisadorBoasPraticas()


# Models Pydantic
class BoaPratica(BaseModel):
    """Model para uma boa prática"""
    titulo: str
    descricao: Optional[str] = None
    is_sebrae: bool = False
    fonte: Optional[str] = None


class BoasPraticasFalha(BaseModel):
    """Model para boas práticas de uma falha"""
    falha_id: int
    titulo: str
    pilar: str
    praticas: List[BoaPratica]


class BuscarBoasPraticasResponse(BaseModel):
    """Response da busca de boas práticas"""
    boas_praticas: List[BoasPraticasFalha]
    total: int


@router.post("/buscar", response_model=BuscarBoasPraticasResponse)
async def buscar_boas_praticas():
    """
    Busca boas práticas para todas as falhas priorizadas

    Processo:
    1. Obtém todas as falhas priorizadas
    2. Para cada falha, busca nos resultados de pesquisa e documentos
    3. Identifica se a prática vem do Sebrae
    4. Retorna lista de falhas com suas respectivas boas práticas
    """
    try:
        logger.info("Iniciando busca de boas práticas")

        # 1. Obter falhas priorizadas
        priorizacoes = await listar_priorizacoes()
        if not priorizacoes:
            return BuscarBoasPraticasResponse(boas_praticas=[], total=0)

        # 2. Obter detalhes das falhas
        falhas = await get_falhas_mercado()
        falhas_dict = {f['id']: f for f in falhas}

        # 3. Analisar cada falha
        resultado = []

        for prio in priorizacoes:
            falha_id = prio['falha_id']
            falha = falhas_dict.get(falha_id)

            if not falha:
                continue

            # Obter fontes (resultados de pesquisa e documentos)
            fontes = await obter_fontes_por_falha(falha_id)

            # Analisar com LLM para extrair boas práticas
            praticas = await analisador.analisar_boas_praticas(
                falha=falha,
                fontes=fontes
            )

            if praticas:
                resultado.append(BoasPraticasFalha(
                    falha_id=falha_id,
                    titulo=falha['titulo'],
                    pilar=falha['pilar'],
                    praticas=praticas
                ))

        logger.info(f"Busca concluída: {len(resultado)} falhas com boas práticas")

        return BuscarBoasPraticasResponse(
            boas_praticas=resultado,
            total=len(resultado)
        )

    except Exception as e:
        logger.error(f"Erro ao buscar boas práticas: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/falha/{falha_id}")
async def obter_boas_praticas_falha(falha_id: int):
    """
    Obtém boas práticas para uma falha específica
    """
    try:
        # Obter detalhes da falha
        falhas = await get_falhas_mercado()
        falha = next((f for f in falhas if f['id'] == falha_id), None)

        if not falha:
            raise HTTPException(status_code=404, detail="Falha não encontrada")

        # Obter fontes
        fontes = await obter_fontes_por_falha(falha_id)

        # Analisar
        praticas = await analisador.analisar_boas_praticas(
            falha=falha,
            fontes=fontes
        )

        return {
            "falha_id": falha_id,
            "titulo": falha['titulo'],
            "pilar": falha['pilar'],
            "praticas": praticas
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter boas práticas da falha {falha_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
