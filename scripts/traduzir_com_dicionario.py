#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para traduzir queries de forma sistemática usando um dicionário contextual
baseado nas falhas de mercado e suas categorias.

Estratégia:
1. Extrair palavras-chave das queries em português
2. Traduzir cada palavra para o idioma alvo usando um dicionário
3. Reconstruir as frases traduzidas
"""
import sqlite3
import sys
from pathlib import Path
import json

# Configurar caminho do projeto
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "falhas_mercado_v1.db"

# Dicionário de traduções de termos comuns encontrados nas queries
DICIONARIO_TRADUCOES = {
    'ar': {  # Árabe
        'qualidade': 'الجودة',
        'relativa': 'النسبية',
        'incipiente': 'الناشئة',
        'dos': '',
        'ambientes': 'البيئات',
        'de': '',
        'inovação': 'الابتكار',
        'boa': 'جيدة',
        'parte': 'جزء',
        'deficiências': 'نواقص',
        'estruturais': 'هيكلية',
        'na': 'في',
        'educação': 'التعليم',
        'stem': 'STEM',
        'lacunas': 'الفجوات',
        'em': '',
        'letramento': 'محو الأمية',
        'digital': 'الرقمية',
        'ia': 'الذكاء الاصطناعي',
        'ausência': 'غياب',
        'de políticas': 'سياسات',
        'imigratórias': 'الهجرة',
        'eficazes': 'فعالة',
        'incentivo': 'الحافز',
        'à': '',
        'escassez': 'نقص',
        'empreendedorismo': 'ريادة الأعمال',
        'para': 'لـ',
        'o': '',
        'e': 'و',
        'falta': 'غياب',
    },
    'ja': {  # Japonês
        'qualidade': '品質',
        'relativa': '相対的',
        'incipiente': '初期的',
        'dos': 'の',
        'ambientes': '環境',
        'de': 'の',
        'inovação': 'イノベーション',
        'boa': 'より良い',
        'parte': 'パート',
        'deficiências': '不足',
        'estruturais': '構造的',
        'na': 'で',
        'educação': '教育',
        'stem': 'STEM',
        'lacunas': 'ギャップ',
        'em': 'で',
        'letramento': 'リテラシー',
        'digital': 'デジタル',
        'ia': 'AI',
        'ausência': '不在',
        'de políticas': 'ポリシー',
        'imigratórias': '移民',
        'eficazes': '効果的',
        'incentivo': 'インセンティブ',
        'à': 'へ',
        'escassez': '不足',
        'empreendedorismo': '起業精神',
        'para': 'へ',
        'o': 'の',
        'e': 'と',
        'falta': '不足',
    },
    'ko': {  # Coreano
        'qualidade': '품질',
        'relativa': '상대적',
        'incipiente': '초기의',
        'dos': '의',
        'ambientes': '환경',
        'de': '의',
        'inovação': '혁신',
        'boa': '더 좋은',
        'parte': '부분',
        'deficiências': '결핍',
        'estruturais': '구조적',
        'na': '에서',
        'educação': '교육',
        'stem': 'STEM',
        'lacunas': '격차',
        'em': '에서',
        'letramento': '문해력',
        'digital': '디지털',
        'ia': 'AI',
        'ausência': '부재',
        'de políticas': '정책',
        'imigratórias': '이민',
        'eficazes': '효과적',
        'incentivo': '인센티브',
        'à': '로',
        'escassez': '부족',
        'empreendedorismo': '기업가 정신',
        'para': '로',
        'o': '의',
        'e': '그리고',
        'falta': '부족',
    },
    'he': {  # Hebraico
        'qualidade': 'איכות',
        'relativa': 'יחסית',
        'incipiente': 'בראשית',
        'dos': 'של',
        'ambientes': 'סביבות',
        'de': 'של',
        'inovação': 'חדשנות',
        'boa': 'טוב יותר',
        'parte': 'חלק',
        'deficiências': 'חסרונות',
        'estruturais': 'מבנייים',
        'na': 'ב',
        'educação': 'חינוך',
        'stem': 'STEM',
        'lacunas': 'פערים',
        'em': 'ב',
        'letramento': 'אוריינות',
        'digital': 'דיגיטלי',
        'ia': 'בינה מלאכותית',
        'ausência': 'היעדרות',
        'de políticas': 'מדיניות',
        'imigratórias': 'הגירה',
        'eficazes': 'יעילה',
        'incentivo': 'תמריץ',
        'à': 'ל',
        'escassez': 'מחסור',
        'empreendedorismo': 'יזמות',
        'para': 'ל',
        'o': 'ה',
        'e': 'ו',
        'falta': 'מחסור',
    },
    'it': {  # Italiano
        'ausência': 'assenza',
        'de': 'di',
        'políticas': 'politiche',
        'claras': 'chiare',
        'sobre': 'su',
        'governança': 'governance',
        'e': 'e',
        'soberania': 'sovranità',
        'dados': 'dati',
        'a': 'la',
        'regulamentação': 'regolamentazione',
        'stock': 'stock',
        'options': 'options',
        'as': 'le',
        'aversão': 'avversione',
        'ao': 'al',
        'risco': 'rischio',
        'empreendedorismo': 'imprenditorialità',
        'necessidade': 'necessità',
        'cultura': 'cultura',
        'brasileira': 'brasiliana',
        'baixa': 'basso',
        'representatividade': 'rappresentanza',
        'gênero': 'genere',
        'raça': 'razza',
        'o': 'il',
        'ecossistema': 'ecosistema',
        'é': 'è',
        'nível': 'livello',
        'confiança': 'fiducia',
        'para': 'per',
        'geração': 'generazione',
        'negócios': 'affari',
        'internacionalização': 'internazionalizzazione',
        'tamanho': 'dimensione',
        'transferência': 'trasferimento',
        'tecnologia': 'tecnologia',
        'entre': 'tra',
        'universidades': 'università',
        'empresas': 'aziende',
        'barreiras': 'barriere',
        'ao': 'al',
        'capital': 'capitale',
        'estrangeiro': 'straniero',
        'atração': 'attrazione',
        'entrada': 'accesso',
        'compras': 'acquisti',
        'públicas': 'pubbliche',
        'governo': 'governo',
        'maior': 'più grande',
        'bases': 'basi',
        'curriculares': 'curricolari',
        'nacionais': 'nazionali',
        'desatualizadas': 'obsolete',
        'há': 'c\'è',
        'uma': 'un',
        'defasagem': 'ritardo',
        'qualidade': 'qualità',
        'relativa': 'relativa',
        'incipiente': 'nascente',
        'dos': 'dei',
        'ambientes': 'ambienti',
        'inovação': 'innovazione',
        'boa': 'buona',
        'parte': 'parte',
        'deficiências': 'carenze',
        'estruturais': 'strutturali',
        'na': 'nella',
        'educação': 'educazione',
        'stem': 'STEM',
        'lacunas': 'lacune',
        'em': 'in',
        'letramento': 'alfabetizzazione',
        'digital': 'digitale',
        'ia': 'intelligenza artificiale',
        'imigratórias': 'migratorie',
        'eficazes': 'efficaci',
        'incentivo': 'incentivo',
        'à': 'a',
        'escassez': 'scarsità',
        'or': 'o',
        'boas': 'buone',
        'práticas': 'pratiche',
        'programas': 'programmi',
        'iniciativas': 'iniziative',
        'relacionadas': 'correlate',
        'infraestrutura': 'infrastruttura',
    },
}

def obter_queries_por_idioma():
    """Obtém todas as queries únicas por idioma"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    queries_por_idioma = {}

    for idioma in ['ar', 'ja', 'ko', 'he']:
        cursor.execute(
            "SELECT DISTINCT query FROM fila_pesquisas WHERE idioma = ? AND status = 'pendente' ORDER BY query",
            (idioma,)
        )
        queries_por_idioma[idioma] = [r[0] for r in cursor.fetchall()]

    conn.close()
    return queries_por_idioma

def traduzir_texto_simples(texto, idioma, dicionario):
    """
    Traduz um texto de forma simples substituindo palavras-chave.
    Mantém a estrutura original e substitui palavras do dicionário.
    """
    palavras = texto.lower().split()
    palavras_traduzidas = []

    for palavra in palavras:
        # Remover pontuação
        palavra_limpa = palavra.strip('.,!?;:')

        # Procurar no dicionário
        if palavra_limpa in dicionario.get(idioma, {}):
            traducao = dicionario[idioma][palavra_limpa]
            if traducao:  # Só adicionar se não estiver vazia
                palavras_traduzidas.append(traducao)
        else:
            # Se não encontrar, manter a palavra original (pode ser nomes próprios)
            if palavra_limpa:
                palavras_traduzidas.append(palavra_limpa)

    return ' '.join(palavras_traduzidas)

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

def processar_idioma(idioma, queries_unicas):
    """Processa tradução para um idioma"""
    print(f"\n{'='*70}")
    print(f"Processando {idioma.upper()}")
    print(f"{'='*70}")

    if not queries_unicas:
        print(f"✓ Nenhuma query pendente")
        return 0

    print(f"Encontradas {len(queries_unicas)} queries únicas")

    dicionario = DICIONARIO_TRADUCOES
    traducoes_map = {}

    for i, query in enumerate(queries_unicas, 1):
        if i % 50 == 0:
            print(f"  [{i}/{len(queries_unicas)}] Traduzindo...")

        traducao = traduzir_texto_simples(query, idioma, dicionario)
        if traducao and traducao != query:
            traducoes_map[query] = traducao

    print(f"\n✓ {len(traducoes_map)} queries traduzidas")

    # Atualizar banco
    if traducoes_map:
        print(f"Atualizando banco de dados...")
        atualizadas = atualizar_banco(idioma, traducoes_map)
        print(f"✓ {atualizadas} queries atualizadas")
    else:
        print(f"✗ Nenhuma tradução foi realizada")
        atualizadas = 0

    return atualizadas

def verificar_status_traducoes():
    """Verifica quantas queries de cada idioma estão traduzidas"""
    print("\n" + "="*70)
    print("Status final das queries por idioma:")
    print("="*70)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    idiomas = ['ar', 'ja', 'ko', 'he', 'it']

    for idioma in idiomas:
        cursor.execute(
            "SELECT COUNT(DISTINCT query) FROM fila_pesquisas WHERE idioma = ? AND status = 'pendente'",
            (idioma,)
        )
        total = cursor.fetchone()[0]
        print(f"{idioma.upper()}: {total:4} queries")

    conn.close()

def main():
    print("Script de Tradução com Dicionário Contextual")
    print("="*70)

    queries_por_idioma = obter_queries_por_idioma()

    total_atualizadas = 0

    for idioma in ['ar', 'ja', 'ko', 'he', 'it']:
        atualizadas = processar_idioma(idioma, queries_por_idioma.get(idioma, []))
        total_atualizadas += atualizadas

    print(f"\n{'='*70}")
    print(f"✓ Total de queries atualizadas: {total_atualizadas}")
    print(f"{'='*70}")

    verificar_status_traducoes()

if __name__ == "__main__":
    main()
