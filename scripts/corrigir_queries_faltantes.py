#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corrigir queries que ainda estão em português
e deveriam estar traduzidas para árabe, japonês, coreano e hebraico.

Identifica queries duplicadas em diferentes idiomas e traduz as que ainda
estão em português para seus idiomas respectivos.
"""
import os
import sqlite3
import sys
from pathlib import Path
from anthropic import Anthropic

# Configurar caminho do projeto
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "falhas_mercado_v1.db"

# Cliente Anthropic
client = Anthropic()

# Mapeamento de idiomas para nomes completos
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

def obter_queries_em_portugues_por_idioma(idioma):
    """Obtém todas as queries que estão em português mas deveriam estar em outro idioma"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
    SELECT DISTINCT query
    FROM fila_pesquisas
    WHERE status = 'pendente' AND idioma = ?
    AND query IN (
        SELECT query FROM fila_pesquisas WHERE idioma = 'pt' AND status = 'pendente'
    )
    ORDER BY query
    """

    cursor.execute(query, (idioma,))
    resultados = cursor.fetchall()
    conn.close()

    return [r[0] for r in resultados]

def traduzir_queries_lote(queries, idioma_alvo, lista_conversacao):
    """Traduz um lote de queries usando Claude com histórico de conversa"""

    idioma_nome = IDIOMAS_NOMES.get(idioma_alvo, idioma_alvo)

    # Criar prompt para tradução em lote
    prompt = f"""You are a professional translator. Translate the following Portuguese queries to {idioma_nome} ({idioma_alvo}).

Important rules:
1. Maintain the exact meaning and context
2. Preserve any hyphens or special formatting
3. Return ONLY the translations, one per line, in the same order as input
4. Do not add explanations or numbering

Queries to translate:
{chr(10).join(f'{i+1}. {q}' for i, q in enumerate(queries))}

Provide the {idioma_nome} translations now:"""

    # Adicionar mensagem do usuário ao histórico
    lista_conversacao.append({
        "role": "user",
        "content": prompt
    })

    # Chamar Claude com histórico
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4000,
        messages=lista_conversacao
    )

    resultado = response.content[0].text

    # Adicionar resposta ao histórico
    lista_conversacao.append({
        "role": "assistant",
        "content": resultado
    })

    # Processar resultado
    linhas = resultado.strip().split('\n')
    traducoes = []

    for linha in linhas:
        # Remover numeração (ex: "1. ", "2. ")
        linha = linha.strip()
        if linha and '.' in linha[:3]:
            # Remover numeração do início
            partes = linha.split('.', 1)
            if len(partes) > 1:
                linha = partes[1].strip()

        if linha:
            traducoes.append(linha)

    return traducoes, lista_conversacao

def atualizar_queries_no_banco(idioma, traducoes_por_query):
    """Atualiza as queries no banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    atualizadas = 0
    for query_original, query_traduzida in traducoes_por_query.items():
        cursor.execute(
            "UPDATE fila_pesquisas SET query = ? WHERE idioma = ? AND query = ?",
            (query_traduzida, idioma, query_original)
        )
        atualizadas += cursor.rowcount

    conn.commit()
    conn.close()

    return atualizadas

def processar_idioma(idioma):
    """Processa todas as queries faltantes de um idioma"""
    print(f"\n{'='*70}")
    print(f"Processando {IDIOMAS_NOMES[idioma]} ({idioma})")
    print(f"{'='*70}")

    # Obter queries que ainda estão em português
    queries_em_pt = obter_queries_em_portugues_por_idioma(idioma)

    if not queries_em_pt:
        print(f"✓ Nenhuma query faltante para {idioma}")
        return 0

    print(f"Encontradas {len(queries_em_pt)} queries que precisam tradução para {IDIOMAS_NOMES[idioma]}")

    # Processar em lotes de 10 queries
    lista_conversacao = []
    traducoes_por_query = {}
    lote_size = 10

    for i in range(0, len(queries_em_pt), lote_size):
        lote = queries_em_pt[i:i+lote_size]
        num_lote = (i // lote_size) + 1
        total_lotes = (len(queries_em_pt) + lote_size - 1) // lote_size

        print(f"\n[Lote {num_lote}/{total_lotes}] Traduzindo {len(lote)} queries...")

        try:
            traducoes, lista_conversacao = traduzir_queries_lote(lote, idioma, lista_conversacao)

            # Mapear original para tradução
            if len(traducoes) == len(lote):
                for original, traduzida in zip(lote, traducoes):
                    traducoes_por_query[original] = traduzida
                print(f"✓ {len(traducoes)} queries traduzidas com sucesso")
            else:
                print(f"⚠ Aviso: Esperado {len(lote)} traduções, recebido {len(traducoes)}")
                # Usar as traduções que conseguimos
                for original, traduzida in zip(lote[:len(traducoes)], traducoes):
                    traducoes_por_query[original] = traduzida

        except Exception as e:
            print(f"✗ Erro ao traduzir lote {num_lote}: {e}")
            continue

    # Atualizar banco de dados
    print(f"\nAtualizando banco de dados...")
    atualizadas = atualizar_queries_no_banco(idioma, traducoes_por_query)
    print(f"✓ {atualizadas} queries atualizadas no banco")

    return atualizadas

def main():
    print("Script de Correção de Queries em Múltiplos Idiomas")
    print("="*70)

    # Idiomas que precisam de correção
    idiomas_com_problema = ['ar', 'ja', 'ko', 'he']

    total_atualizadas = 0

    for idioma in idiomas_com_problema:
        atualizadas = processar_idioma(idioma)
        total_atualizadas += atualizadas

    print(f"\n{'='*70}")
    print(f"✓ Total de queries atualizadas: {total_atualizadas}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
