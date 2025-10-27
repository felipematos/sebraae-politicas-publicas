#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para gerar filas traduzidas a partir dos textos em português completados
Usa Claude para traduzir as queries já processadas para todos os idiomas
"""

import sqlite3
import asyncio
import os
from typing import Dict, List, Tuple, Set
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
IDIOMAS = ["en", "es", "fr", "de", "it", "ar", "ja", "ko", "he"]  # Sem PT
IDIOMAS_NOMES = {
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


def extrair_entradas_pt_completadas() -> Dict[Tuple, Set[str]]:
    """
    Extrai todas as entradas em português completadas

    Returns:
        {(falha_id, ferramenta): set(queries_unicas)}
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT falha_id, ferramenta, query
        FROM fila_pesquisas
        WHERE idioma = 'pt' AND status = 'completa'
        ORDER BY falha_id, ferramenta
    """)

    entradas = {}
    for falha_id, ferramenta, query in cursor.fetchall():
        chave = (falha_id, ferramenta)
        if chave not in entradas:
            entradas[chave] = set()
        entradas[chave].add(query)

    conn.close()
    return entradas


async def traduzir_queries_para_idioma(
    client: Anthropic,
    queries_unicos: List[str],
    idioma_alvo: str
) -> Dict[str, str]:
    """
    Traduz um conjunto de queries para um idioma específico

    Args:
        client: Cliente Anthropic
        queries_unicos: Lista de queries em português únicos
        idioma_alvo: Idioma alvo (en, es, fr, etc)

    Returns:
        {query_pt: query_traduzida}
    """
    print(f"  📝 Traduzindo {len(queries_unicos)} queries para {IDIOMAS_NOMES.get(idioma_alvo)}")

    resultados = {}
    conversation_history = [
        {
            "role": "user",
            "content": f"Você é um tradutor de queries de pesquisa. Vai traduzir para {IDIOMAS_NOMES.get(idioma_alvo)}. Responda APENAS com a tradução, sem explicações ou marcadores."
        },
        {
            "role": "assistant",
            "content": f"Entendido. Vou traduzir queries para {IDIOMAS_NOMES.get(idioma_alvo)} de forma precisa e concisa, respondendo apenas com a tradução."
        }
    ]

    for i, query_pt in enumerate(queries_unicos, 1):
        try:
            conversation_history.append({
                "role": "user",
                "content": query_pt
            })

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                system=f"Você é um especialista em tradução. Traduz queries de pesquisa para {IDIOMAS_NOMES.get(idioma_alvo)}. Responde APENAS com a tradução, sem explicações.",
                messages=conversation_history
            )

            traduzida = response.content[0].text.strip()
            resultados[query_pt] = traduzida

            conversation_history.append({
                "role": "assistant",
                "content": traduzida
            })

            if i % 5 == 0:
                print(f"    → {i}/{len(queries_unicos)} traduzidas")

        except Exception as e:
            print(f"    ✗ Erro traduzindo '{query_pt[:50]}': {e}")
            resultados[query_pt] = query_pt  # Fallback

    print(f"    ✓ {len(resultados)} queries traduzidas para {IDIOMAS_NOMES.get(idioma_alvo)}")
    return resultados


async def traduzir_todas_queries(
    queries_por_ferramenta: Dict[Tuple, Set[str]]
) -> Dict[str, Dict[str, str]]:
    """
    Traduz todas as queries para todos os idiomas

    Args:
        queries_por_ferramenta: {(falha_id, ferramenta): set(queries)}

    Returns:
        {idioma: {query_pt: query_traduzida}}
    """
    # Extrair queries únicos em português
    queries_unicos = set()
    for queries_set in queries_por_ferramenta.values():
        queries_unicos.update(queries_set)

    queries_unicos = sorted(list(queries_unicos))
    print(f"✓ {len(queries_unicos)} queries únicos em português")

    # Traduzir para cada idioma
    client = Anthropic()
    all_translations = {}

    for idioma in IDIOMAS:
        try:
            traducoes = await traduzir_queries_para_idioma(
                client, queries_unicos, idioma
            )
            all_translations[idioma] = traducoes
        except Exception as e:
            print(f"❌ Erro traduzindo para {idioma}: {e}")
            all_translations[idioma] = {}

    return all_translations


def inserir_queries_traduzidas(
    queries_por_ferramenta: Dict[Tuple, Set[str]],
    all_translations: Dict[str, Dict[str, str]]
) -> int:
    """
    Insere as queries traduzidas na fila

    Args:
        queries_por_ferramenta: Metadados das queries PT
        all_translations: {idioma: {query_pt: query_traduzida}}

    Returns:
        Total de entradas inseridas
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total_inseridas = 0

    for (falha_id, ferramenta), queries_pt_set in queries_por_ferramenta.items():
        for query_pt in queries_pt_set:
            for idioma, traducoes in all_translations.items():
                query_traduzida = traducoes.get(query_pt, query_pt)

                try:
                    cursor.execute("""
                        INSERT INTO fila_pesquisas
                        (falha_id, query, idioma, ferramenta, prioridade, tentativas, max_tentativas, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'pendente')
                    """, (
                        falha_id,
                        query_traduzida,
                        idioma,
                        ferramenta,
                        0,  # prioridade
                        0,  # tentativas
                        3   # max_tentativas
                    ))
                    total_inseridas += 1
                except Exception as e:
                    print(f"✗ Erro inserindo: {e}")

    conn.commit()
    conn.close()

    return total_inseridas


def mostrar_samples(all_translations: Dict[str, Dict[str, str]]):
    """
    Mostra amostra de traduções
    """
    print(f"\n✅ Amostra de traduções:")

    for idioma in ["en", "es", "fr", "de"]:
        if idioma not in all_translations:
            continue

        traducoes = all_translations[idioma]
        if not traducoes:
            continue

        query_pt, query_traduzida = next(iter(traducoes.items()))

        print(f"\n  {IDIOMAS_NOMES.get(idioma)} [{idioma.upper()}]:")
        print(f"    PT: {query_pt}")
        print(f"    {idioma.upper()}: {query_traduzida}")


async def main():
    """
    Fluxo principal
    """
    print("=" * 70)
    print("🔄 REGENERAÇÃO DE FILAS COM TRADUÇÕES ADEQUADAS")
    print("=" * 70)

    # 1. Extrair entradas PT completadas
    print("\n📋 Extraindo queries em português...")
    queries_por_ferramenta = extrair_entradas_pt_completadas()

    total_queries = sum(len(qs) for qs in queries_por_ferramenta.values())
    print(f"  ✓ {len(queries_por_ferramenta)} combinações (falha_id, ferramenta)")
    print(f"  ✓ {total_queries} instâncias de queries")

    # 2. Traduzir
    print("\n🤖 Iniciando tradução com Claude API...")
    all_translations = await traduzir_todas_queries(queries_por_ferramenta)

    # 3. Mostrar samples
    mostrar_samples(all_translations)

    # 4. Confirmar
    total_a_inserir = total_queries * len(IDIOMAS)
    print(f"\n⚠️  Próximo passo: inserir {total_a_inserir} entradas traduzidas na fila")

    resposta = input("\n👉 Deseja continuar? (s/n): ").strip().lower()
    if resposta != 's':
        print("❌ Operação cancelada")
        return

    # 5. Inserir
    print("\n📥 Inserindo queries traduzidas...")
    inseridas = inserir_queries_traduzidas(queries_por_ferramenta, all_translations)
    print(f"  ✓ Inseridas {inseridas} entradas")

    # 6. Verificar resultado
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT idioma, COUNT(*)
        FROM fila_pesquisas
        GROUP BY idioma
        ORDER BY idioma
    """)

    print(f"\n✅ Resultado final:")
    total_final = 0
    for idioma, count in cursor.fetchall():
        print(f"  {idioma.upper():5} : {count:5} entradas")
        total_final += count

    print(f"\n  TOTAL: {total_final} entradas na fila")
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
