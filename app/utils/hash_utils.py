# -*- coding: utf-8 -*-
"""
Utilitarios para hashing de conteudo
"""
import hashlib


def gerar_hash_conteudo(titulo: str, descricao: str, fonte: str) -> str:
    """
    Gera hash SHA256 de conteudo normalizado para deduplicacao

    Args:
        titulo: Titulo do resultado
        descricao: Descricao/resumo
        fonte: URL da fonte

    Returns:
        Hash SHA256 em hexadecimal
    """
    # Normalizar texto (lowercase, strip, remove multiplos espacos)
    texto_normalizado = f"{titulo.lower().strip()} {descricao.lower().strip()}"
    texto_normalizado = " ".join(texto_normalizado.split())

    # Gerar hash
    hash_obj = hashlib.sha256(texto_normalizado.encode('utf-8'))
    return hash_obj.hexdigest()
