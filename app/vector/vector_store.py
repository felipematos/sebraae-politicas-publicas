# -*- coding: utf-8 -*-
"""
Cliente de armazenamento vetorial em-memória para busca semântica
Implementação leve e simples sem dependências externas como ChromaDB
"""
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from app.vector.embeddings import EmbeddingClient


class SimpleVectorCollection:
    """Coleção simples de vetores armazenados em memória"""

    def __init__(self, name: str):
        """Inicializa uma coleção"""
        self.name = name
        self.documents = []  # Lista de {id, embedding, metadata, document}
        self.metadata_dict = {}  # Para busca rápida por ID

    def add(self, ids: List[str], embeddings: List[List[float]],
            metadatas: List[Dict], documents: List[str]):
        """Adiciona documentos à coleção"""
        for doc_id, embedding, metadata, document in zip(ids, embeddings, metadatas, documents):
            self.documents.append({
                "id": doc_id,
                "embedding": embedding,
                "metadata": metadata,
                "document": document
            })
            self.metadata_dict[doc_id] = metadata

    def query(self, query_embeddings: List[List[float]], n_results: int = 5,
              include: List[str] = None) -> Dict:
        """Busca documentos similares usando distância euclidiana"""
        if not self.documents:
            return {"metadatas": [[]], "distances": [[]], "documents": [[]], "embeddings": [[]]}

        import math

        query_embedding = query_embeddings[0]
        similarities = []

        for doc in self.documents:
            # Calcular distância euclidiana
            dist = 0
            for i, (q, d) in enumerate(zip(query_embedding, doc["embedding"])):
                dist += (q - d) ** 2
            dist = math.sqrt(dist)
            similarities.append((doc, dist))

        # Ordenar por distância (menor = mais similar)
        similarities.sort(key=lambda x: x[1])
        top_results = similarities[:n_results]

        metadatas = [[doc["metadata"] for doc, _ in top_results]]
        distances = [[dist for _, dist in top_results]]
        documents = [[doc["document"] for doc, _ in top_results]]
        embeddings = [[doc["embedding"] for doc, _ in top_results]] if include and "embeddings" in include else [[]]

        return {
            "metadatas": metadatas,
            "distances": distances,
            "documents": documents,
            "embeddings": embeddings
        }

    def get(self, where: Dict = None) -> Dict:
        """Retorna documentos filtrados por metadados"""
        if not where:
            return {"metadatas": [doc["metadata"] for doc in self.documents]}

        # Implementar filtro simples para falha_id
        filtered = []
        for doc in self.documents:
            if "falha_id" in where and "$eq" in where["falha_id"]:
                if doc["metadata"].get("falha_id") == where["falha_id"]["$eq"]:
                    filtered.append(doc["metadata"])

        return {"metadatas": filtered}

    def count(self) -> int:
        """Retorna número de documentos"""
        return len(self.documents)


class VectorStore:
    """Gerenciador de banco de dados vetorial simples e leve"""

    def __init__(
        self,
        persist_path: Path,
        embedding_client: EmbeddingClient
    ):
        """
        Inicializa VectorStore

        Args:
            persist_path: Caminho para salvar dados (persistência futura)
            embedding_client: Cliente de embeddings
        """
        self.persist_path = persist_path
        self.embedding_client = embedding_client

        # Criar diretório se não existir
        self.persist_path.mkdir(parents=True, exist_ok=True)

        # Inicializar coleções em memória
        self.resultados_collection = SimpleVectorCollection("resultados")
        self.falhas_collection = SimpleVectorCollection("falhas")
        self.queries_collection = SimpleVectorCollection("queries")
        self.documents_collection = SimpleVectorCollection("documents")  # Para documentos RAG

    async def add_texts(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> bool:
        """
        Adiciona textos/documentos ao banco vetorial (para RAG)

        Args:
            texts: Lista de textos a adicionar
            metadatas: Lista de dicionários com metadados
            ids: Lista de IDs únicos para os documentos

        Returns:
            True se todos foram adicionados com sucesso
        """
        try:
            # Gerar embeddings para todos os textos
            embeddings = []
            for text in texts:
                embedding = await self.embedding_client.embed_text(text)
                embeddings.append(embedding)

            # Adicionar à coleção
            self.documents_collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=texts
            )

            return True

        except Exception as e:
            print(f"Erro ao adicionar textos ao VectorStore: {e}")
            return False

    async def add_resultado(
        self,
        resultado: Dict[str, Any],
        falha_id: int
    ) -> bool:
        """
        Adiciona um resultado ao banco vetorial

        Args:
            resultado: Dicionário com titulo, descricao, url, fonte, etc
            falha_id: ID da falha associada

        Returns:
            True se adicionado com sucesso
        """
        try:
            # Gerar ID único baseado em URL
            doc_id = f"resultado_{resultado.get('url', '').replace('/', '_')[:50]}"

            # Preparar texto para embedding
            texto = f"{resultado.get('titulo', '')} {resultado.get('descricao', '')}"

            # Gerar embedding
            embedding = await self.embedding_client.embed_text(texto)

            # Adicionar à coleção
            self.resultados_collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[{
                    "falha_id": falha_id,
                    "titulo": resultado.get('titulo', ''),
                    "url": resultado.get('url', ''),
                    "fonte": resultado.get('fonte', 'unknown'),
                    "idioma": resultado.get('idioma', 'pt'),
                    "confidence_score": resultado.get('confidence_score', 0.5)
                }],
                documents=[texto]
            )

            return True

        except Exception as e:
            print(f"Erro adicionando resultado ao VectorStore: {e}")
            return False

    async def add_falha(
        self,
        falha_id: int,
        titulo: str,
        pilar: str,
        descricao: str
    ) -> bool:
        """
        Adiciona uma falha de mercado ao banco vetorial

        Args:
            falha_id: ID da falha
            titulo: Título da falha
            pilar: Pilar (ex: "6. Regulação")
            descricao: Descrição detalhada

        Returns:
            True se adicionado com sucesso
        """
        try:
            doc_id = f"falha_{falha_id}"

            # Preparar texto para embedding
            texto = f"{titulo} {pilar} {descricao}"

            # Gerar embedding
            embedding = await self.embedding_client.embed_text(texto)

            # Adicionar à coleção
            self.falhas_collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[{
                    "falha_id": falha_id,
                    "titulo": titulo,
                    "pilar": pilar
                }],
                documents=[texto]
            )

            return True

        except Exception as e:
            print(f"Erro adicionando falha ao VectorStore: {e}")
            return False

    async def add_query(
        self,
        query: str,
        falha_id: int,
        idioma: str = "pt"
    ) -> bool:
        """
        Adiciona uma query de pesquisa ao banco vetorial

        Args:
            query: Texto da query
            falha_id: ID da falha
            idioma: Idioma da query

        Returns:
            True se adicionado com sucesso
        """
        try:
            doc_id = f"query_{falha_id}_{hash(query)}"

            # Gerar embedding da query
            embedding = await self.embedding_client.embed_text(query)

            # Adicionar à coleção
            self.queries_collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[{
                    "falha_id": falha_id,
                    "idioma": idioma,
                    "query_length": len(query)
                }],
                documents=[query]
            )

            return True

        except Exception as e:
            print(f"Erro adicionando query ao VectorStore: {e}")
            return False

    async def search_resultados(
        self,
        query: str,
        n_results: int = 5
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Busca resultados similares a uma query

        Args:
            query: Query para buscar
            n_results: Número de resultados a retornar

        Returns:
            Lista de (metadados, similaridade)
        """
        try:
            # Gerar embedding da query
            embedding = await self.embedding_client.embed_text(query)

            # Buscar na coleção
            results = self.resultados_collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                include=["embeddings", "metadatas", "documents", "distances"]
            )

            # Converter distâncias para similaridade (1 - distância normalizada)
            similaridades = []
            if results['metadatas'] and results['metadatas'][0]:
                for i, metadata in enumerate(results['metadatas'][0]):
                    distance = results['distances'][0][i]
                    # Normalizar distância euclidiana para escala 0-1
                    # Usar: similarity = 1 / (1 + distance)
                    similarity = 1 / (1 + distance)

                    similaridades.append((metadata, similarity))

            return similaridades

        except Exception as e:
            print(f"Erro buscando resultados no VectorStore: {e}")
            return []

    async def search_falhas(
        self,
        query: str,
        n_results: int = 5
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Busca falhas similares a uma query

        Args:
            query: Query para buscar
            n_results: Número de resultados a retornar

        Returns:
            Lista de (metadados, similaridade)
        """
        try:
            # Gerar embedding da query
            embedding = await self.embedding_client.embed_text(query)

            # Buscar na coleção
            results = self.falhas_collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                include=["metadatas", "distances"]
            )

            # Converter distâncias para similaridade
            similaridades = []
            if results['metadatas'] and results['metadatas'][0]:
                for i, metadata in enumerate(results['metadatas'][0]):
                    distance = results['distances'][0][i]
                    similarity = 1 / (1 + distance)

                    similaridades.append((metadata, similarity))

            return similaridades

        except Exception as e:
            print(f"Erro buscando falhas no VectorStore: {e}")
            return []

    async def find_similar_queries(
        self,
        query: str,
        n_results: int = 3
    ) -> List[Tuple[str, Dict[str, Any], float]]:
        """
        Encontra queries similares já executadas

        Args:
            query: Query para comparar
            n_results: Número de resultados

        Returns:
            Lista de (query_text, metadados, similaridade)
        """
        try:
            # Gerar embedding da query
            embedding = await self.embedding_client.embed_text(query)

            # Buscar na coleção
            results = self.queries_collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                include=["metadatas", "documents", "distances"]
            )

            # Processar resultados
            similares = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'][0] else {}
                    distance = results['distances'][0][i]
                    similarity = 1 / (1 + distance)

                    similares.append((doc, metadata, similarity))

            return similares

        except Exception as e:
            print(f"Erro encontrando queries similares: {e}")
            return []

    async def get_by_falha_id(
        self,
        collection_name: str,
        falha_id: int
    ) -> List[Dict[str, Any]]:
        """
        Retorna todos os documentos de uma falha em uma coleção

        Args:
            collection_name: "resultados", "falhas" ou "queries"
            falha_id: ID da falha

        Returns:
            Lista de metadados
        """
        try:
            collection = self._get_collection(collection_name)

            # Buscar documentos filtrados por falha_id
            results = collection.get(
                where={"falha_id": {"$eq": falha_id}}
            )

            return results['metadatas'] if results['metadatas'] else []

        except Exception as e:
            print(f"Erro buscando por falha_id: {e}")
            return []

    def _get_collection(self, collection_name: str) -> SimpleVectorCollection:
        """
        Retorna a coleção solicitada

        Args:
            collection_name: Nome da coleção

        Returns:
            Coleção de vetores
        """
        if collection_name == "resultados":
            return self.resultados_collection
        elif collection_name == "falhas":
            return self.falhas_collection
        elif collection_name == "queries":
            return self.queries_collection
        elif collection_name == "documents":
            return self.documents_collection
        else:
            raise ValueError(f"Coleção desconhecida: {collection_name}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do banco vetorial

        Returns:
            Dicionário com contagens
        """
        return {
            "resultados_count": self.resultados_collection.count(),
            "falhas_count": self.falhas_collection.count(),
            "queries_count": self.queries_collection.count(),
            "documents_count": self.documents_collection.count(),
            "embedding_cache_stats": self.embedding_client.get_cache_stats()
        }

    async def cleanup(self):
        """Limpa caches e recursos"""
        self.embedding_client.clear_cache()


# Singleton global
_vector_store: Optional[VectorStore] = None


async def get_vector_store(
    persist_path: Optional[Path] = None,
    embedding_client: Optional[EmbeddingClient] = None
) -> VectorStore:
    """
    Retorna instância global do VectorStore

    Args:
        persist_path: Caminho para dados (opcional)
        embedding_client: Cliente de embeddings (opcional)

    Returns:
        VectorStore
    """
    global _vector_store

    if _vector_store is None:
        if persist_path is None or embedding_client is None:
            raise ValueError("Deve fornecer persist_path e embedding_client na primeira inicialização")

        _vector_store = VectorStore(persist_path, embedding_client)

    return _vector_store
