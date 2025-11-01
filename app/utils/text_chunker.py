# -*- coding: utf-8 -*-
"""
Chunking inteligente de texto para RAG
Limpa espacos extras, respeita limites de frases e adiciona overlap
"""
import re
from typing import List


def clean_text(text: str) -> str:
    """
    Limpa texto removendo espacos extras entre letras (problema de OCR)
    Suporta caracteres Unicode de todos os idiomas (português, espanhol, árabe, hebraico, japonês, coreano, etc)

    Args:
        text: Texto a ser limpo

    Returns:
        Texto limpo
    """
    # Padrao 1: Remover espacos entre letras INDIVIDUAIS (caracteres isolados)
    # Ex: "n o v e m b r o" -> "novembro", "t er" -> "ter"
    # Ex multilíngua: "e s p a ñ o l" -> "español", "한 국 어" -> "한국어"
    # Detecta: espacos entre letras quando ha 2+ letras isoladas em sequencia
    # Evita quebrar palavras normais preservando espacos entre palavras completas
    def fix_spaced_letters(match_obj):
        # Pegar o texto e remover espacos
        return match_obj.group(0).replace(' ', '')

    # Procurar padroes como "t er", "r ecebe", "v ai" (2+ letras com espacos)
    # REGEX com suporte Unicode: \w em modo UNICODE = letras de qualquer idioma
    # Usa word boundary para nao pegar palavras normais
    text = re.sub(r'\b([\w]\s){1,}[\w]\b', fix_spaced_letters, text, flags=re.UNICODE)

    # Padrao 2: Remover espacos multiplos
    text = re.sub(r'\s{2,}', ' ', text)

    # Padrao 3: Remover espacos antes de pontuacao (suporta pontuação Unicode)
    # Incluindo pontuação árabe (،), japonesa (。、), etc
    text = re.sub(r'\s+([\.,;:!?\u060C\u3002\u3001])', r'\1', text, flags=re.UNICODE)

    # Padrao 4: Remover espacos no inicio e fim
    text = text.strip()

    return text


def split_into_sentences(text: str) -> List[str]:
    """
    Divide texto em frases de forma inteligente
    Suporta múltiplos idiomas: português, espanhol, inglês, árabe, hebraico, japonês, coreano, etc

    Args:
        text: Texto a ser dividido

    Returns:
        Lista de frases
    """
    # Padrao para detectar fim de frase com suporte multilíngue:
    # - Pontuação ocidental: . ! ?
    # - Pontuação árabe: ؟ (question mark) ۔ (period)
    # - Pontuação japonesa: 。(period) ！(exclamation) ？(question)
    # - Pontuação chinesa/coreana: 。！？
    # Seguidos de espaco e letra maiuscula Unicode (qualquer alfabeto)
    sentence_pattern = r'(?<=[.!?\u061F\u06D4\u3002\uFF01\uFF1F])\s+(?=\p{Lu})'

    # Python re não suporta \p{Lu} nativamente, usar alternativa:
    # Detectar letra maiúscula Unicode com categoria de caracteres
    # Usar lookbehind para pontuação + lookahead para maiúsculas de qualquer idioma
    sentence_pattern = r'(?<=[.!?\u061F\u06D4\u3002\uFF01\uFF1F])\s+(?=[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸĀĂĄĆĈĊČĎĐĒĔĖĘĚĜĞĠĢĤĦĨĪĬĮIĴĶĹĻĽĿŁŃŅŇŊŌŎŐŒŔŖŘŚŜŞŠŢŤŦŨŪŬŮŰŲŴŶŹŻŽ\u0400-\u04FF\u0600-\u06FF\u0590-\u05FF\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF])'

    sentences = re.split(sentence_pattern, text, flags=re.UNICODE)

    # Limpar frases vazias
    sentences = [s.strip() for s in sentences if s.strip()]

    return sentences


def create_smart_chunks(
    text: str,
    chunk_size: int = 1500,
    overlap: int = 300,
    clean: bool = True
) -> List[str]:
    """
    Cria chunks inteligentes respeitando limites de frases
    Otimizado para RAG de alta qualidade

    Args:
        text: Texto a ser dividido em chunks
        chunk_size: Tamanho maximo do chunk em caracteres (default: 1500 para melhor contexto)
        overlap: Numero de caracteres de overlap entre chunks (default: 300 para continuidade)
        clean: Se True, limpa o texto antes de dividir

    Returns:
        Lista de chunks
    """
    # Limpar texto se solicitado
    if clean:
        text = clean_text(text)

    # Se o texto for menor que chunk_size, retornar como esta
    if len(text) <= chunk_size:
        return [text]

    # Dividir em sentencas
    sentences = split_into_sentences(text)

    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence)

        # Se adicionar esta frase ultrapassar o limite
        if current_length + sentence_length > chunk_size and current_chunk:
            # Salvar chunk atual
            chunk_text = ' '.join(current_chunk)
            chunks.append(chunk_text)

            # Comecar novo chunk com overlap
            # Pegar ultimas frases ate preencher o overlap
            overlap_sentences = []
            overlap_length = 0

            for s in reversed(current_chunk):
                if overlap_length + len(s) <= overlap:
                    overlap_sentences.insert(0, s)
                    overlap_length += len(s)
                else:
                    break

            current_chunk = overlap_sentences
            current_length = overlap_length

        # Adicionar frase ao chunk atual
        current_chunk.append(sentence)
        current_length += sentence_length

    # Adicionar ultimo chunk se houver conteudo
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        chunks.append(chunk_text)

    return chunks


def chunk_text_simple(text: str, chunk_size: int = 1500) -> List[str]:
    """
    Chunking simples sem overlap (retrocompatibilidade)

    Args:
        text: Texto a ser dividido
        chunk_size: Tamanho de cada chunk

    Returns:
        Lista de chunks
    """
    chunks = [
        text[i:i + chunk_size]
        for i in range(0, len(text), chunk_size)
    ]
    return chunks
