#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tradução agressiva e completa com dicionário MUITO mais expandido.
"""
import sqlite3
import re

DB_PATH = "falhas_mercado_v1.db"

# Dicionário ENORME com TODAS as palavras encontradas nas queries
DICT_GRANDE = {
    'ar': {
        'ausência': 'غياب',
        'de': 'من',
        'políticas': 'سياسات',
        'claras': 'واضحة',
        'sobre': 'حول',
        'governança': 'الحوكمة',
        'e': 'و',
        'soberania': 'السيادة',
        'dados': 'البيانات',
        'a': 'لـ',
        'dificuldade': 'صعوبة',
        'na': 'في',
        'continuidade': 'الاستمرارية',
        'públicas': 'عامة',
        'entre': 'بين',
        'gestões': 'الإدارات',
        'uma': 'واحد',
        'das': 'من',
        'grandes': 'كبير',
        'politica': 'السياسة',
        'pública': 'العامة',
        'para': 'ل',
        'or': 'أو',
        'boas': 'جيدة',
        'práticas': 'ممارسات',
        'programas': 'برامج',
        'iniciativas': 'مبادرات',
        'relacionadas': 'ذات الصلة',
        'a:': 'ل:',
        'infraestrutura': 'البنية التحتية',
        'apoio': 'دعم',
        'à': 'لـ',
        'exportação': 'التصدير',
        'comercialização': 'التسويق',
        'descentralização': 'اللامركزية',
        'educação': 'التعليم',
        'empreendedora': 'الريادية',
        'empreendedorismo': 'ريادة الأعمال',
        'como': 'مثل',
        'resolver': 'حل',
        'grandis': 'كبيرة',
        'aziendi': 'الشركات',
        'têm': 'لديها',
        'regras': 'قواعد',
        'di': 'من',
        'compliance': 'الامتثال',
        'internas': 'الداخلية',
        'compras': 'المشتريات',
        'pouco': 'قليلة',
        'refere-se': 'يشير إلى',
        'à': 'إلى',
        'uma': 'واحد',
        'questão': 'مسألة',
        'que': 'أن',
        'Brasil': 'البرازيل',
    },
    'ja': {
        'ausência': '不在',
        'de': 'の',
        'políticas': 'ポリシー',
        'claras': '明確',
        'sobre': 'について',
        'governança': 'ガバナンス',
        'e': 'と',
        'soberania': '主権',
        'dados': 'データ',
        'a': 'へ',
        'dificuldade': '困難',
        'na': 'で',
        'continuidade': '継続性',
        'públicas': '公共',
        'entre': 'の間',
        'gestões': 'ガバナンス',
        'uma': 'ひとつ',
        'das': 'の',
        'grandes': '大きい',
        'politica': 'ポリシー',
        'pública': '公開',
        'para': 'のため',
        'or': 'または',
        'boas': '良い',
        'práticas': 'ベストプラクティス',
        'programas': 'プログラム',
        'iniciativas': 'イニシアチブ',
        'relacionadas': '関連',
        'a:': 'へ:',
        'infraestrutura': 'インフラ',
        'apoio': 'サポート',
        'à': 'へ',
        'exportação': '輸出',
        'comercialização': 'マーケティング',
        'descentralização': '分散化',
        'educação': '教育',
        'empreendedora': '起業家',
        'empreendedorismo': '起業精神',
        'como': 'など',
        'resolver': '解決',
        'grandis': '大きな',
        'aziendi': '会社',
        'têm': '持っている',
        'regras': 'ルール',
        'di': 'の',
        'compliance': 'コンプライアンス',
        'internas': '内部',
        'compras': '購入',
        'pouco': '少し',
        'refere-se': '指す',
        'uma': '1',
        'questão': '質問',
        'que': 'その',
        'Brasil': 'ブラジル',
    },
    'ko': {
        'ausência': '부재',
        'de': '의',
        'políticas': '정책',
        'claras': '명확한',
        'sobre': '에 대해',
        'governança': '거버넌스',
        'e': '그리고',
        'soberania': '주권',
        'dados': '데이터',
        'a': '로',
        'dificuldade': '어려움',
        'na': '에서',
        'continuidade': '연속성',
        'públicas': '공공',
        'entre': '사이',
        'gestões': '관리',
        'uma': '하나',
        'das': '의',
        'grandes': '큰',
        'politica': '정책',
        'pública': '공개',
        'para': '위해',
        'or': '또는',
        'boas': '좋은',
        'práticas': '관행',
        'programas': '프로그램',
        'iniciativas': '이니셔티브',
        'relacionadas': '관련',
        'a:': '로:',
        'infraestrutura': '기반시설',
        'apoio': '지원',
        'à': '로',
        'exportação': '수출',
        'comercialização': '마케팅',
        'descentralização': '분산화',
        'educação': '교육',
        'empreendedora': '기업가적',
        'empreendedorismo': '기업가정신',
        'como': '같은',
        'resolver': '해결',
        'grandis': '큰',
        'aziendi': '회사',
        'têm': '가지다',
        'regras': '규칙',
        'di': '의',
        'compliance': '준수',
        'internas': '내부',
        'compras': '구매',
        'pouco': '적다',
        'refere-se': '지칭',
        'uma': '한',
        'questão': '질문',
        'que': '그',
        'Brasil': '브라질',
    },
    'he': {
        'ausência': 'היעדרות',
        'de': 'של',
        'políticas': 'מדיניות',
        'claras': 'ברורות',
        'sobre': 'על',
        'governança': 'ניהול',
        'e': 'ו',
        'soberania': 'ריבונות',
        'dados': 'נתונים',
        'a': 'ל',
        'dificuldade': 'קושי',
        'na': 'ב',
        'continuidade': 'המשכיות',
        'públicas': 'ציבוריות',
        'entre': 'בין',
        'gestões': 'ניהול',
        'uma': 'אחד',
        'das': 'של',
        'grandes': 'גדול',
        'politica': 'מדיניות',
        'pública': 'ציבורית',
        'para': 'ל',
        'or': 'או',
        'boas': 'טוב',
        'práticas': 'שיטות',
        'programas': 'תוכניות',
        'iniciativas': 'יוזמות',
        'relacionadas': 'קשור',
        'a:': 'ל:',
        'infraestrutura': 'תשתיות',
        'apoio': 'תמיכה',
        'à': 'ל',
        'exportação': 'ייצוא',
        'comercialização': 'שיווק',
        'descentralização': 'ביזור',
        'educação': 'חינוך',
        'empreendedora': 'יזמית',
        'empreendedorismo': 'יזמות',
        'como': 'כמו',
        'resolver': 'לפתור',
        'grandis': 'גדול',
        'aziendi': 'חברות',
        'têm': 'יש',
        'regras': 'כללים',
        'di': 'של',
        'compliance': 'ציות',
        'internas': 'פנימי',
        'compras': 'רכישות',
        'pouco': 'מעט',
        'refere-se': 'מתייחס',
        'uma': 'אחד',
        'questão': 'שאלה',
        'que': 'ש',
        'Brasil': 'ברזיל',
    },
    'it': {
        'ausência': 'assenza',
        'de': 'di',
        'políticas': 'politiche',
        'claras': 'chiare',
        'sobre': 'su',
        'governança': 'governance',
        'e': 'e',
        'soberania': 'sovranità',
        'dados': 'dati',
        'a': 'a',
        'dificuldade': 'difficoltà',
        'na': 'nella',
        'continuidade': 'continuità',
        'públicas': 'pubbliche',
        'entre': 'tra',
        'gestões': 'gestioni',
        'uma': 'una',
        'das': 'delle',
        'grandes': 'grandi',
        'politica': 'politica',
        'pública': 'pubblica',
        'para': 'per',
        'or': 'o',
        'boas': 'buone',
        'práticas': 'pratiche',
        'programas': 'programmi',
        'iniciativas': 'iniziative',
        'relacionadas': 'correlate',
        'a:': 'a:',
        'infraestrutura': 'infrastruttura',
        'apoio': 'supporto',
        'à': 'alla',
        'exportação': 'esportazione',
        'comercialização': 'commercializzazione',
        'descentralização': 'decentralizzazione',
        'educação': 'educazione',
        'empreendedora': 'imprenditoriale',
        'empreendedorismo': 'imprenditorialità',
        'como': 'come',
        'resolver': 'risolvere',
        'grandis': 'grandi',
        'aziendi': 'aziende',
        'têm': 'hanno',
        'regras': 'regole',
        'di': 'di',
        'compliance': 'compliance',
        'internas': 'interne',
        'compras': 'acquisti',
        'pouco': 'poco',
        'refere-se': 'si riferisce',
        'uma': 'una',
        'questão': 'questione',
        'que': 'che',
        'Brasil': 'Brasile',
    },
}

def traduzir_query_agressivo(query, idioma):
    """Traduz uma query substituindo todas as palavras encontradas no dicionário"""
    resultado = query.lower()
    
    # Ordenar por comprimento decrescente para evitar substituições parciais
    pares = sorted(DICT_GRANDE.get(idioma, {}).items(), key=lambda x: len(x[0]), reverse=True)
    
    for pt, trad in pares:
        # Substituir de forma case-insensitive mas mantendo a capitalização original
        padrao = r'\b' + re.escape(pt) + r'\b'
        if re.search(padrao, resultado, re.IGNORECASE):
            resultado = re.sub(padrao, trad, resultado, flags=re.IGNORECASE)
    
    # Capitalizar primeira letra
    if resultado:
        resultado = resultado[0].upper() + resultado[1:]
    
    return resultado

def atualizar_queries():
    """Atualiza todas as queries com tradução agressiva"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total_atualizadas = 0
    
    for idioma in ['ar', 'ja', 'ko', 'he', 'it']:
        print(f"\nProcessando {idioma.upper()}...")
        
        cursor.execute(
            "SELECT DISTINCT query FROM fila_pesquisas WHERE idioma = ? AND status = 'pendente' AND query LIKE '%políticas%'",
            (idioma,)
        )
        
        queries = [r[0] for r in cursor.fetchall()]
        atualizadas_idioma = 0
        
        for query in queries:
            query_traduzida = traduzir_query_agressivo(query, idioma)
            
            if query_traduzida != query.lower():
                cursor.execute(
                    "UPDATE fila_pesquisas SET query = ? WHERE idioma = ? AND query = ? AND status = 'pendente'",
                    (query_traduzida, idioma, query)
                )
                atualizadas_idioma += cursor.rowcount
        
        print(f"  ✓ {atualizadas_idioma} queries atualizadas")
        total_atualizadas += atualizadas_idioma
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Total: {total_atualizadas} queries corrigidas")

if __name__ == "__main__":
    atualizar_queries()
