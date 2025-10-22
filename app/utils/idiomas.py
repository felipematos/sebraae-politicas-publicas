# -*- coding: utf-8 -*-
"""
Modulo para geracao de queries multilingues
Gera variacoes de queries em 8+ idiomas para cada falha de mercado
"""
import re
import asyncio
from typing import List, Dict, Any
from app.config import settings


# Mapa de idiomas com nomes descritivos
MAPA_IDIOMAS_NOMES = {
    "pt": "Portugues (Brasil)",
    "en": "English",
    "es": "Espanol",
    "fr": "Francais",
    "de": "Deutsch",
    "it": "Italiano",
    "ar": "Arabi",
    "ko": "Coreano",
    "he": "Hebraico"
}


def normalizar_query(query: str) -> str:
    """
    Normaliza uma query removendo caracteres especiais e mantendo palavras-chave

    Args:
        query: Query original

    Returns:
        Query normalizada
    """
    if not query:
        return ""

    # Converter para minusculas
    normalizada = query.lower()

    # Remover caracteres especiais mantendo acentos
    normalizada = re.sub(r'[^\w\s\-áàâãäéèêëíìîïóòôõöúùûüçñ]', '', normalizada)

    # Remover espacos multiplos
    normalizada = re.sub(r'\s+', ' ', normalizada).strip()

    return normalizada


async def traduzir_query(
    query: str,
    idioma_origem: str,
    idioma_alvo: str
) -> str:
    """
    Traduz uma query de um idioma para outro

    Args:
        query: Query a traduzir
        idioma_origem: Codigo do idioma origem (pt, en, etc)
        idioma_alvo: Codigo do idioma alvo

    Returns:
        Query traduzida
    """
    # Se eh o mesmo idioma, retornar a query original
    if idioma_origem == idioma_alvo:
        return query

    # Mapping simples de traducoes comuns para idiomas principais
    # Em producao, usar Claude API para traducoes mais precisas

    traducoes_comuns = {
        ("pt", "en"): {
            "acesso": "access",
            "credito": "credit",
            "financiamento": "financing",
            "startup": "startup",
            "mercado": "market",
            "falta de": "lack of",
            "dificuldade": "difficulty",
            "barreira": "barrier",
            "regulacao": "regulation",
            "imposto": "tax"
        },
        ("en", "pt"): {
            "access": "acesso",
            "credit": "credito",
            "financing": "financiamento",
            "startup": "startup",
            "market": "mercado",
            "lack of": "falta de",
            "difficulty": "dificuldade",
            "barrier": "barreira",
            "regulation": "regulacao",
            "tax": "imposto"
        },
        ("pt", "es"): {
            "acesso": "acceso",
            "credito": "credito",
            "financiamento": "financiamiento",
            "startup": "startup",
            "mercado": "mercado",
            "falta de": "falta de",
            "dificuldade": "dificultad",
            "regulacao": "regulacion"
        },
        ("en", "es"): {
            "access": "acceso",
            "credit": "credito",
            "financing": "financiamiento",
            "startup": "startup",
            "market": "mercado",
            "lack of": "falta de",
            "difficulty": "dificultad",
            "regulation": "regulacion"
        }
    }

    chave = (idioma_origem, idioma_alvo)
    mapa = traducoes_comuns.get(chave, {})

    resultado = query.lower()
    for origem, alvo in mapa.items():
        resultado = re.sub(r'\b' + re.escape(origem) + r'\b', alvo, resultado)

    # Se nao encontrou traducoes, usar estrategia simples
    if resultado == query.lower():
        # Para idiomas nao mapeados, fazer transliteracao simples
        resultado = f"[{idioma_alvo.upper()}] {query}"

    return resultado


async def gerar_variacoes_query(
    titulo: str,
    descricao: str,
    dica_busca: str
) -> List[str]:
    """
    Gera multiplas variacoes de uma query baseada no titulo, descricao e dica

    Args:
        titulo: Titulo da falha
        descricao: Descricao da falha
        dica_busca: Dica de busca para pesquisa

    Returns:
        Lista com 5+ variacoes de queries
    """
    variacoes = []

    # Variacao 1: Titulo direto
    variacoes.append(titulo)

    # Variacao 2: Titulo + primeiras palavras da descricao
    palavras_desc = descricao.split()[:3]
    if palavras_desc:
        variacoes.append(f"{titulo} {' '.join(palavras_desc)}")

    # Variacao 3: Apenas dica de busca
    if dica_busca:
        variacoes.append(dica_busca)

    # Variacao 4: Descricao resumida
    desc_resumida = descricao[:80]  # Primeiros 80 caracteres
    variacoes.append(f"Como resolver: {desc_resumida}")

    # Variacao 5: Pesquisa + palavra-chave principal
    primeira_dica = dica_busca.split(",")[0].strip() if dica_busca else "problema"
    variacoes.append(f"Solucao para {primeira_dica} em startups")

    # Variacao 6: Policy/regulation angle
    variacoes.append(f"Politica publica para {primeira_dica.lower()}")

    # Remover duplicatas
    variacoes = list(dict.fromkeys(variacoes))

    return variacoes[:6]  # Retornar no maximo 6 variacoes


async def gerar_queries_multilingues(falha: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Gera queries multilingues para uma falha de mercado

    Args:
        falha: Dicionario com id, titulo, descricao, dica_busca

    Returns:
        Lista de queries com idioma, variacao e falha_id
    """
    titulo = falha.get("titulo", "")
    descricao = falha.get("descricao", "")
    dica_busca = falha.get("dica_busca", "")
    falha_id = falha.get("id", 0)

    # Gerar variacoes da query
    variacoes = await gerar_variacoes_query(titulo, descricao, dica_busca)

    queries_multilingues = []

    # Para cada variacao
    for num_variacao, variacao in enumerate(variacoes, 1):
        # Para cada idioma
        for idioma in settings.IDIOMAS:
            try:
                # Traduzir para o idioma alvo
                query_traduzida = await traduzir_query(
                    variacao,
                    "pt",  # Assumir que variacoes sao em portugues
                    idioma
                )

                queries_multilingues.append({
                    "falha_id": falha_id,
                    "query": query_traduzida,
                    "idioma": idioma,
                    "variacao": num_variacao,
                    "idioma_nome": MAPA_IDIOMAS_NOMES.get(idioma, idioma)
                })
            except Exception as e:
                print(f"Erro traduzindo para {idioma}: {e}")
                # Fallback: adicionar com prefixo de idioma
                queries_multilingues.append({
                    "falha_id": falha_id,
                    "query": f"[{idioma.upper()}] {variacao}",
                    "idioma": idioma,
                    "variacao": num_variacao,
                    "idioma_nome": MAPA_IDIOMAS_NOMES.get(idioma, idioma)
                })

    return queries_multilingues


async def traduzir_com_claude(
    textos: List[str],
    idioma_origem: str = "pt",
    idioma_alvo: str = "en"
) -> List[str]:
    """
    Traduz multiplos textos usando Claude API (para melhor qualidade)

    Args:
        textos: Lista de textos para traduzir
        idioma_origem: Codigo do idioma origem
        idioma_alvo: Codigo do idioma alvo

    Returns:
        Lista de textos traduzidos
    """
    # Nota: Esta funcao sera implementada quando integrarmos Claude API
    # Por enquanto, usar fallback com traducoes simples

    traducoes = []
    for texto in textos:
        traducao = await traduzir_query(texto, idioma_origem, idioma_alvo)
        traducoes.append(traducao)

    return traducoes
