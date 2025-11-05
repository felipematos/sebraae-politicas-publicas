# -*- coding: utf-8 -*-
"""
Avaliador de confianca para resultados de pesquisa
Calcula confidence scores usando multiplos fatores
"""
import re
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings


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


async def calcular_score_relevancia(
    resultado: str,
    query: str,
    resultado_traduzido: Optional[str] = None
) -> float:
    """
    Calcula score de relevancia baseado em matching de palavras-chave

    Para resultados em idiomas diferentes do português, usa a tradução
    para garantir comparação justa com a query em português.

    Args:
        resultado: Texto do resultado (idioma original)
        query: Query/pergunta original (em português)
        resultado_traduzido: Texto do resultado traduzido para português (opcional)

    Returns:
        Score de relevancia entre 0.0 e 1.0
    """
    if not resultado or not query:
        return 0.0

    # Se temos tradução, usar ela para calcular relevância
    # Isso garante que resultados em outros idiomas sejam avaliados de forma justa
    texto_para_avaliar = resultado_traduzido if resultado_traduzido else resultado

    # Extrair palavras-chave da query
    palavras_query = extrair_palavras_chave(query)
    if not palavras_query:
        return 0.0

    # Converter texto para minusculas para matching
    texto_lower = texto_para_avaliar.lower()
    query_lower = query.lower()

    # Contar quantas palavras-chave aparecem no texto
    matches = 0
    for palavra in palavras_query:
        if palavra in texto_lower:
            matches += 1

    # Score base: proporcao de palavras encontradas (0-0.8)
    # Usa escala 0-1 completa para refletir bem a relevancia
    score_base = (matches / len(palavras_query)) * 0.8

    # Bonus se query completa aparece como phrase (0-0.15)
    bonus_phrase = 0.0
    if query_lower in texto_lower:
        bonus_phrase = 0.15  # Muito bom: encontrou a query inteira
    elif matches == len(palavras_query):
        # Se todas as palavras estao presentes mas nao em sequence
        bonus_phrase = 0.10  # Bom: encontrou todas as palavras

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
    Calcula score ponderado melhorado com 4 fatores

    Fatores:
    - score_relevancia: Quanto o resultado eh relevante para a query (50%)
      Usa escala 0-1 completa para refletir melhor a relevancia
    - num_ocorrencias: Quantas vezes apareceu em multiplas pesquisas (20%)
      Incentiva resultados que aparecem em multiplas buscas
    - confiabilidade_fonte: Confiabilidade da fonte de dados (20%)
      Pondera pela fonte de onde veio o resultado
    - titulo_match: Se titulo contem palavras-chave (10%)
      Bonus se a query aparece no titulo

    Args:
        resultado: Dicionario com titulo, descricao, url, fonte
        query: Query para matching no titulo
        score_relevancia: Score de relevancia (0-1) - CORRIGIDO PARA USAR ESCALA COMPLETA
        num_ocorrencias: Numero de ocorrencias
        confiabilidade_fonte: Confiabilidade da fonte (0-1)

    Returns:
        Score ponderado entre 0.0 e 1.0
    """
    # Fator 1: Relevancia (50%) - AUMENTADO para refletir importancia
    # score_relevancia agora usa escala 0-1 completa
    peso_relevancia = 0.50
    valor_relevancia = min(1.0, score_relevancia)  # Ja entre 0-1

    # Fator 2: Ocorrencias (20%) - REDUZIDO pois já considerado em relevancia
    # Normalizamos para 0-1: max 5 ocorrencias = 100%
    peso_ocorrencias = 0.20
    valor_ocorrencias = min(1.0, num_ocorrencias / 5.0)

    # Fator 3: Confiabilidade da fonte (20%) - MANTIDO
    peso_fonte = 0.20
    valor_fonte = min(1.0, confiabilidade_fonte)  # Ja entre 0-1

    # Fator 4: Match no titulo (10%) - MANTIDO como bonus
    peso_titulo = 0.10
    titulo = resultado.get("titulo", "").lower()
    palavras_query = extrair_palavras_chave(query)
    if palavras_query:
        titulo_matches = sum(1 for p in palavras_query if p in titulo)
        valor_titulo = min(1.0, titulo_matches / len(palavras_query))
    else:
        valor_titulo = 0.0

    # Score ponderado com formula melhorada
    score = (
        valor_relevancia * peso_relevancia +
        valor_ocorrencias * peso_ocorrencias +
        valor_fonte * peso_fonte +
        valor_titulo * peso_titulo
    )

    return min(1.0, max(0.0, score))


class Avaliador:
    """Avaliador de confianca para resultados de pesquisa com suporte a RAG"""

    def __init__(self, vector_store=None):
        """
        Inicializa o avaliador com configuracoes padroes

        Args:
            vector_store: Instância do VectorStore para RAG (opcional)
        """
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

        # VectorStore para RAG (opcional)
        self.vector_store = vector_store
        self.rag_enabled = vector_store is not None and settings.RAG_ENABLED

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

    async def buscar_contexto_rag(
        self,
        resultado: Dict[str, Any],
        top_k: int = 3
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Busca resultados similares no histório usando vector store

        Args:
            resultado: Resultado atual para comparar
            top_k: Número de resultados similares a retornar

        Returns:
            Lista de (metadados_resultado_similar, similarity_score)
        """
        if not self.rag_enabled:
            return []

        try:
            # Preparar texto para busca
            texto_busca = f"{resultado.get('titulo', '')} {resultado.get('descricao', '')}"

            # Buscar no vector store
            similares = await self.vector_store.search_resultados(
                query=texto_busca,
                n_results=top_k
            )

            return similares

        except Exception as e:
            print(f"Erro buscando contexto RAG: {e}")
            return []

    async def _ajustar_score_com_rag(
        self,
        score_base: float,
        resultado: Dict[str, Any],
        top_k: int = 3
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Ajusta score baseado em contexto RAG histórico

        Lógica:
        - Se resultado muito similar de alta qualidade existe → boost de 0.1
        - Se resultado muito similar de baixa qualidade existe → redução de 0.15

        Args:
            score_base: Score calculado sem RAG
            resultado: Resultado para avaliar
            top_k: Número de resultados similares a considerar

        Returns:
            (score_ajustado, info_rag) - Tupla com score ajustado e informações RAG
        """
        info_rag = {
            "rag_aplicado": False,
            "similares_encontrados": 0,
            "ajuste_aplicado": 0.0,
            "motivo": "RAG desabilitado"
        }

        if not self.rag_enabled:
            return score_base, info_rag

        try:
            # Buscar similares
            similares = await self.buscar_contexto_rag(resultado, top_k)

            if not similares:
                info_rag["motivo"] = "Nenhum similar encontrado"
                return score_base, info_rag

            info_rag["similares_encontrados"] = len(similares)
            info_rag["rag_aplicado"] = True

            # Analisar similares encontrados
            score_ajustado = score_base
            ajuste = 0.0

            for similar_meta, similarity in similares:
                # Considerar apenas similares com alta similaridade
                if similarity < settings.RAG_SIMILARITY_THRESHOLD:
                    continue

                # Score anterior do similar (se disponível)
                score_anterior = similar_meta.get("confidence_score", 0.5)

                if score_anterior > 0.75:
                    # Resultado similar de alta qualidade → boost
                    ajuste += 0.1
                    info_rag["motivo"] = f"Boost por similar alta qualidade (sim={similarity:.2f})"

                elif score_anterior < 0.5:
                    # Resultado similar de baixa qualidade → redução
                    ajuste -= 0.15
                    info_rag["motivo"] = f"Redução por similar baixa qualidade (sim={similarity:.2f})"

            # Aplicar ajuste cumulativo (máx +0.2 ou -0.3)
            ajuste = max(-0.3, min(0.2, ajuste))
            score_ajustado = max(0.0, min(1.0, score_base + ajuste))

            info_rag["ajuste_aplicado"] = round(ajuste, 3)

            return score_ajustado, info_rag

        except Exception as e:
            print(f"Erro ajustando score com RAG: {e}")
            info_rag["motivo"] = f"Erro: {str(e)}"
            return score_base, info_rag

    async def avaliar(
        self,
        resultado: Dict[str, Any],
        query: str,
        num_ocorrencias: int = 1,
        usar_rag: bool = False
    ) -> float:
        """
        Avalia um resultado individual e retorna confidence score

        Para resultados em idiomas diferentes do português, utiliza as traduções
        armazenadas (titulo_pt, descricao_pt) para garantir comparação justa.

        Args:
            resultado: Dicionario com titulo, descricao, url, fonte
                      Pode conter titulo_pt e descricao_pt para resultados traduzidos
            query: Query para avaliar relevancia (em português)
            num_ocorrencias: Numero de vezes que apareceu
            usar_rag: Se deve usar RAG para ajustar score

        Returns:
            Score entre 0.0 e 1.0
        """
        # Verificar cache
        cache_key = f"{resultado.get('url', '')}-{query}-rag={usar_rag}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Preparar texto para avaliação
        # Se resultado tem tradução (titulo_pt, descricao_pt), usar ela
        idioma = resultado.get('idioma', 'pt')

        if idioma != 'pt':
            # Resultado em outro idioma: usar tradução se disponível
            titulo_pt = resultado.get('titulo_pt', '')
            descricao_pt = resultado.get('descricao_pt', '')

            # Se tem traduções, usá-las; senão usar original
            if titulo_pt or descricao_pt:
                resultado_traduzido = f"{titulo_pt} {descricao_pt}"
            else:
                resultado_traduzido = None
        else:
            # Resultado já em português: não precisa tradução
            resultado_traduzido = None

        # Texto original (sempre necessário como fallback)
        resultado_texto = f"{resultado.get('titulo', '')} {resultado.get('descricao', '')}"

        # Calcular score de relevancia (usa tradução se disponível)
        score_relevancia = await calcular_score_relevancia(
            resultado_texto,
            query,
            resultado_traduzido=resultado_traduzido
        )

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

        # Aplicar ajuste com RAG se solicitado
        if usar_rag:
            score_final, _ = await self._ajustar_score_com_rag(score_final, resultado)

        # Guardar em cache
        self.cache[cache_key] = score_final

        return score_final

    async def avaliar_com_rag(
        self,
        resultado: Dict[str, Any],
        query: str,
        num_ocorrencias: int = 1
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Avalia um resultado usando contexto RAG

        Args:
            resultado: Dicionario com titulo, descricao, url, fonte
            query: Query para avaliar relevancia
            num_ocorrencias: Numero de vezes que apareceu

        Returns:
            Tupla (score_final, info_rag)
        """
        # Calcular score base
        score_base = await self.avaliar(resultado, query, num_ocorrencias, usar_rag=False)

        # Ajustar com RAG
        score_ajustado, info_rag = await self._ajustar_score_com_rag(score_base, resultado)

        return score_ajustado, info_rag

    async def avaliar_batch(
        self,
        resultados: List[Dict[str, Any]],
        query: str,
        usar_rag: bool = False
    ) -> List[float]:
        """
        Avalia multiplos resultados em paralelo

        Args:
            resultados: Lista de resultados
            query: Query para avaliar
            usar_rag: Se deve usar RAG para ajustar scores

        Returns:
            Lista de scores correspondentes aos resultados
        """
        tarefas = [
            self.avaliar(resultado, query, usar_rag=usar_rag)
            for resultado in resultados
        ]

        scores = await asyncio.gather(*tarefas)
        return scores

    async def avaliar_batch_com_rag(
        self,
        resultados: List[Dict[str, Any]],
        query: str
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """
        Avalia multiplos resultados em paralelo usando RAG

        Args:
            resultados: Lista de resultados
            query: Query para avaliar

        Returns:
            Lista de tuplas (score, info_rag)
        """
        tarefas = [
            self.avaliar_com_rag(resultado, query)
            for resultado in resultados
        ]

        resultados_rag = await asyncio.gather(*tarefas)
        return resultados_rag

    def limpar_cache(self):
        """Limpa o cache de avaliacoes"""
        self.cache = {}

    async def avaliar_qualidade_conjunto(
        self,
        resultados: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """
        Avalia a qualidade geral de um conjunto de resultados
        Usa heurísticas inteligentes para decidir se precisa continuar buscando

        Args:
            resultados: Lista de resultados acumulados
            query: Query da pesquisa

        Returns:
            Dicionário com:
            - qualidade_geral: Score 0-1 da qualidade geral
            - confianca: Nível de confiança nos resultados
            - diversidade: Score de diversidade das fontes
            - recomendacao: "parar", "continuar" ou "talvez"
            - motivo: Explicação da recomendação
        """
        if not resultados:
            return {
                "qualidade_geral": 0.0,
                "confianca": 0.0,
                "diversidade": 0.0,
                "recomendacao": "continuar",
                "motivo": "Nenhum resultado encontrado ainda"
            }

        # Avaliar todos os resultados
        scores = await self.avaliar_batch(resultados, query)

        # Calcular métricas
        qualidade_geral = sum(scores) / len(scores) if scores else 0.0
        melhor_score = max(scores) if scores else 0.0
        piores_scores = sorted(scores)[:max(1, len(scores)//3)]
        media_piores = sum(piores_scores) / len(piores_scores)

        # Diversidade de fontes
        fontes = [r.get("fonte", "unknown") for r in resultados]
        fontes_unicas = len(set(fontes))
        diversidade = min(1.0, fontes_unicas / 5.0)  # Max 5 fontes é 100% diversidade

        # Confiança: baseada em qualidade geral + consistência
        # Se todos os scores são altos e altos, alta confiança
        # Se há muito spread, baixa confiança
        score_spread = max(scores) - min(scores) if scores else 0.0
        consistencia = 1.0 - min(1.0, score_spread)  # Menos spread = mais consistência
        confianca = (qualidade_geral * 0.7) + (consistencia * 0.3)

        # Lógica inteligente para decisão
        motivos = []
        recomendacao = "continuar"

        if qualidade_geral >= 0.75:
            motivos.append("Qualidade geral excelente")
            if confianca >= 0.70 and diversidade >= 0.6:
                recomendacao = "parar"
                motivos.append("Confiança e diversidade adequadas")
            else:
                recomendacao = "talvez"
                if diversidade < 0.6:
                    motivos.append("Diversidade de fontes ainda limitada")
        elif qualidade_geral >= 0.60:
            motivos.append("Qualidade razoável")
            if confianca >= 0.75 and diversidade >= 0.8:
                recomendacao = "talvez"
                motivos.append("Resultados consistentes mas qualidade poderia melhorar")
            else:
                recomendacao = "continuar"
        else:
            motivos.append(f"Qualidade baixa ({qualidade_geral:.2f})")
            recomendacao = "continuar"

        # Verificação de redundância: se muitos resultados similares, pode parar antes
        duplicatas = len(resultados) - len(set(r.get("url", "") for r in resultados))
        if duplicatas > len(resultados) * 0.5:
            motivos.append("Alta redundância entre resultados")
            if recomendacao == "continuar" and qualidade_geral >= 0.50:
                recomendacao = "talvez"

        motivo_final = " | ".join(motivos) if motivos else "Avaliação padrão"

        return {
            "qualidade_geral": round(qualidade_geral, 3),
            "confianca": round(confianca, 3),
            "diversidade": round(diversidade, 3),
            "consistencia": round(consistencia, 3),
            "num_resultados": len(resultados),
            "fontes_unicas": fontes_unicas,
            "recomendacao": recomendacao,
            "motivo": motivo_final,
            "melhor_score": round(melhor_score, 3),
            "media_piores": round(media_piores, 3)
        }
