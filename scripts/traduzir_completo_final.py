#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script final e completo para traduzir TODAS as queries em português
para seus idiomas respectivos.

Estratégia:
1. Identificar queries que têm mistura de idiomas ou estão em português
2. Extrair a parte em português puro
3. Traduzir para o idioma alvo
4. Atualizar no banco de dados
"""
import sqlite3
import re
from pathlib import Path

DB_PATH = Path(".") / "falhas_mercado_v1.db"

# Dicionário MUITO MAIS COMPLETO de traduções
DICIONARIO_COMPLETO = {
    'ar': {  # Árabe
        'politica pública': 'سياسة عامة',
        'política pública': 'سياسة عامة',
        'políticas públicas': 'سياسات عامة',
        'boas práticas': 'أفضل الممارسات',
        'programas': 'برامج',
        'iniciativas': 'مبادرات',
        'relacionadas': 'ذات الصلة',
        'a:': 'إلى:',
        'infraestrutura': 'البنية التحتية',
        'ambiente': 'بيئة',
        'de inovação': 'للابتكار',
        'inovação': 'الابتكار',
        'hub': 'مركز',
        'startups': 'شركات ناشئة',
        'soluções': 'حلول',
        'para': 'ل',
        'solução': 'حل',
        'or': 'أو',
        'e': 'و',
        'em': 'في',
        'de': 'من',
        'a': 'إلى',
        'como': 'مثل',
        'incubadoras': 'حاضنات',
        'parques': 'متنزهات',
        'tecnológicos': 'تكنولوجية',
        'empresas': 'شركات',
    },
    'ja': {  # Japonês
        'politica pública': '公共政策',
        'política pública': '公共政策',
        'políticas públicas': '公共政策',
        'boas práticas': 'ベストプラクティス',
        'programas': 'プログラム',
        'iniciativas': 'イニシアチブ',
        'relacionadas': '関連する',
        'a:': 'へ:',
        'infraestrutura': 'インフラストラクチャ',
        'ambiente': '環境',
        'de inovação': 'イノベーション',
        'inovação': 'イノベーション',
        'hub': 'ハブ',
        'startups': 'スタートアップ',
        'soluções': 'ソリューション',
        'para': 'のため',
        'solução': 'ソリューション',
        'or': 'または',
        'e': 'と',
        'em': 'で',
        'de': 'の',
        'a': 'へ',
        'como': 'など',
        'incubadoras': 'インキュベータ',
        'parques': '公園',
        'tecnológicos': '技術的',
        'empresas': '企業',
    },
    'ko': {  # Coreano
        'politica pública': '공공 정책',
        'política pública': '공공 정책',
        'políticas públicas': '공공 정책',
        'boas práticas': '모범 사례',
        'programas': '프로그램',
        'iniciativas': '이니셔티브',
        'relacionadas': '관련된',
        'a:': '로:',
        'infraestrutura': '기반시설',
        'ambiente': '환경',
        'de inovação': '혁신',
        'inovação': '혁신',
        'hub': '허브',
        'startups': '스타트업',
        'soluções': '솔루션',
        'para': '위해',
        'solução': '솔루션',
        'or': '또는',
        'e': '그리고',
        'em': '에서',
        'de': '의',
        'a': '로',
        'como': '같은',
        'incubadoras': '인큐베이터',
        'parques': '공원',
        'tecnológicos': '기술적',
        'empresas': '회사',
    },
    'he': {  # Hebraico
        'politica pública': 'מדיניות ציבורית',
        'política pública': 'מדיניות ציבורית',
        'políticas públicas': 'מדיניות ציבורית',
        'boas práticas': 'שיטות טובות',
        'programas': 'תוכניות',
        'iniciativas': 'יוזמות',
        'relacionadas': 'הקשורות',
        'a:': 'ל:',
        'infraestrutura': 'תשתיות',
        'ambiente': 'סביבה',
        'de inovação': 'חדשנות',
        'inovação': 'חדשנות',
        'hub': 'מרכז',
        'startups': 'סטארטאפים',
        'soluções': 'פתרונות',
        'para': 'ל',
        'solução': 'פתרון',
        'or': 'או',
        'e': 'ו',
        'em': 'ב',
        'de': 'של',
        'a': 'ל',
        'como': 'כמו',
        'incubadoras': 'אינקובטורים',
        'parques': 'פארקים',
        'tecnológicos': 'טכנולוגיים',
        'empresas': 'חברות',
    },
    'it': {  # Italiano
        'politica pública': 'politica pubblica',
        'política pública': 'politica pubblica',
        'políticas públicas': 'politiche pubbliche',
        'boas práticas': 'buone pratiche',
        'programas': 'programmi',
        'iniciativas': 'iniziative',
        'relacionadas': 'correlate',
        'a:': 'a:',
        'infraestrutura': 'infrastruttura',
        'ambiente': 'ambiente',
        'de inovação': 'di innovazione',
        'inovação': 'innovazione',
        'hub': 'hub',
        'startups': 'startup',
        'soluções': 'soluzioni',
        'para': 'per',
        'solução': 'soluzione',
        'or': 'o',
        'e': 'e',
        'em': 'in',
        'de': 'di',
        'a': 'a',
        'como': 'come',
        'incubadoras': 'incubatori',
        'parques': 'parchi',
        'tecnológicos': 'tecnologici',
        'empresas': 'aziende',
    },
}

def limpar_query(query):
    """Remove caracteres de outros idiomas e deixa apenas português"""
    # Remove caracteres árabes
    query = re.sub(r'[\u0600-\u06FF]+', '', query)
    # Remove caracteres hebraicos
    query = re.sub(r'[\u0590-\u05FF]+', '', query)
    # Remove hiragana, katakana, kanji
    query = re.sub(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+', '', query)
    # Remove hangul (coreano)
    query = re.sub(r'[\uAC00-\uD7AF]+', '', query)
    # Remove espaços múltiplos
    query = re.sub(r'\s+', ' ', query)
    return query.strip()

def traduzir_query(query, idioma, dicionario):
    """Traduz uma query palavra por palavra"""
    # Primeiro, limpar qualquer caractere não-português
    query_limpo = limpar_query(query)

    if not query_limpo:
        return query_limpo

    # Converter para lowercase para busca
    query_lower = query_limpo.lower()

    # Tentar encontrar matches no dicionário em ordem de comprimento (maior primeiro)
    pares = sorted(dicionario.get(idioma, {}).items(), key=lambda x: len(x[0]), reverse=True)

    resultado = query_lower

    for pt, idioma_trad in pares:
        if pt.lower() in resultado:
            resultado = resultado.replace(pt.lower(), idioma_trad)

    # Capitalizar primeira letra
    if resultado:
        resultado = resultado[0].upper() + resultado[1:]

    return resultado

def contar_queries_em_pt():
    """Conta quantas queries ainda estão em português"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for idioma in ['ar', 'ja', 'ko', 'he', 'it']:
        cursor.execute(
            f"SELECT COUNT(DISTINCT query) FROM fila_pesquisas WHERE idioma = ? AND status = 'pendente' AND query NOT LIKE '%politica%' AND query NOT LIKE '%política%'",
            (idioma,)
        )
        total = cursor.fetchone()[0]
        print(f"{idioma.upper()}: {total} queries sem 'política'")

    conn.close()

def processar_idioma(idioma):
    """Processa e traduz todas as queries de um idioma"""
    print(f"\n{'='*70}")
    print(f"Processando {idioma.upper()}")
    print(f"{'='*70}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Obter todas as queries únicas deste idioma
    cursor.execute(
        "SELECT DISTINCT query FROM fila_pesquisas WHERE idioma = ? AND status = 'pendente' ORDER BY LENGTH(query)",
        (idioma,)
    )

    queries = [r[0] for r in cursor.fetchall()]
    print(f"Encontradas {len(queries)} queries únicas")

    atualizadas = 0

    for i, query in enumerate(queries, 1):
        if i % 200 == 0 or i == len(queries):
            print(f"  [{i}/{len(queries)}] Processando...")

        # Limpar e traduzir
        query_limpo = limpar_query(query)

        if query_limpo != query:
            # A query tinha caracteres de outro idioma, limpar
            query_traduzido = traduzir_query(query_limpo, idioma, DICIONARIO_COMPLETO)

            # Atualizar no banco
            cursor.execute(
                "UPDATE fila_pesquisas SET query = ? WHERE idioma = ? AND query = ? AND status = 'pendente'",
                (query_traduzido, idioma, query)
            )
            atualizadas += cursor.rowcount

    conn.commit()
    conn.close()

    print(f"✓ {atualizadas} queries atualizadas")
    return atualizadas

def main():
    print("Script Final de Tradução Completa")
    print("="*70)

    total = 0

    for idioma in ['ar', 'ja', 'ko', 'he', 'it']:
        atualizadas = processar_idioma(idioma)
        total += atualizadas

    print(f"\n{'='*70}")
    print(f"✓ Total de queries corrigidas: {total}")
    print(f"{'='*70}")

    # Verificação final
    contar_queries_em_pt()

if __name__ == "__main__":
    main()
