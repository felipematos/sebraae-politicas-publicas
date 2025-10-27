#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para traduzir queries usando modelos de tradução locais (sem APIs externas).

Usa Helsinki-NLP models do Hugging Face que são executados localmente.
Modelos suportados:
- Português → Árabe
- Português → Japonês
- Português → Coreano
- Português → Hebraico
"""
import sqlite3
import sys
from pathlib import Path
from transformers import pipeline
import json

# Configurar caminho do projeto
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "falhas_mercado_v1.db"
CACHE_FILE = PROJECT_DIR / "scripts" / "cache_traducoes_local.json"

# Mapeamento de idiomas para nomes completos
IDIOMAS_NOMES = {
    'ar': 'Arabic',
    'ja': 'Japanese',
    'ko': 'Korean',
    'he': 'Hebrew',
}

# Mapas de modelos disponíveis (pt → idioma alvo)
# Usando Helsinki-NLP models que estão disponíveis no Hugging Face
MODELOS = {
    'ar': 'Helsinki-NLP/opus-mt-pt-ar',      # Português para Árabe
    'ja': 'Helsinki-NLP/opus-mt-pt-jap',     # Português para Japonês
    'ko': 'Helsinki-NLP/opus-mt-pt-ko',      # Português para Coreano
    'he': 'Helsinki-NLP/opus-mt-pt-he',      # Português para Hebraico
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

def traduzir_com_modelo(translator, texto):
    """Traduz um texto usando o modelo carregado"""
    try:
        resultado = translator(texto, max_length=512)
        if resultado and len(resultado) > 0:
            return resultado[0]['translation_text']
        return None
    except Exception as e:
        print(f"      ✗ Erro ao traduzir: {e}")
        return None

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

    # Carregar modelo
    modelo_nome = MODELOS.get(idioma)
    if not modelo_nome:
        print(f"✗ Modelo não disponível para {idioma}")
        return 0, cache

    print(f"Carregando modelo: {modelo_nome}...")
    try:
        translator = pipeline("translation", model=modelo_nome, device=0 if sys.platform != "darwin" else -1)
    except Exception as e:
        print(f"✗ Erro ao carregar modelo: {e}")
        return 0, cache

    # Verificar cache
    ja_traduzidas = 0
    queries_traduzir = []

    for query in queries_unicas:
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

    # Traduzir
    traducoes_map = {}
    total = len(queries_traduzir)

    print(f"\nTraduzindo {total} queries...")

    for i, query in enumerate(queries_traduzir, 1):
        # Mostrar progresso a cada 10 queries
        if i % 10 == 0 or i == total:
            print(f"  [{i}/{total}] Traduzindo...")

        try:
            traducao = traduzir_com_modelo(translator, query)
            if traducao:
                traducoes_map[query] = traducao
                cache_key = f"{idioma}:{query}"
                cache[cache_key] = traducao
            else:
                print(f"  ⚠ Falha ao traduzir query {i}: {query[:50]}...")

        except Exception as e:
            print(f"  ✗ Erro na query {i}: {e}")
            continue

    print(f"\n✓ {len(traducoes_map)} queries traduzidas com sucesso")

    # Atualizar banco
    if traducoes_map:
        print(f"Atualizando banco de dados...")
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

    idiomas = ['ar', 'ja', 'ko', 'he']

    for idioma in idiomas:
        cursor.execute(
            "SELECT COUNT(DISTINCT query) FROM fila_pesquisas WHERE idioma = ? AND status = 'pendente'",
            (idioma,)
        )
        total = cursor.fetchone()[0]
        print(f"{IDIOMAS_NOMES[idioma]:12} ({idioma}): {total:4} queries")

    conn.close()

def main():
    print("Script de Tradução Local (Sem APIs Externas)")
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
