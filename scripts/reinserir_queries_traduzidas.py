#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para reinserir queries com traduções adequadas usando Claude
Remove TODAS as entradas não-português da queue e reinsere com traduções de qualidade
"""

import sqlite3
import asyncio
import os
from typing import Dict, List, Tuple
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


def get_queue_info() -> Tuple[int, Dict[str, int]]:
    """
    Obtém informações sobre a queue atual

    Returns:
        (total_entries, counts_by_language)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM fila_pesquisas")
    total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT idioma, COUNT(*)
        FROM fila_pesquisas
        GROUP BY idioma
        ORDER BY idioma
    """)

    counts = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    return total, counts


def get_portuguese_queries_with_metadata() -> List[Dict]:
    """
    Obtém todas as queries em português com seus metadados

    Returns:
        Lista de dicts com query, ferramenta, etc
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT
            falha_id, query, ferramenta, prioridade, max_tentativas
        FROM fila_pesquisas
        WHERE idioma = 'pt' AND status = 'pendente'
        ORDER BY falha_id, ferramenta
    """)

    queries = []
    for row in cursor.fetchall():
        queries.append({
            'falha_id': row[0],
            'query': row[1],
            'ferramenta': row[2],
            'prioridade': row[3],
            'max_tentativas': row[4]
        })

    conn.close()
    return queries


async def traduzir_queries_batch(
    client: Anthropic,
    queries_pt: List[str]
) -> Dict[str, Dict[str, str]]:
    """
    Traduz um lote de queries para todos os idiomas

    Args:
        client: Cliente Anthropic
        queries_pt: Lista de queries em português

    Returns:
        {idioma: {query_pt: query_traduzida}}
    """
    resultados = {}

    for idioma_alvo in IDIOMAS:
        if idioma_alvo == "pt":
            continue

        print(f"\n📝 Traduzindo {len(queries_pt)} queries para {IDIOMAS_NOMES.get(idioma_alvo)}")

        resultados[idioma_alvo] = {}
        conversation_history = [
            {
                "role": "user",
                "content": f"Você vai traduzir queries de pesquisa para {IDIOMAS_NOMES.get(idioma_alvo)}. Cada resposta deve ser APENAS a tradução, sem explicações."
            },
            {
                "role": "assistant",
                "content": f"Entendido. Vou traduzir queries de pesquisa para {IDIOMAS_NOMES.get(idioma_alvo)} de forma precisa e concisa."
            }
        ]

        for i, query_pt in enumerate(queries_pt, 1):
            try:
                conversation_history.append({
                    "role": "user",
                    "content": f"Traduza para {IDIOMAS_NOMES.get(idioma_alvo)}:\n{query_pt}"
                })

                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=500,
                    system="Você é um especialista em tradução de queries de pesquisa. Traduz para diversos idiomas mantendo precisão. Responde APENAS com a tradução, sem explicações.",
                    messages=conversation_history
                )

                traduzida = response.content[0].text.strip()
                resultados[idioma_alvo][query_pt] = traduzida

                conversation_history.append({
                    "role": "assistant",
                    "content": traduzida
                })

                if i % 10 == 0:
                    print(f"  → {i}/{len(queries_pt)} traduzidas")

            except Exception as e:
                print(f"  ✗ Erro traduzindo '{query_pt[:50]}': {e}")
                resultados[idioma_alvo][query_pt] = query_pt  # Fallback: keep original

        print(f"  ✓ {len(resultados[idioma_alvo])} queries traduzidas para {idioma_alvo}")

    return resultados


def limpar_queue_nao_portuguesa():
    """
    Deleta TODAS as entradas não-português da queue
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM fila_pesquisas WHERE idioma != 'pt'")
    deletadas = cursor.rowcount

    conn.commit()
    conn.close()

    return deletadas


def reinserir_com_traducoes(
    queries_pt_metadata: List[Dict],
    queries_traduzidas: Dict[str, Dict[str, str]]
) -> int:
    """
    Reinsere queries com traduções proper na queue

    Args:
        queries_pt_metadata: Metadata das queries em português
        queries_traduzidas: Traduções geradas

    Returns:
        Total de entradas inseridas
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total_inseridas = 0

    for idioma, mapa_traducoes in queries_traduzidas.items():
        for query_pt, query_traduzida in mapa_traducoes.items():
            # Encontrar metadados desta query
            for meta in queries_pt_metadata:
                if meta['query'] == query_pt:
                    cursor.execute("""
                        INSERT INTO fila_pesquisas
                        (falha_id, query, idioma, ferramenta, prioridade, tentativas, max_tentativas, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'pendente')
                    """, (
                        meta['falha_id'],
                        query_traduzida,
                        idioma,
                        meta['ferramenta'],
                        meta['prioridade'],
                        0,
                        meta['max_tentativas']
                    ))
                    total_inseridas += 1

    conn.commit()
    conn.close()

    return total_inseridas


def validar_sample(queries_traduzidas: Dict[str, Dict[str, str]]):
    """
    Mostra amostra de traduções para validação
    """
    print(f"\n✅ Amostra de traduções após re-insert:")

    for idioma in ["en", "es", "fr", "de"]:
        if idioma not in queries_traduzidas:
            continue

        mapa = queries_traduzidas[idioma]
        if not mapa:
            continue

        query_pt, query_traduzida = next(iter(mapa.items()))

        print(f"\n  {IDIOMAS_NOMES.get(idioma)} [{idioma.upper()}]:")
        print(f"    PT: {query_pt}")
        print(f"    {idioma.upper()}: {query_traduzida}")


async def main():
    """
    Fluxo principal
    """
    print("=" * 70)
    print("🔧 REINSERT DE QUERIES COM TRADUÇÕES ADEQUADAS")
    print("=" * 70)

    # 1. Diagnóstico
    print("\n📊 Diagnóstico atual:")
    total, counts = get_queue_info()
    print(f"  Total de entradas na queue: {total}")
    for idioma in IDIOMAS:
        count = counts.get(idioma, 0)
        print(f"    {IDIOMAS_NOMES.get(idioma):20} {idioma.upper():5} : {count:5} entradas")

    # 2. Obter queries em português
    print("\n📋 Extração de queries:")
    queries_pt_metadata = get_portuguese_queries_with_metadata()
    print(f"  ✓ Encontradas {len(queries_pt_metadata)} entradas em português com metadados")

    # Extrair apenas os textos únicos
    queries_pt_unicos = list(set(q['query'] for q in queries_pt_metadata))
    print(f"  ✓ {len(queries_pt_unicos)} queries únicas")

    # 3. Traduzir usando Claude
    print("\n🤖 Iniciando tradução com Claude API...")
    client = Anthropic()

    try:
        queries_traduzidas = await traduzir_queries_batch(client, queries_pt_unicos)
    except Exception as e:
        print(f"❌ Erro na tradução: {e}")
        return

    # 4. Validar amostra
    validar_sample(queries_traduzidas)

    # 5. Confirmar antes de atualizar
    print("\n⚠️  Próximo passo: atualizar database")
    print(f"   Serão deletadas TODAS as {total - counts.get('pt', 0)} entradas não-português")
    print(f"   Serão inseridas ~{(total - counts.get('pt', 0))} entradas com traduções adequadas")

    resposta = input("\n👉 Deseja continuar? (s/n): ").strip().lower()
    if resposta != 's':
        print("❌ Operação cancelada")
        return

    # 6. Deletar entradas não-português
    print("\n🗑️  Limpando queue...")
    deletadas = limpar_queue_nao_portuguesa()
    print(f"  ✓ Deletadas {deletadas} entradas não-português")

    # 7. Reinserir com traduções
    print("\n📥 Reinserindo com traduções adequadas...")
    inseridas = reinserir_com_traducoes(queries_pt_metadata, queries_traduzidas)
    print(f"  ✓ Inseridas {inseridas} entradas traduzidas")

    # 8. Verificar resultado final
    print("\n✅ Concluído!")
    total_final, counts_final = get_queue_info()
    print(f"  Total final: {total_final} entradas")
    for idioma in IDIOMAS:
        count_antes = counts.get(idioma, 0)
        count_depois = counts_final.get(idioma, 0)
        change = count_depois - count_antes
        symbol = "↑" if change > 0 else "=" if change == 0 else "↓"
        print(f"    {IDIOMAS_NOMES.get(idioma):20} {idioma.upper():5} : {count_antes:5} → {count_depois:5} ({symbol} {change:+d})")


if __name__ == "__main__":
    asyncio.run(main())
