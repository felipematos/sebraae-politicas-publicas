# -*- coding: utf-8 -*-
"""
Avaliador de confianca para resultados de pesquisa
Calcula confidence scores usando multiplos fatores
"""
import re
import asyncio
from typing import List, Dict, Any


# Stop words em portugues para remover ao extrair palavras-chave
STOP_WORDS_PT = {
    "o", "a", "os", "as", "um", "uma", "uns", "umas",
    "e", "ou", "mas", "por", "para", "com", "sem",
    "de", "do", "da", "dos", "das", "ao", "aos", "a", "ante",
    "sob", "sobre", "em", "entre", "desde", "ate", "que",
    "qual", "quais", "quanto", "quantos", "quanta", "quantas",
    "quando", "onde", "como", "porque", "se", "nao",
    "sim", "talvez", "eh", "sao", "serao", "seria", "fosse",
    "foi", "era", "sendo", "ter", "tendo", "tido", "tenha"
}


def extrair_palavras_chave(texto: str, min_length: int = 3) -> List[str]:
    """
    Extrai palavras-chave de um texto removendo stop words

    Args:
        texto: Texto para extrair palavras-chave
        min_length: Tamanho minimo da palavra

    Returns:
        Lista de palavras-chave
    """
    if not texto:
        return []

    # Converter para minusculas e dividir por palavras
    texto_limpo = re.sub(r'[^\w\s]', ' ', texto.lower())
    palavras = texto_limpo.split()

    # Filtrar stop words e palavras curtas
    palavras_chave = [
        p for p in palavras
        if p not in STOP_WORDS_PT and len(p) >= min_length
    ]

    # Remover duplicatas mantendo ordem
    return list(dict.fromkeys(palavras_chave))


async def calcular_score_relevancia(resultado: str, query: str) -> float:
    """
    Calcula score de relevancia baseado em matching de palavras-chave

    Args:
        resultado: Texto do resultado
        query: Query/pergunta original

    Returns:
        Score de relevancia entre 0.0 e 1.0
    """
    if not resultado or not query:
        return 0.0

    # Extrair palavras-chave da query
    palavras_query = extrair_palavras_chave(query)
    if not palavras_query:
        return 0.0

    # Converter resultado para minusculas para matching
    resultado_lower = resultado.lower()
    query_lower = query.lower()

    # Contar quantas palavras-chave aparecem no resultado
    matches = 0
    for palavra in palavras_query:
        if palavra in resultado_lower:
            matches += 1

    # Score base: proporcao de palavras encontradas (0-0.7)
    score_base = (matches / len(palavras_query)) * 0.7

    # Bonus se query completa aparece como phrase (0-0.2)
    bonus_phrase = 0.0
    if query_lower in resultado_lower:
        bonus_phrase = 0.2
    elif matches == len(palavras_query):
        # Se todas as palavras estao presentes mas nao em sequence, bonus muito pequeno
        bonus_phrase = 0.05

    score = score_base + bonus_phrase

    return min(1.0, score)


def calcular_score_ponderado(
    resultado: Dict[str, Any],
    query: str,
    score_relevancia: float,
    num_ocorrencias: int,
    confiabilidade_fonte: float
) -> float:
    """
    Calcula score ponderado usando 4 fatores

    Fatores:
    - score_relevancia: Quanto o resultado eh relevante para a query (40%)
    - num_ocorrencias: Quantas vezes apareceu em multiplas pesquisas (30%)
    - confiabilidade_fonte: Confiabilidade da fonte de dados (20%)
    - titulo_match: Se titulo contem palavras-chave (10%)

    Args:
        resultado: Dicionario com titulo, descricao, url, fonte
        query: Query para matching no titulo
        score_relevancia: Score de relevancia (0-1)
        num_ocorrencias: Numero de ocorrencias
        confiabilidade_fonte: Confiabilidade da fonte (0-1)

    Returns:
        Score ponderado entre 0.0 e 1.0
    """
    # Fator 1: Relevancia (40%)
    peso_relevancia = 0.40
    valor_relevancia = score_relevancia  # Ja entre 0-1

    # Fator 2: Ocorrencias (30%)
    # Normalizamos para 0-1: assumindo max 10 ocorrencias
    peso_ocorrencias = 0.30
    valor_ocorrencias = min(1.0, num_ocorrencias / 10.0)

    # Fator 3: Confiabilidade da fonte (20%)
    peso_fonte = 0.20
    valor_fonte = confiabilidade_fonte  # Ja entre 0-1

    # Fator 4: Match no titulo (10%)
    peso_titulo = 0.10
    titulo = resultado.get("titulo", "").lower()
    palavras_query = extrair_palavras_chave(query)
    if palavras_query:
        titulo_matches = sum(1 for p in palavras_query if p in titulo)
        valor_titulo = titulo_matches / len(palavras_query)
    else:
        valor_titulo = 0.0

    # Score ponderado
    score = (
        valor_relevancia * peso_relevancia +
        valor_ocorrencias * peso_ocorrencias +
        valor_fonte * peso_fonte +
        valor_titulo * peso_titulo
    )

    return min(1.0, max(0.0, score))


class Avaliador:
    """Avaliador de confianca para resultados de pesquisa"""

    def __init__(self):
        """Inicializa o avaliador com configuracoes padroes"""
        # Score de confiabilidade por fonte
        self.fontes_confiabilidade = {
            "perplexity": 0.95,  # Muito confiavel
            "jina": 0.90,        # Muito confiavel
            "deep_research": 0.85,  # Confiavel
            "google": 0.80,      # Confiavel
            "wikipedia": 0.75,   # Moderadamente confiavel
            "blog": 0.50,        # Pouco confiavel
            "social_media": 0.30,  # Muito pouco confiavel
            "unknown": 0.40      # Default para fontes desconhecidas
        }

        # Cache de avaliacoes (opcional, para evitar reavaliar)
        self.cache = {}

    def get_confiabilidade_fonte(self, nome_fonte: str) -> float:
        """
        Retorna score de confiabilidade para uma fonte

        Args:
            nome_fonte: Nome da fonte

        Returns:
            Score de confiabilidade entre 0.0 e 1.0
        """
        nome_fonte_lower = nome_fonte.lower()

        # Buscar match exato
        if nome_fonte_lower in self.fontes_confiabilidade:
            return self.fontes_confiabilidade[nome_fonte_lower]

        # Buscar match parcial
        for fonte, score in self.fontes_confiabilidade.items():
            if fonte in nome_fonte_lower:
                return score

        # Default para desconhecidas
        return self.fontes_confiabilidade["unknown"]

    async def avaliar(
        self,
        resultado: Dict[str, Any],
        query: str,
        num_ocorrencias: int = 1
    ) -> float:
        """
        Avalia um resultado individual e retorna confidence score

        Args:
            resultado: Dicionario com titulo, descricao, url, fonte
            query: Query para avaliar relevancia
            num_ocorrencias: Numero de vezes que apareceu

        Returns:
            Score entre 0.0 e 1.0
        """
        # Verificar cache
        cache_key = f"{resultado.get('url', '')}-{query}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Calcular score de relevancia
        resultado_texto = f"{resultado.get('titulo', '')} {resultado.get('descricao', '')}"
        score_relevancia = await calcular_score_relevancia(resultado_texto, query)

        # Get confiabilidade da fonte
        fonte = resultado.get("fonte", "unknown")
        confiabilidade = self.get_confiabilidade_fonte(fonte)

        # Calcular score ponderado
        score_final = calcular_score_ponderado(
            resultado=resultado,
            query=query,
            score_relevancia=score_relevancia,
            num_ocorrencias=num_ocorrencias,
            confiabilidade_fonte=confiabilidade
        )

        # Guardar em cache
        self.cache[cache_key] = score_final

        return score_final

    async def avaliar_batch(
        self,
        resultados: List[Dict[str, Any]],
        query: str
    ) -> List[float]:
        """
        Avalia multiplos resultados em paralelo

        Args:
            resultados: Lista de resultados
            query: Query para avaliar

        Returns:
            Lista de scores correspondentes aos resultados
        """
        tarefas = [
            self.avaliar(resultado, query)
            for resultado in resultados
        ]

        scores = await asyncio.gather(*tarefas)
        return scores

    def limpar_cache(self):
        """Limpa o cache de avaliacoes"""
        self.cache = {}
