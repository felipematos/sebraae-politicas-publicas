#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para traduzir queries que ainda estão em português para árabe, japonês, coreano e hebraico.

Identifica todas as queries únicas em cada idioma e as traduz, usando cache em memória
para evitar traduzir a mesma query múltiplas vezes.
"""
import os
import sqlite3
import sys
from pathlib import Path
from anthropic import Anthropic
import json
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar caminho do projeto
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "falhas_mercado_v1.db"
CACHE_FILE = PROJECT_DIR / "scripts" / "cache_traducoes.json"

# Cliente Anthropic com API key do .env
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("✗ Erro: ANTHROPIC_API_KEY não está definida em .env")
    sys.exit(1)

client = Anthropic(api_key=api_key)

# Mapeamento de idiomas
IDIOMAS_NOMES = {
    'ar': 'Arabic',
    'ja': 'Japanese',
    'ko': 'Korean',
    'he': 'Hebrew',
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian'
}

def carregar_cache():
    """Carrega cache de traduções anterior"""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_cache(cache):
    """Salva cache de traduções"""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def obter_queries_unicas(idioma):
    """Obtém todas as queries únicas de um idioma"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT DISTINCT query FROM fila_pesquisas WHERE idioma = ? AND status = 'pendente' ORDER BY query",
        (idioma,)
    )

    queries = [r[0] for r in cursor.fetchall()]
    conn.close()

    return queries

def traduzir_lote(queries, idioma_alvo):
    """Traduz um lote de queries usando Claude"""
    idioma_nome = IDIOMAS_NOMES.get(idioma_alvo, idioma_alvo)

    prompt = f"""You are a professional translator. Translate the following Portuguese text to {idioma_nome} ({idioma_alvo}).

IMPORTANT RULES:
1. Translate each line of text to {idioma_nome}
2. Keep the exact same structure and formatting
3. Return ONLY the translations, one per line
4. If input is multiple lines separated by newlines, maintain that structure
5. Do not add numbering, explanations or extra text
6. Preserve any hyphens or special characters

Text to translate:
{chr(10).join(queries)}

Provide the {idioma_nome} translations only:"""

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        resultado = response.content[0].text

        # Processar resultado
        linhas = resultado.strip().split('\n')
        traducoes = [l.strip() for l in linhas if l.strip()]

        return traducoes

    except Exception as e:
        print(f"✗ Erro ao traduzir: {e}")
        return []

def atualizar_banco(idioma, traducoes_map):
    """Atualiza o banco com as traduções"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    atualizadas = 0

    for query_original, query_traduzida in traducoes_map.items():
        cursor.execute(
            "UPDATE fila_pesquisas SET query = ? WHERE idioma = ? AND query = ? AND status = 'pendente'",
            (query_traduzida, idioma, query_original)
        )
        atualizadas += cursor.rowcount

    conn.commit()
    conn.close()

    return atualizadas

def processar_idioma(idioma, cache):
    """Processa tradução para um idioma"""
    print(f"\n{'='*70}")
    print(f"Processando {IDIOMAS_NOMES[idioma]} ({idioma})")
    print(f"{'='*70}")

    queries_unicas = obter_queries_unicas(idioma)

    if not queries_unicas:
        print(f"✓ Nenhuma query pendente para {idioma}")
        return 0, cache

    print(f"Encontradas {len(queries_unicas)} queries únicas")

    # Verificar se já estão traduzidas (se começam com caracteres não-latinos)
    # Para árabe: \\u0600-\\u06FF
    # Para japonês: \\u3040-\\u309F (Hiragana) ou \\u30A0-\\u30FF (Katakana) ou \\u4E00-\\u9FFF (Kanji)
    # Para coreano: \\uAC00-\\uD7AF (Hangul)
    # Para hebraico: \\u0590-\\u05FF

    ja_traduzidas = 0
    queries_traduzir = []

    for query in queries_unicas:
        # Criar chave cache única
        cache_key = f"{idioma}:{query}"

        if cache_key in cache:
            ja_traduzidas += 1
        else:
            queries_traduzir.append(query)

    print(f"  - Já em cache: {ja_traduzidas}")
    print(f"  - Precisam tradução: {len(queries_traduzir)}")

    if not queries_traduzir:
        print(f"✓ Todas as queries já foram traduzidas ou estão em cache")
        return 0, cache

    # Traduzir em lotes de 5
    traducoes_map = {}
    lote_size = 5

    for i in range(0, len(queries_traduzir), lote_size):
        lote = queries_traduzir[i:i+lote_size]
        num_lote = (i // lote_size) + 1
        total_lotes = (len(queries_traduzir) + lote_size - 1) // lote_size

        print(f"\n[Lote {num_lote}/{total_lotes}] Traduzindo {len(lote)} queries...")

        try:
            traducoes = traduzir_lote(lote, idioma)

            if len(traducoes) >= len(lote):
                for original, traduzida in zip(lote, traducoes[:len(lote)]):
                    traducoes_map[original] = traduzida
                    cache_key = f"{idioma}:{original}"
                    cache[cache_key] = traduzida

                print(f"  ✓ {len(lote)} queries traduzidas")
            else:
                print(f"  ⚠ Esperado {len(lote)} traduções, recebido {len(traducoes)}")
                for original, traduzida in zip(lote[:len(traducoes)], traducoes):
                    traducoes_map[original] = traduzida
                    cache_key = f"{idioma}:{original}"
                    cache[cache_key] = traduzida

        except Exception as e:
            print(f"  ✗ Erro no lote {num_lote}: {e}")
            continue

    # Atualizar banco
    if traducoes_map:
        print(f"\nAtualizando banco de dados...")
        atualizadas = atualizar_banco(idioma, traducoes_map)
        print(f"✓ {atualizadas} queries atualizadas")
    else:
        print(f"✗ Nenhuma tradução foi realizada")
        atualizadas = 0

    return atualizadas, cache

def verificar_status_traducoes():
    """Verifica quantas queries de cada idioma ainda estão em português"""
    print("\n" + "="*70)
    print("Verificando status das queries por idioma...")
    print("="*70)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    idiomas = ['ar', 'ja', 'ko', 'he', 'en', 'es', 'fr', 'de', 'it']

    for idioma in idiomas:
        cursor.execute(
            "SELECT COUNT(DISTINCT query) FROM fila_pesquisas WHERE idioma = ? AND status = 'pendente'",
            (idioma,)
        )
        total = cursor.fetchone()[0]

        print(f"{IDIOMAS_NOMES[idioma]:12} ({idioma}): {total:4} queries")

    conn.close()

def main():
    print("Script de Tradução de Queries em Idiomas Faltantes")
    print("="*70)

    cache = carregar_cache()
    print(f"Cache carregado com {len(cache)} entradas")

    # Idiomas que precisam de correção
    idiomas_com_problema = ['ar', 'ja', 'ko', 'he']

    total_atualizadas = 0

    for idioma in idiomas_com_problema:
        atualizadas, cache = processar_idioma(idioma, cache)
        total_atualizadas += atualizadas

    # Salvar cache
    salvar_cache(cache)
    print(f"\n✓ Cache salvo com {len(cache)} entradas")

    print(f"\n{'='*70}")
    print(f"✓ Total de queries atualizadas: {total_atualizadas}")
    print(f"{'='*70}")

    # Verificar status final
    verificar_status_traducoes()

if __name__ == "__main__":
    main()
