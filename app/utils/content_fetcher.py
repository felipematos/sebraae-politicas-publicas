# -*- coding: utf-8 -*-
"""
Utilitário para buscar e processar conteúdo de URLs e documentos
"""
import httpx
import re
from typing import Dict, Any, Optional, List
from app.database import obter_conteudo_url_cache, salvar_conteudo_url_cache
from app.utils.logger import logger


async def fetch_url_content_with_cache(url: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Busca conteúdo de URL via Jina.ai com cache em banco de dados

    Args:
        url: URL original a ser buscada
        force_refresh: Se True, ignora cache e busca novamente

    Returns:
        Dict com: {url, content, title, error}
    """
    try:
        # Verificar cache primeiro (a menos que force_refresh)
        if not force_refresh:
            cached = await obter_conteudo_url_cache(url)
            if cached and not cached.get('error'):
                logger.info(f"Usando conteúdo em cache para: {url}")
                return {
                    'url': cached['url'],
                    'content': cached['content'],
                    'title': cached.get('title'),
                    'error': None,
                    'from_cache': True
                }
            elif cached and cached.get('error'):
                logger.warning(f"URL em cache com erro: {url} - {cached['error']}")
                # Continua para tentar buscar novamente

        # Buscar via Jina.ai
        jina_url = f"https://r.jina.ai/{url}"
        logger.info(f"Buscando via Jina.ai: {url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(jina_url)
            response.raise_for_status()

            content = response.text

            # Tentar extrair título (Jina.ai geralmente inclui no início do conteúdo)
            title = extract_title_from_content(content) or url

            # Salvar no cache
            await salvar_conteudo_url_cache(
                url=url,
                content=content,
                title=title,
                error=None
            )

            logger.info(f"Conteúdo buscado e cacheado com sucesso: {url}")

            return {
                'url': url,
                'content': content,
                'title': title,
                'error': None,
                'from_cache': False
            }

    except httpx.HTTPError as e:
        error_msg = f"Erro HTTP ao buscar URL: {str(e)}"
        logger.error(f"{error_msg} - URL: {url}")

        # Salvar erro no cache para não tentar repetidamente
        await salvar_conteudo_url_cache(
            url=url,
            content=None,
            title=None,
            error=error_msg
        )

        return {
            'url': url,
            'content': None,
            'title': None,
            'error': error_msg,
            'from_cache': False
        }

    except Exception as e:
        error_msg = f"Erro inesperado ao buscar URL: {str(e)}"
        logger.error(f"{error_msg} - URL: {url}")

        return {
            'url': url,
            'content': None,
            'title': None,
            'error': error_msg,
            'from_cache': False
        }


def extract_title_from_content(content: str) -> Optional[str]:
    """
    Tenta extrair título do conteúdo retornado pelo Jina.ai
    Jina.ai geralmente coloca o título nas primeiras linhas
    """
    if not content:
        return None

    # Pegar primeiras linhas
    lines = content.split('\n')[:5]

    # Procurar por linha que parece ser título (não vazia, não muito longa)
    for line in lines:
        line = line.strip()
        if line and len(line) < 200 and not line.startswith('http'):
            return line

    return None


def extract_excerpt_soft_cut(
    full_text: str,
    match_position: int,
    before: int = 500,
    after: int = 10000
) -> str:
    """
    Extrai trecho de texto sem cortar no meio de frases ou parágrafos

    Args:
        full_text: Texto completo do documento
        match_position: Posição do match/relevância no texto
        before: Quantidade de caracteres antes do match (aproximado)
        after: Quantidade de caracteres depois do match (aproximado)

    Returns:
        Trecho extraído com cortes suaves em limites de sentenças
    """
    if not full_text:
        return ""

    text_length = len(full_text)

    # Calcular posições iniciais (brutas)
    start_pos = max(0, match_position - before)
    end_pos = min(text_length, match_position + after)

    # Ajustar início para não cortar no meio de frase
    if start_pos > 0:
        # Procurar por delimitadores de sentença antes da posição inicial
        # Ordem de preferência: parágrafo, ponto final, ponto e vírgula
        search_window = full_text[max(0, start_pos - 100):start_pos + 100]

        # Procurar quebra de parágrafo (duas quebras de linha)
        paragraph_break = search_window.rfind('\n\n')
        if paragraph_break != -1:
            start_pos = max(0, start_pos - 100) + paragraph_break + 2
        else:
            # Procurar ponto final seguido de espaço e maiúscula
            sentence_pattern = r'\.\s+[A-ZÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÇ]'
            matches = list(re.finditer(sentence_pattern, search_window))
            if matches:
                last_match = matches[-1]
                start_pos = max(0, start_pos - 100) + last_match.start() + 1
            else:
                # Fallback: procurar qualquer ponto
                last_period = search_window.rfind('. ')
                if last_period != -1:
                    start_pos = max(0, start_pos - 100) + last_period + 2

    # Ajustar fim para não cortar no meio de frase
    if end_pos < text_length:
        # Procurar por delimitadores de sentença depois da posição final
        search_window = full_text[max(0, end_pos - 100):min(text_length, end_pos + 100)]

        # Procurar quebra de parágrafo
        paragraph_break = search_window.find('\n\n')
        if paragraph_break != -1:
            end_pos = max(0, end_pos - 100) + paragraph_break
        else:
            # Procurar ponto final seguido de espaço e maiúscula
            sentence_pattern = r'\.\s+[A-ZÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÇ]'
            match = re.search(sentence_pattern, search_window)
            if match:
                end_pos = max(0, end_pos - 100) + match.start() + 1
            else:
                # Fallback: procurar qualquer ponto
                next_period = search_window.find('. ')
                if next_period != -1:
                    end_pos = max(0, end_pos - 100) + next_period + 1

    # Extrair e limpar trecho
    excerpt = full_text[start_pos:end_pos].strip()

    # Adicionar indicadores de continuação se necessário
    if start_pos > 0:
        excerpt = "... " + excerpt
    if end_pos < text_length:
        excerpt = excerpt + " ..."

    return excerpt


async def enrich_sources_with_full_content(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Enriquece lista de fontes com conteúdo completo de URLs e trechos de documentos

    Args:
        sources: Lista de fontes com estrutura:
            - fonte_tipo: 'pesquisa' ou 'documento'
            - fonte_url: URL (para tipo pesquisa)
            - fonte_conteudo: Conteúdo parcial
            - match_position: Posição do match (para documentos)

    Returns:
        Lista de fontes enriquecidas com:
            - conteudo_completo: Conteúdo completo (URLs) ou trecho (documentos)
            - conteudo_original: Conteúdo original curto
    """
    enriched = []

    for fonte in sources:
        fonte_tipo = fonte.get('fonte_tipo', 'documento')

        if fonte_tipo == 'pesquisa' and fonte.get('fonte_url'):
            # Buscar conteúdo completo da URL via Jina.ai
            url_content = await fetch_url_content_with_cache(fonte['fonte_url'])

            enriched.append({
                **fonte,
                'conteudo_original': fonte.get('fonte_conteudo', ''),
                'conteudo_completo': url_content.get('content') if not url_content.get('error') else None,
                'url_error': url_content.get('error'),
                'url_title': url_content.get('title')
            })

        elif fonte_tipo == 'documento':
            # Para documentos, extrair trecho com soft cut
            # Assumindo que fonte_conteudo já é o texto completo do documento
            # e que há algum indicador de posição relevante

            full_text = fonte.get('fonte_conteudo', '')
            match_position = fonte.get('match_position', len(full_text) // 2)

            excerpt = extract_excerpt_soft_cut(
                full_text=full_text,
                match_position=match_position,
                before=500,
                after=10000
            )

            enriched.append({
                **fonte,
                'conteudo_original': full_text[:500],  # Preview curto
                'conteudo_completo': excerpt
            })

        else:
            # Fonte sem enriquecimento especial
            enriched.append(fonte)

    return enriched
