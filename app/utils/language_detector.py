# -*- coding: utf-8 -*-
"""
Detector de idioma para validar idioma dos resultados
Usa heurísticas simples baseadas em palavras-chave conhecidas
"""
from typing import Tuple

# Palavras-chave em português (comuns em textos portugueses)
PORTUGUESE_KEYWORDS = {
    'o', 'a', 'que', 'de', 'e', 'é', 'para', 'em', 'com', 'foi',
    'se', 'não', 'da', 'do', 'este', 'essa', 'você', 'também',
    'pelo', 'pela', 'pelos', 'pelas', 'mais', 'como', 'mas',
    'seu', 'sua', 'seus', 'suas', 'qual', 'quais', 'quando',
    'onde', 'qual', 'quem', 'quantos', 'quanto', 'como',
    'português', 'brasil', 'brasileiro', 'brasileira',
    'são', 'estar', 'poder', 'dever', 'ir', 'vir', 'fazer',
    'dia', 'dias', 'ano', 'anos', 'mes', 'mês', 'hora', 'horas',
    'novo', 'nova', 'novos', 'novas', 'grande', 'pequeno',
    'bom', 'mau', 'ruim', 'melhor', 'pior', 'igual', 'diferente',
    'tal', 'mesmo', 'próprio', 'certo', 'errado', 'verdadeiro',
    'importante', 'necessário', 'possível', 'impossível',
}

# Palavras-chave em inglês
ENGLISH_KEYWORDS = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have',
    'i', 'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you',
    'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they',
    'we', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one',
    'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out',
    'if', 'about', 'who', 'get', 'which', 'go', 'me', 'when',
    'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know',
    'take', 'people', 'into', 'year', 'your', 'good', 'some',
    'could', 'them', 'see', 'other', 'than', 'then', 'now',
    'look', 'only', 'come', 'its', 'over', 'think', 'also',
}

# Palavras-chave em espanhol
SPANISH_KEYWORDS = {
    'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'ser', 'se',
    'no', 'haber', 'por', 'con', 'su', 'para', 'es', 'como',
    'estar', 'tener', 'le', 'lo', 'todo', 'pero', 'más', 'hacer',
    'o', 'poder', 'decir', 'este', 'ir', 'otro', 'ese', 'la',
    'si', 'me', 'ya', 'ver', 'porque', 'dar', 'cuando', 'él',
    'muy', 'sin', 'vez', 'mucho', 'saber', 'qué', 'sobre', 'mi',
    'alguno', 'mismo', 'yo', 'también', 'hasta', 'año', 'dos',
    'querer', 'entre', 'así', 'primero', 'desde', 'grande', 'eso',
    'ni', 'nos', 'durante', 'estado', 'todos', 'uno', 'les',
    'español', 'españa', 'español', 'mexicano', 'argentina',
}

# Palavras-chave em francês
FRENCH_KEYWORDS = {
    'de', 'le', 'et', 'à', 'un', 'en', 'que', 'pour', 'est',
    'par', 'se', 'pas', 'plus', 'pouvoir', 'ne', 'sur', 'être',
    'ce', 'dit', 'dans', 'ont', 'qui', 'du', 'qui', 'avec', 'la',
    'il', 'vous', 'faire', 'des', 'au', 'dire', 'aller', 'lui',
    'me', 'monde', 'temps', 'venir', 'dire', 'peut', 'tout',
    'année', 'montrer', 'sans', 'autre', 'tant', 'bien', 'même',
    'cas', 'jour', 'homme', 'fois', 'nouveau', 'part', 'où',
    'français', 'france', 'paris', 'monsieur', 'madame',
}

# Palavras-chave em alemão
GERMAN_KEYWORDS = {
    'der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit',
    'sich', 'des', 'auf', 'für', 'ist', 'im', 'dem', 'nicht',
    'ein', 'die', 'eine', 'als', 'auch', 'es', 'an', 'werden',
    'aus', 'er', 'hat', 'dass', 'sie', 'nach', 'wird', 'bei',
    'einer', 'um', 'am', 'sind', 'noch', 'wie', 'einem', 'über',
    'einen', 'so', 'zum', 'war', 'haben', 'nur', 'oder', 'aber',
    'deutsch', 'deutschland', 'berlin', 'münchen', 'hamburg',
}

# Palavras-chave em italiano
ITALIAN_KEYWORDS = {
    'di', 'il', 'che', 'e', 'la', 'per', 'un', 'in', 'è', 'una',
    'con', 'del', 'da', 'non', 'si', 'della', 'dei', 'le', 'delle',
    'dei', 'al', 'alla', 'sono', 'anche', 'degli', 'agli', 'alle',
    'come', 'ma', 'più', 'nel', 'nella', 'essere', 'suo', 'sua',
    'questo', 'hanno', 'aveva', 'loro', 'fare', 'può', 'quando',
    'italia', 'italiano', 'italiana', 'roma', 'milano', 'venezia',
}

LANGUAGE_KEYWORDS = {
    'pt': PORTUGUESE_KEYWORDS,
    'en': ENGLISH_KEYWORDS,
    'es': SPANISH_KEYWORDS,
    'fr': FRENCH_KEYWORDS,
    'de': GERMAN_KEYWORDS,
    'it': ITALIAN_KEYWORDS,
}


def detectar_idioma(texto: str) -> Tuple[str, float]:
    """
    Detecta o idioma de um texto baseado em palavras-chave.

    Args:
        texto: Texto para detectar idioma

    Returns:
        Tuple com (codigo_idioma, confianca)
        confianca: valor entre 0 e 1 indicando a certeza da detecção
    """
    if not texto:
        return 'unknown', 0.0

    # Limpar e normalizar texto
    texto_lower = texto.lower()
    palavras = texto_lower.split()

    # Se muito curto, confiança baixa
    if len(palavras) < 3:
        return 'unknown', 0.0

    # Contar ocorrências de palavras-chave por idioma
    scores = {}
    total_palavras = len(palavras)

    for idioma, keywords in LANGUAGE_KEYWORDS.items():
        matches = sum(1 for palavra in palavras if palavra in keywords)
        score = matches / total_palavras if total_palavras > 0 else 0
        scores[idioma] = score

    # Encontrar idioma com maior score
    if scores:
        idioma_detectado = max(scores, key=scores.get)
        confianca = scores[idioma_detectado]

        # Retornar resultado só se confiança mínima
        if confianca >= 0.10:  # Mínimo 10% de palavras-chave
            return idioma_detectado, confianca

    return 'unknown', 0.0


def validar_idioma_resultado(
    titulo: str,
    descricao: str,
    idioma_esperado: str,
    threshold_confianca: float = 0.15
) -> Tuple[bool, str, float]:
    """
    Valida se um resultado está no idioma esperado.

    Args:
        titulo: Título do resultado
        descricao: Descrição/conteúdo do resultado
        idioma_esperado: Código do idioma esperado (pt, en, es, etc)
        threshold_confianca: Mínimo de confiança para considerar válido

    Returns:
        Tuple com (eh_valido, idioma_detectado, confianca)
        eh_valido: True se o resultado está no idioma esperado
    """
    # Combinar título e descrição para melhor detecção
    texto_completo = f"{titulo} {descricao}"

    idioma_detectado, confianca = detectar_idioma(texto_completo)

    # Resultado é válido se:
    # 1. Idioma detectado corresponde ao esperado
    # 2. Ou a confiança é muito baixa (texto muito curto/ambíguo)
    eh_valido = (idioma_detectado == idioma_esperado or
                 idioma_detectado == 'unknown')

    return eh_valido, idioma_detectado, confianca


def gerar_relatorio_idiomas(resultados: list) -> dict:
    """
    Gera relatório sobre idiomas dos resultados vs esperado.

    Args:
        resultados: Lista de dicts com titulo, descricao, idioma

    Returns:
        Dict com estatísticas de idiomas
    """
    problematicos = []
    validos = []

    for res in resultados:
        titulo = res.get('titulo', '')
        descricao = res.get('descricao', '')
        idioma_esperado = res.get('idioma', 'pt')

        eh_valido, idioma_det, confianca = validar_idioma_resultado(
            titulo, descricao, idioma_esperado
        )

        if not eh_valido and idioma_det != 'unknown':
            problematicos.append({
                'id': res.get('id'),
                'idioma_esperado': idioma_esperado,
                'idioma_detectado': idioma_det,
                'confianca': confianca,
                'titulo': titulo[:50]
            })
        else:
            validos.append(res.get('id'))

    return {
        'total': len(resultados),
        'validos': len(validos),
        'problematicos': len(problematicos),
        'percentual_problematico': round((len(problematicos) / len(resultados) * 100), 2) if resultados else 0,
        'exemplos_problematicos': problematicos[:10],
        'ids_problematicos': [p['id'] for p in problematicos]
    }
