#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corrigir queries não traduzidas na fila de pesquisas
Remove queries em português com prefixo [LINGUA] e reinsere com traduções adequadas
"""

import sqlite3
import asyncio
import json
import re
import os
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import sys
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Adicionar app ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from anthropic import Anthropic

# Configuração
DB_PATH = Path(__file__).parent.parent / "falhas_mercado_v1.db"
IDIOMAS = ["pt", "en", "es", "fr", "de", "it", "ar", "ja", "ko", "he"]
IDIOMAS_NOMES = {
    "pt": "Português (Brasil)",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "ar": "العربية",
    "ja": "日本語",
    "ko": "한국어",
    "he": "עברית"
}


def get_unique_portuguese_queries() -> Dict[int, str]:
    """
    Extrai queries únicas em português (sem prefixo de idioma)

    Returns:
        Dict com {falha_id: query_português}
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Busca queries em português únicos (sem prefixo [XX])
    cursor.execute("""
        SELECT DISTINCT falha_id, query
        FROM fila_pesquisas
        WHERE idioma = 'pt' AND query NOT LIKE '[%'
        ORDER BY falha_id
    """)

    queries = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    print(f"✓ Encontradas {len(queries)} queries únicas em português")
    return queries


def get_untranslated_entries_count() -> Dict[str, int]:
    """
    Conta entradas não traduzidas por idioma

    Returns:
        Dict com contagem por idioma
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT idioma, COUNT(*)
        FROM fila_pesquisas
        WHERE idioma != 'pt' AND query LIKE '[%'
        GROUP BY idioma
    """)

    counts = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    return counts


async def traduzir_query_claude(
    client: Anthropic,
    query: str,
    idioma_alvo: str,
    conversation_history: List[Dict]
) -> Tuple[str, List[Dict]]:
    """
    Traduz uma query para o idioma alvo usando Claude

    Args:
        client: Cliente Anthropic
        query: Query em português para traduzir
        idioma_alvo: Código do idioma alvo
        conversation_history: Histórico da conversa para multi-turn

    Returns:
        Tupla (query_traduzida, conversation_history_atualizado)
    """
    if idioma_alvo == "pt":
        return query, conversation_history

    # Adicionar mensagem do usuário
    conversation_history.append({
        "role": "user",
        "content": f"Traduza esta query de pesquisa para {IDIOMAS_NOMES.get(idioma_alvo, idioma_alvo)}. Mantenha o significado e a estrutura. Responda APENAS com a tradução, sem explicações:\n\n{query}"
    })

    # Chamar Claude
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        system="Você é um especialista em tradução de queries de pesquisa. Traduz para diversos idiomas mantendo precisão técnica. Responde APENAS com a tradução, sem explicações ou formatação adicional.",
        messages=conversation_history
    )

    traduzida = response.content[0].text.strip()

    # Adicionar resposta do assistente ao histórico
    conversation_history.append({
        "role": "assistant",
        "content": traduzida
    })

    return traduzida, conversation_history


async def traduzir_queries_lote(
    client: Anthropic,
    queries_por_idioma: Dict[str, List[str]]
) -> Dict[str, Dict[str, str]]:
    """
    Traduz queries agrupadas por idioma alvo

    Args:
        client: Cliente Anthropic
        queries_por_idioma: {idioma: [queries]}

    Returns:
        {idioma: {query_original: query_traduzida}}
    """
    resultados = {}

    for idioma_alvo in IDIOMAS:
        if idioma_alvo == "pt":
            continue

        queries = queries_por_idioma.get(idioma_alvo, [])
        if not queries:
            continue

        print(f"\n📝 Traduzindo {len(queries)} queries para {IDIOMAS_NOMES.get(idioma_alvo)}")

        resultados[idioma_alvo] = {}
        conversation_history = []

        for i, query in enumerate(queries, 1):
            try:
                traduzida, conversation_history = await traduzir_query_claude(
                    client, query, idioma_alvo, conversation_history
                )
                resultados[idioma_alvo][query] = traduzida

                if i % 5 == 0:
                    print(f"  → {i}/{len(queries)} traduzidas")

            except Exception as e:
                print(f"  ✗ Erro traduzindo '{query[:50]}': {e}")
                resultados[idioma_alvo][query] = f"[{idioma_alvo.upper()}] {query}"

        print(f"  ✓ {len(resultados[idioma_alvo])} queries traduzidas para {idioma_alvo}")

    return resultados


def atualizar_database(
    queries_traduzidas: Dict[str, Dict[str, str]],
    dryrun: bool = False
) -> Tuple[int, int]:
    """
    Atualiza database com queries traduzidas

    Args:
        queries_traduzidas: Resultado da tradução
        dryrun: Se True, mostra o que seria feito sem alterar

    Returns:
        (queries_deletadas, queries_inseridas)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Contar entradas que serão deletadas
    cursor.execute("SELECT COUNT(*) FROM fila_pesquisas WHERE idioma != 'pt' AND query LIKE '[%'")
    total_deletar = cursor.fetchone()[0]

    print(f"\n📊 Resumo das mudanças:")
    print(f"  Entradas a deletar: {total_deletar}")

    if dryrun:
        print("  [DRY RUN - Nenhuma alteração será feita]")
        conn.close()
        return total_deletar, 0

    # 2. Deletar entradas não traduzidas
    cursor.execute("DELETE FROM fila_pesquisas WHERE idioma != 'pt' AND query LIKE '[%'")
    queries_deletadas = cursor.rowcount
    print(f"  ✓ Deletadas {queries_deletadas} entradas não traduzidas")

    # 3. Reinsert com queries traduzidas
    queries_inseridas = 0
    total_re_insert = 0

    for idioma_alvo, mapa_traducoes in queries_traduzidas.items():
        if not mapa_traducoes:
            continue

        # Para cada query original
        for query_pt, query_traduzida in mapa_traducoes.items():
            # Buscar todas as entradas que tinham essa query em português
            cursor.execute("""
                SELECT falha_id, ferramenta, prioridade, tentativas, max_tentativas
                FROM fila_pesquisas
                WHERE idioma = 'pt' AND query = ? AND status = 'pendente'
            """, (query_pt,))

            entradas_pt = cursor.fetchall()

            # Para cada entrada original em português, criar versão traduzida
            for falha_id, ferramenta, prioridade, tentativas, max_tentativas in entradas_pt:
                cursor.execute("""
                    INSERT INTO fila_pesquisas
                    (falha_id, query, idioma, ferramenta, prioridade, tentativas, max_tentativas, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pendente')
                """, (
                    falha_id,
                    query_traduzida,
                    idioma_alvo,
                    ferramenta,
                    prioridade,
                    0,  # Reset tentativas
                    max_tentativas
                ))
                queries_inseridas += 1

        total_re_insert += len(mapa_traducoes)

    print(f"  ✓ Inseridas {queries_inseridas} entradas traduzidas")

    conn.commit()
    conn.close()

    return queries_deletadas, queries_inseridas


def validar_traducoes(queries_traduzidas: Dict[str, Dict[str, str]]) -> None:
    """
    Mostra amostra das traduções para validação
    """
    print(f"\n✅ Amostra de traduções:")

    for idioma, mapa in queries_traduzidas.items():
        if not mapa:
            continue

        # Pegar primeira tradução como exemplo
        query_pt, query_traduzida = next(iter(mapa.items()))

        print(f"\n  {IDIOMAS_NOMES.get(idioma)} [{idioma.upper()}]:")
        print(f"    PT: {query_pt}")
        print(f"    {idioma.upper()}: {query_traduzida}")


async def main():
    """
    Fluxo principal
    """
    print("=" * 70)
    print("🔧 CORRETOR DE QUERIES NÃO TRADUZIDAS")
    print("=" * 70)

    # 1. Diagnóstico
    print("\n📊 Diagnóstico:")
    untranslated = get_untranslated_entries_count()
    total_untranslated = sum(untranslated.values())
    print(f"  Total de entradas não traduzidas: {total_untranslated}")
    for idioma, count in sorted(untranslated.items()):
        print(f"    {IDIOMAS_NOMES.get(idioma):20} {idioma.upper():5} : {count:5} entradas")

    # 2. Extrair queries únicas em português
    print("\n📋 Extração de queries:")
    queries_pt = get_unique_portuguese_queries()

    # Agrupar queries por idioma (cada query será traduzida para todos)
    queries_por_idioma = {idioma: list(queries_pt.values()) for idioma in IDIOMAS if idioma != "pt"}

    # 3. Traduzir usando Claude
    print("\n🤖 Iniciando tradução com Claude API...")
    client = Anthropic()

    try:
        queries_traduzidas = await traduzir_queries_lote(client, queries_por_idioma)
    except Exception as e:
        print(f"❌ Erro na tradução: {e}")
        return

    # 4. Validar amostra
    validar_traducoes(queries_traduzidas)

    # 5. Confirmar antes de atualizar
    print("\n⚠️  Próximo passo: atualizar database")
    print(f"   Será deletado {total_untranslated} entradas não traduzidas")
    print(f"   Serão inseridas ~{total_untranslated} entradas com traduções")

    resposta = input("\n👉 Deseja continuar? (s/n): ").strip().lower()
    if resposta != 's':
        print("❌ Operação cancelada")
        return

    # 6. Atualizar database
    deletadas, inseridas = atualizar_database(queries_traduzidas, dryrun=False)

    print(f"\n✅ Concluído!")
    print(f"  Deletadas: {deletadas}")
    print(f"  Inseridas: {inseridas}")
    print(f"  Saldo: {inseridas - deletadas:+d}")


if __name__ == "__main__":
    asyncio.run(main())
