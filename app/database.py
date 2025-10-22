# -*- coding: utf-8 -*-
"""
Gerenciador de conexao e operacoes com banco de dados SQLite
"""
import sqlite3
import aiosqlite
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.config import get_database_path, settings


class Database:
    """Classe para gerenciar conexoes e operacoes no SQLite"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_database_path()

    @asynccontextmanager
    async def get_connection(self):
        """Context manager para conexoes assincronas"""
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row  # Retornar dicts ao inves de tuplas
        try:
            yield conn
        finally:
            await conn.close()

    async def execute(self, query: str, params: tuple = ()) -> None:
        """Executa uma query (INSERT, UPDATE, DELETE)"""
        async with self.get_connection() as conn:
            await conn.execute(query, params)
            await conn.commit()

    async def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Executa multiplas queries (batch insert)"""
        async with self.get_connection() as conn:
            await conn.executemany(query, params_list)
            await conn.commit()

    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Retorna um unico registro"""
        async with self.get_connection() as conn:
            async with conn.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Retorna todos os registros"""
        async with self.get_connection() as conn:
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def init_tables(self):
        """Cria as novas tabelas necessarias para o sistema"""

        create_tables_sql = """
        -- Tabela de resultados de pesquisa
        CREATE TABLE IF NOT EXISTS resultados_pesquisa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            falha_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT,
            fonte_url TEXT NOT NULL,
            fonte_tipo TEXT,
            pais_origem TEXT,
            idioma TEXT,
            confidence_score REAL DEFAULT 0.5,
            num_ocorrencias INTEGER DEFAULT 1,
            ferramenta_origem TEXT,
            hash_conteudo TEXT UNIQUE,
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
            atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (falha_id) REFERENCES falhas_mercado(id)
        );

        -- Tabela de historico de pesquisas
        CREATE TABLE IF NOT EXISTS historico_pesquisas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            falha_id INTEGER NOT NULL,
            query TEXT NOT NULL,
            idioma TEXT NOT NULL,
            ferramenta TEXT NOT NULL,
            status TEXT DEFAULT 'pendente',
            resultados_encontrados INTEGER DEFAULT 0,
            erro_mensagem TEXT,
            tempo_execucao REAL,
            executado_em DATETIME,
            FOREIGN KEY (falha_id) REFERENCES falhas_mercado(id)
        );

        -- Tabela de fila de pesquisas
        CREATE TABLE IF NOT EXISTS fila_pesquisas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            falha_id INTEGER NOT NULL,
            query TEXT NOT NULL,
            idioma TEXT NOT NULL,
            ferramenta TEXT NOT NULL,
            prioridade INTEGER DEFAULT 0,
            tentativas INTEGER DEFAULT 0,
            max_tentativas INTEGER DEFAULT 3,
            status TEXT DEFAULT 'pendente',
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (falha_id) REFERENCES falhas_mercado(id)
        );

        -- Indices para performance
        CREATE INDEX IF NOT EXISTS idx_resultados_falha
            ON resultados_pesquisa(falha_id);

        CREATE INDEX IF NOT EXISTS idx_resultados_score
            ON resultados_pesquisa(confidence_score DESC);

        CREATE INDEX IF NOT EXISTS idx_historico_falha
            ON historico_pesquisas(falha_id);

        CREATE INDEX IF NOT EXISTS idx_fila_status
            ON fila_pesquisas(status, prioridade DESC);
        """

        async with self.get_connection() as conn:
            await conn.executescript(create_tables_sql)
            await conn.commit()

        print("Tabelas criadas/verificadas com sucesso!")


# Instancia global do banco de dados
db = Database()


# Funcoes auxiliares para operacoes comuns

async def get_falhas_mercado() -> List[Dict[str, Any]]:
    """Retorna todas as falhas de mercado"""
    return await db.fetch_all("SELECT * FROM falhas_mercado ORDER BY id")


async def get_falha_by_id(falha_id: int) -> Optional[Dict[str, Any]]:
    """Retorna uma falha especifica por ID"""
    return await db.fetch_one(
        "SELECT * FROM falhas_mercado WHERE id = ?",
        (falha_id,)
    )


async def get_resultados_by_falha(falha_id: int) -> List[Dict[str, Any]]:
    """Retorna todos os resultados de uma falha"""
    return await db.fetch_all(
        """
        SELECT * FROM resultados_pesquisa
        WHERE falha_id = ?
        ORDER BY confidence_score DESC, atualizado_em DESC
        """,
        (falha_id,)
    )


async def insert_resultado(resultado: Dict[str, Any]) -> int:
    """Insere um novo resultado de pesquisa"""
    query = """
    INSERT INTO resultados_pesquisa (
        falha_id, titulo, descricao, fonte_url, fonte_tipo,
        pais_origem, idioma, confidence_score, ferramenta_origem,
        hash_conteudo
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    async with db.get_connection() as conn:
        cursor = await conn.execute(query, (
            resultado['falha_id'],
            resultado['titulo'],
            resultado.get('descricao'),
            resultado['fonte_url'],
            resultado.get('fonte_tipo'),
            resultado.get('pais_origem'),
            resultado['idioma'],
            resultado['confidence_score'],
            resultado['ferramenta_origem'],
            resultado['hash_conteudo']
        ))
        await conn.commit()
        return cursor.lastrowid


async def update_resultado_score(resultado_id: int, novo_score: float) -> None:
    """Atualiza o confidence score de um resultado"""
    await db.execute(
        """
        UPDATE resultados_pesquisa
        SET confidence_score = ?,
            atualizado_em = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (novo_score, resultado_id)
    )


async def delete_resultado(resultado_id: int) -> None:
    """Deleta um resultado"""
    await db.execute(
        "DELETE FROM resultados_pesquisa WHERE id = ?",
        (resultado_id,)
    )


async def get_estatisticas_gerais() -> Dict[str, Any]:
    """Retorna estatisticas gerais do sistema"""
    stats = {}

    # Total de falhas
    result = await db.fetch_one("SELECT COUNT(*) as total FROM falhas_mercado")
    stats['total_falhas'] = result['total']

    # Total de resultados
    result = await db.fetch_one("SELECT COUNT(*) as total FROM resultados_pesquisa")
    stats['total_resultados'] = result['total']

    # Total de pesquisas executadas
    result = await db.fetch_one(
        "SELECT COUNT(*) as total FROM historico_pesquisas WHERE status = 'concluido'"
    )
    stats['pesquisas_concluidas'] = result['total']

    # Pesquisas pendentes
    result = await db.fetch_one(
        "SELECT COUNT(*) as total FROM fila_pesquisas WHERE status = 'pendente'"
    )
    stats['pesquisas_pendentes'] = result['total']

    # Media de confidence score
    result = await db.fetch_one(
        "SELECT AVG(confidence_score) as media FROM resultados_pesquisa"
    )
    stats['confidence_medio'] = round(result['media'], 2) if result['media'] else 0.0

    return stats


async def get_estatisticas_falha(falha_id: int) -> Dict[str, Any]:
    """Retorna estatisticas de uma falha especifica"""
    stats = {}

    # Total de resultados
    result = await db.fetch_one(
        "SELECT COUNT(*) as total FROM resultados_pesquisa WHERE falha_id = ?",
        (falha_id,)
    )
    stats['total_resultados'] = result['total']

    # Media de confidence
    result = await db.fetch_one(
        "SELECT AVG(confidence_score) as media FROM resultados_pesquisa WHERE falha_id = ?",
        (falha_id,)
    )
    stats['confidence_medio'] = round(result['media'], 2) if result['media'] else 0.0

    # Distribuicao por pais
    paises = await db.fetch_all(
        """
        SELECT pais_origem, COUNT(*) as total
        FROM resultados_pesquisa
        WHERE falha_id = ? AND pais_origem IS NOT NULL
        GROUP BY pais_origem
        ORDER BY total DESC
        LIMIT 10
        """,
        (falha_id,)
    )
    stats['top_paises'] = paises

    # Distribuicao por idioma
    idiomas = await db.fetch_all(
        """
        SELECT idioma, COUNT(*) as total
        FROM resultados_pesquisa
        WHERE falha_id = ?
        GROUP BY idioma
        ORDER BY total DESC
        """,
        (falha_id,)
    )
    stats['idiomas'] = idiomas

    return stats


# Script para inicializar o banco
if __name__ == "__main__":
    import asyncio

    async def main():
        await db.init_tables()
        print("\nEstatisticas atuais:")
        stats = await get_estatisticas_gerais()
        for key, value in stats.items():
            print(f"  {key}: {value}")

    asyncio.run(main())
