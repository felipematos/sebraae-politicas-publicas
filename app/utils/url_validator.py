# -*- coding: utf-8 -*-
"""
Validador e filtro de URLs para resultados de pesquisa.
Remove URLs de mecanismos de pesquisa e valida URLs de conteúdo original.
"""
from typing import Set, Tuple
from urllib.parse import urlparse
import re


# Domínios de mecanismos de pesquisa e ferramentas que NÃO devem ser fonte_url
SEARCH_ENGINE_DOMAINS = {
    'perplexity.ai',
    'www.perplexity.ai',
    'api.perplexity.ai',
    'tavily.com',
    'www.tavily.com',
    'api.tavily.com',
    'serper.dev',
    'api.serper.dev',
    'jina.ai',
    'api.jina.ai',
    'r.jina.ai',
    'exa.ai',
    'api.exa.ai',
    'deep-research.ai',
    'api.deep-research.ai',
    'google.com',
    'www.google.com',
    'search.google.com',
    'translate.google.com',
    'bing.com',
    'www.bing.com',
}

# Padrões de URL de placeholder ou stub
PLACEHOLDER_PATTERNS = [
    r'^https?://example\.com($|/)',  # Apenas example.com com ou sem caminho
    r'^https?://deep-research\.example\.com',  # Deep research placeholder
    r'^https?://placeholder\.',
    r'^https?://stub\.',
    r'^https?://\{.*\}',  # Placeholders com chaves
]


def extrair_dominio(url: str) -> str:
    """Extrai o domínio de uma URL."""
    try:
        parsed = urlparse(url)
        dominio = parsed.netloc.lower()
        # Remove www. se presente
        if dominio.startswith('www.'):
            dominio = dominio[4:]
        return dominio
    except Exception:
        return ""


def eh_url_mecanismo_pesquisa(url: str) -> bool:
    """
    Verifica se a URL é de um mecanismo de pesquisa ou ferramenta de busca.

    Args:
        url: URL a validar

    Returns:
        True se é URL de mecanismo de pesquisa, False caso contrário
    """
    if not url or not isinstance(url, str):
        return False

    url_lower = url.lower()

    # Verificar domínios conhecidos (correspondência exata)
    dominio = extrair_dominio(url)
    if dominio in SEARCH_ENGINE_DOMAINS:
        return True

    # Verificar se é domínio com mecanismo de busca (apenas domínios base, não subdomínios)
    for engine_domain in SEARCH_ENGINE_DOMAINS:
        # Apenas se o domínio corresponde exatamente ou é subdomain direto
        if dominio == engine_domain or dominio.endswith('.' + engine_domain):
            return True

    # Verificar padrões de placeholder
    for pattern in PLACEHOLDER_PATTERNS:
        if re.match(pattern, url_lower):
            return True

    return False


def eh_url_valida(url: str) -> bool:
    """
    Verifica se uma URL é válida (tem formato correto e não é de mecanismo).

    Args:
        url: URL a validar

    Returns:
        True se é URL válida, False caso contrário
    """
    if not url or not isinstance(url, str):
        return False

    url = url.strip()

    # Deve começar com http:// ou https://
    if not (url.startswith('http://') or url.startswith('https://')):
        return False

    # Verificar se é URL de mecanismo de pesquisa
    if eh_url_mecanismo_pesquisa(url):
        return False

    # Deve ter um domínio válido
    dominio = extrair_dominio(url)
    if not dominio or len(dominio) < 3:
        return False

    # Deve ter um ponto no domínio (exceto localhost)
    if '.' not in dominio and dominio != 'localhost':
        return False

    return True


def classificar_urls(urls: Set[str]) -> Tuple[Set[str], Set[str], Set[str]]:
    """
    Classifica URLs em válidas, inválidas e de mecanismo de pesquisa.

    Args:
        urls: Set de URLs para classificar

    Returns:
        Tuple com (urls_validas, urls_invalidas, urls_mecanismo)
    """
    validas = set()
    invalidas = set()
    mecanismo = set()

    for url in urls:
        if not url:
            invalidas.add(url)
        elif eh_url_mecanismo_pesquisa(url):
            mecanismo.add(url)
        elif eh_url_valida(url):
            validas.add(url)
        else:
            invalidas.add(url)

    return validas, invalidas, mecanismo


def gerar_relatorio_urls(urls: Set[str]) -> dict:
    """
    Gera um relatório detalhado sobre as URLs.

    Args:
        urls: Set de URLs para analisar

    Returns:
        Dict com estatísticas e exemplos
    """
    validas, invalidas, mecanismo = classificar_urls(urls)

    return {
        'total': len(urls),
        'validas': {
            'count': len(validas),
            'exemplos': list(validas)[:5]
        },
        'invalidas': {
            'count': len(invalidas),
            'exemplos': list(invalidas)[:5]
        },
        'mecanismo_pesquisa': {
            'count': len(mecanismo),
            'exemplos': list(mecanismo)[:5]
        },
        'percentual_validas': round((len(validas) / len(urls) * 100) if urls else 0, 2)
    }
