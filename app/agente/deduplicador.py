# -*- coding: utf-8 -*-
"""
Deduplicador de resultados de pesquisa
Detecta e remove duplicados usando hash e similaridade (Jaccard e semântica)
"""
import hashlib
import re
import asyncio
from typing import Dict, List, Any, Set, Tuple, Optional
from app.config import settings


def normalizar_para_hash(texto: str) -> str:
    """
    Normaliza texto para calculo de hash
    Remove espacos extras, pontuacao e converte para minusculas

    Args:
        texto: Texto a normalizar

    Returns:
        Texto normalizado
    """
    if not texto:
        return ""

    # Converter para minusculas
    normalizado = texto.lower()

    # Remover pontuacao e caracteres especiais mantendo apenas palavras e espacos
    normalizado = re.sub(r'[^\w\s]', ' ', normalizado)

    # Remover espacos multiplos
    normalizado = re.sub(r'\s+', ' ', normalizado).strip()

    return normalizado


def calcular_hash_conteudo(conteudo: str) -> str:
    """
    Calcula hash SHA256 do conteudo

    Args:
        conteudo: Conteudo para hashear

    Returns:
        Hash SHA256 em hex
    """
    # Normalizar primeiro
    normalizado = normalizar_para_hash(conteudo)

    # Calcular SHA256
    hash_obj = hashlib.sha256(normalizado.encode('utf-8'))
    return hash_obj.hexdigest()


def calcular_similaridade(texto1: str, texto2: str) -> float:
    """
    Calcula similaridade entre dois textos usando Jaccard index
    (palavras comuns / palavras totais)

    Args:
        texto1: Primeiro texto
        texto2: Segundo texto

    Returns:
        Score entre 0.0 e 1.0
    """
    if not texto1 or not texto2:
        return 0.0 if texto1 != texto2 else 1.0

    # Extrair palavras
    palavras1 = set(normalizar_para_hash(texto1).split())
    palavras2 = set(normalizar_para_hash(texto2).split())

    if not palavras1 or not palavras2:
        return 0.0

    # Calcular Jaccard similarity
    intersecao = len(palavras1 & palavras2)
    uniao = len(palavras1 | palavras2)

    if uniao == 0:
        return 0.0

    return intersecao / uniao


class Deduplicador:
    """Deduplicador de resultados usando hash, similaridade Jaccard e semântica"""

    def __init__(self, threshold: float = 0.80, vector_store=None):
        """
        Inicializa o deduplicador

        Args:
            threshold: Threshold de similaridade Jaccard para considerar como duplicado (0-1)
            vector_store: Instância do VectorStore para deduplicação semântica (opcional)
        """
        self.threshold = threshold
        self.vector_store = vector_store

        # Set de hashes de conteudo ja vistos
        self.hashes_vistos: Dict[str, Dict[str, Any]] = {}

        # Contador de ocorrencias por hash (para boost de score)
        self.contador_hashes: Dict[str, int] = {}

        # Flag para usar deduplicacao semantica
        self.usar_semantica = vector_store is not None and settings.RAG_ENABLED

    def _extrair_conteudo_relevante(self, resultado: Dict[str, Any]) -> str:
        """
        Extrai conteudo relevante de um resultado para deduplicacao

        Args:
            resultado: Dicionario com titulo, descricao, etc

        Returns:
            String com conteudo concatenado
        """
        titulo = resultado.get("titulo", "")
        descricao = resultado.get("descricao", "")

        # Concatenar titulo e descricao para deduplicacao
        conteudo = f"{titulo} {descricao}"
        return conteudo

    async def _encontrar_duplicata_semantica(
        self,
        resultado: Dict[str, Any]
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        """
        Encontra uma possível duplicata usando similaridade semântica

        Args:
            resultado: Resultado para comparar

        Returns:
            Tupla (resultado_duplicado, similarity) ou None
        """
        if not self.usar_semantica or not self.vector_store:
            return None

        try:
            conteudo = self._extrair_conteudo_relevante(resultado)

            # Buscar similares no vector store
            similares = await self.vector_store.search_resultados(
                query=conteudo,
                n_results=3
            )

            if not similares:
                return None

            # Retornar o mais similar que ultrapassa threshold semântico
            for similar_meta, similarity in similares:
                if similarity >= settings.RAG_SIMILARITY_THRESHOLD_DEDUP:
                    # Criar resultado parcial do metadado para retorno
                    resultado_similar = {
                        "titulo": similar_meta.get("titulo", ""),
                        "descricao": similar_meta.get("descricao", ""),
                        "url": similar_meta.get("url", ""),
                        "fonte": similar_meta.get("fonte", ""),
                        "confidence_score": similar_meta.get("confidence_score", 0.5)
                    }
                    return (resultado_similar, similarity)

            return None

        except Exception as e:
            print(f"Erro na busca semântica de duplicatas: {e}")
            return None

    async def remover_duplicatas_semanticas(
        self,
        resultados: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicatas usando similaridade semântica

        Mantém o resultado de maior qualidade quando duplicatas são encontradas.

        Args:
            resultados: Lista de resultados

        Returns:
            Lista de resultados sem duplicatas semânticas
        """
        if not self.usar_semantica:
            return resultados

        resultados_unicos = []
        visitados = set()

        for resultado in resultados:
            url = resultado.get("url", "")

            # Skip se já processado
            if url in visitados:
                continue

            # Buscar duplicata semântica
            duplicata = await self._encontrar_duplicata_semantica(resultado)

            if duplicata:
                resultado_duplicado, similarity = duplicata

                # Manter o resultado de maior qualidade (maior score/confidence)
                score_atual = resultado.get("confidence_score", resultado.get("score", 0.5))
                score_duplicado = resultado_duplicado.get("confidence_score", resultado_duplicado.get("score", 0.5))

                if score_atual >= score_duplicado:
                    resultados_unicos.append(resultado)
                else:
                    resultados_unicos.append(resultado_duplicado)

                # Marcar ambas URLs como visitadas
                visitados.add(url)
                visitados.add(resultado_duplicado.get("url", ""))
            else:
                resultados_unicos.append(resultado)
                visitados.add(url)

        return resultados_unicos

    def eh_novo(self, resultado: Dict[str, Any]) -> bool:
        """
        Verifica se um resultado eh novo (nao eh duplicado)

        Args:
            resultado: Resultado para verificar

        Returns:
            True se eh novo, False se eh duplicado
        """
        conteudo = self._extrair_conteudo_relevante(resultado)
        hash_conteudo = calcular_hash_conteudo(conteudo)

        # Hash exato encontrado
        if hash_conteudo in self.hashes_vistos:
            return False

        # Verificar similaridade com outros hashes
        for hash_existente in self.hashes_vistos:
            resultado_existente = self.hashes_vistos[hash_existente]
            conteudo_existente = self._extrair_conteudo_relevante(resultado_existente)

            similaridade = calcular_similaridade(conteudo, conteudo_existente)

            if similaridade >= self.threshold:
                return False

        # Eh novo
        self.hashes_vistos[hash_conteudo] = resultado
        self.contador_hashes[hash_conteudo] = 1

        return True

    def processar(self, resultado: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa um resultado, incrementando score se for duplicado

        Args:
            resultado: Resultado para processar (copia sera retornada)

        Returns:
            Resultado processado (possivelmente com score incrementado)
        """
        resultado_copia = resultado.copy()

        conteudo = self._extrair_conteudo_relevante(resultado)
        hash_conteudo = calcular_hash_conteudo(conteudo)

        # Se ja existe hash exato
        if hash_conteudo in self.contador_hashes:
            # Incrementar contador
            self.contador_hashes[hash_conteudo] += 1

            # Incrementar score (5% por ocorrencia)
            score_atual = resultado_copia.get("score", 0.5)
            incremento = min(0.3, self.contador_hashes[hash_conteudo] * 0.05)
            resultado_copia["score"] = min(1.0, score_atual + incremento)

            return resultado_copia

        # Verificar similaridade
        for hash_existente in self.hashes_vistos:
            resultado_existente = self.hashes_vistos[hash_existente]
            conteudo_existente = self._extrair_conteudo_relevante(resultado_existente)

            similaridade = calcular_similaridade(conteudo, conteudo_existente)

            if similaridade >= self.threshold:
                # Duplicado similar encontrado
                self.contador_hashes[hash_existente] += 1

                # Incrementar score
                score_atual = resultado_copia.get("score", 0.5)
                incremento = min(0.3, self.contador_hashes[hash_existente] * 0.05)
                resultado_copia["score"] = min(1.0, score_atual + incremento)

                return resultado_copia

        # Eh novo, registrar
        self.hashes_vistos[hash_conteudo] = resultado_copia
        self.contador_hashes[hash_conteudo] = 1

        return resultado_copia

    def processar_batch(self, resultados: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processa lote de resultados, removendo duplicados e incrementando scores

        Args:
            resultados: Lista de resultados

        Returns:
            Lista de resultados processados (sem duplicados exatos)
        """
        resultados_processados = []
        hashes_no_batch = set()

        for resultado in resultados:
            conteudo = self._extrair_conteudo_relevante(resultado)
            hash_conteudo = calcular_hash_conteudo(conteudo)

            # Skip se ja vimos esse hash neste batch
            if hash_conteudo in hashes_no_batch:
                continue

            hashes_no_batch.add(hash_conteudo)

            # Processar resultado
            resultado_processado = self.processar(resultado)
            resultados_processados.append(resultado_processado)

        return resultados_processados

    def limpar(self):
        """Limpa o cache de hashes vistos"""
        self.hashes_vistos = {}
        self.contador_hashes = {}

    def get_estatisticas(self) -> Dict[str, Any]:
        """
        Retorna estatisticas de deduplicacao

        Returns:
            Dicionario com total de hashes, contadores, etc
        """
        return {
            "total_hashes_vistos": len(self.hashes_vistos),
            "total_ocorrencias": sum(self.contador_hashes.values()),
            "duplicados_detectados": sum(1 for c in self.contador_hashes.values() if c > 1),
            "threshold": self.threshold
        }
