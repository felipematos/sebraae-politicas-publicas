#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de migração: Popula o banco vetorial com dados existentes
Indexa: falhas de mercado, resultados e queries históricas
"""
import asyncio
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

# Adicionar app ao path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings, get_database_path, get_chroma_path
from app.vector.embeddings import EmbeddingClient
from app.vector.vector_store import VectorStore


class MigrationWorker:
    """Worker para migração de dados para VectorStore"""

    def __init__(self):
        """Inicializa worker"""
        self.db_path = get_database_path()
        self.chroma_path = get_chroma_path()

        # Validar API key
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY não configurada no .env")

        # Inicializar clientes
        self.embedding_client = EmbeddingClient(
            api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL
        )

        self.vector_store = VectorStore(
            persist_path=self.chroma_path,
            embedding_client=self.embedding_client
        )

    def _get_db_connection(self) -> sqlite3.Connection:
        """Retorna conexão com banco de dados"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _fetch_falhas(self) -> List[Dict[str, Any]]:
        """Retorna todas as falhas do banco"""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, titulo, pilar, descricao
            FROM falhas_mercado
            ORDER BY id
        """)

        falhas = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return falhas

    def _fetch_resultados(self) -> List[Dict[str, Any]]:
        """Retorna todos os resultados do banco"""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, falha_id, titulo, descricao, fonte_url,
                fonte_tipo, idioma, confidence_score, ferramenta_origem
            FROM resultados
            ORDER BY falha_id, id
        """)

        resultados = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return resultados

    def _fetch_queries(self) -> List[Dict[str, Any]]:
        """Retorna todas as queries históricas"""
        conn = self._get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, falha_id, query, idioma
            FROM fila_pesquisas
            WHERE status = 'completa'
            ORDER BY falha_id, id
        """)

        queries = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return queries

    async def migrate_falhas(self) -> int:
        """Migra falhas de mercado para VectorStore"""
        print("\n[MIGRAÇÃO] Indexando falhas de mercado...")
        falhas = self._fetch_falhas()

        count = 0
        for falha in falhas:
            try:
                sucesso = await self.vector_store.add_falha(
                    falha_id=falha['id'],
                    titulo=falha['titulo'],
                    pilar=falha['pilar'],
                    descricao=falha['descricao']
                )

                if sucesso:
                    count += 1
                    if count % 10 == 0:
                        print(f"  ✓ {count}/{len(falhas)} falhas indexadas")

            except Exception as e:
                print(f"  ✗ Erro indexando falha {falha['id']}: {e}")

        print(f"✓ {count}/{len(falhas)} falhas indexadas com sucesso")
        return count

    async def migrate_resultados(self, batch_size: int = 50) -> int:
        """Migra resultados de pesquisa para VectorStore"""
        print("\n[MIGRAÇÃO] Indexando resultados de pesquisa...")
        resultados = self._fetch_resultados()

        count = 0
        total = len(resultados)

        for i, resultado in enumerate(resultados):
            try:
                # Preparar dados
                resultado_dict = {
                    'titulo': resultado['titulo'],
                    'descricao': resultado['descricao'],
                    'url': resultado['fonte_url'],
                    'fonte': resultado['fonte_tipo'],
                    'idioma': resultado['idioma'],
                    'confidence_score': resultado['confidence_score']
                }

                sucesso = await self.vector_store.add_resultado(
                    resultado=resultado_dict,
                    falha_id=resultado['falha_id']
                )

                if sucesso:
                    count += 1

                if (i + 1) % batch_size == 0:
                    print(f"  ✓ {count}/{total} resultados indexados")

            except Exception as e:
                print(f"  ✗ Erro indexando resultado {resultado['id']}: {e}")

        print(f"✓ {count}/{total} resultados indexados com sucesso")
        return count

    async def migrate_queries(self) -> int:
        """Migra queries de pesquisa históricas para VectorStore"""
        print("\n[MIGRAÇÃO] Indexando queries históricas...")
        queries = self._fetch_queries()

        count = 0
        for query in queries:
            try:
                sucesso = await self.vector_store.add_query(
                    query=query['query'],
                    falha_id=query['falha_id'],
                    idioma=query['idioma']
                )

                if sucesso:
                    count += 1
                    if count % 50 == 0:
                        print(f"  ✓ {count}/{len(queries)} queries indexadas")

            except Exception as e:
                print(f"  ✗ Erro indexando query {query['id']}: {e}")

        print(f"✓ {count}/{len(queries)} queries indexadas com sucesso")
        return count

    async def run_full_migration(self) -> Dict[str, int]:
        """Executa migração completa"""
        print("=" * 70)
        print("MIGRAÇÃO PARA BANCO VETORIAL - ChromaDB + OpenAI Embeddings")
        print("=" * 70)

        print(f"\nCaminho da origem: {self.db_path}")
        print(f"Caminho de destino: {self.chroma_path}")
        print(f"Modelo de embeddings: {settings.EMBEDDING_MODEL}")

        try:
            # Migrar dados
            falhas_count = await self.migrate_falhas()
            resultados_count = await self.migrate_resultados()
            queries_count = await self.migrate_queries()

            # Exibir estatísticas
            stats = self.vector_store.get_stats()

            print("\n" + "=" * 70)
            print("RESULTADO DA MIGRAÇÃO")
            print("=" * 70)
            print(f"✓ Falhas indexadas: {stats['falhas_count']}")
            print(f"✓ Resultados indexados: {stats['resultados_count']}")
            print(f"✓ Queries indexadas: {stats['queries_count']}")
            print(f"✓ Total de documentos: {sum([stats['falhas_count'], stats['resultados_count'], stats['queries_count']])}")
            print(f"\nCache de embeddings:")
            print(f"  - Textos em cache: {stats['embedding_cache_stats']['cached_texts']}")
            print(f"  - Tamanho do cache: {stats['embedding_cache_stats']['cache_size_mb']:.2f} MB")
            print("=" * 70)

            return {
                "falhas": falhas_count,
                "resultados": resultados_count,
                "queries": queries_count
            }

        except Exception as e:
            print(f"\n✗ ERRO na migração: {e}")
            raise


async def main():
    """Função principal"""
    worker = MigrationWorker()

    try:
        await worker.run_full_migration()
        print("\n✓ Migração concluída com sucesso!")

    except Exception as e:
        print(f"\n✗ Migração falhou: {e}")
        exit(1)

    # Cleanup
    await worker.vector_store.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
