#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corrigir títulos dos resultados da Perplexity no banco de dados
Extrai o título correto que está entre pipes "|" na descrição
"""

import sqlite3
import re
from typing import Tuple, Optional


def extrair_titulo_da_descricao(descricao: str) -> Tuple[Optional[str], str]:
    """
    Extrai o título da descrição se estiver entre pipes

    Args:
        descricao: Descrição atual (pode conter: | Título | URL | Outros |)

    Returns:
        Tupla (titulo_extraido, descricao_limpa)
    """
    if not descricao or "|" not in descricao:
        return None, descricao

    # Separar por pipes
    partes = [p.strip() for p in descricao.split("|")]

    # Filtrar partes vazias e partes que contêm URLs
    partes_sem_url = [p for p in partes if p and "http" not in p.lower()]

    if not partes_sem_url:
        return None, descricao

    # Primeira parte não-vazia é o título
    titulo_extraido = partes_sem_url[0]

    # Restante é a descrição
    if len(partes_sem_url) > 1:
        descricao_limpa = " ".join(partes_sem_url[1:])
    else:
        descricao_limpa = titulo_extraido

    return titulo_extraido, descricao_limpa


def corrigir_titulos_perplexity(db_path: str = "falhas_mercado_v1.db"):
    """
    Corrige os títulos dos resultados da Perplexity no banco de dados
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Buscar todos os resultados da Perplexity
    cursor.execute("""
        SELECT id, titulo, descricao
        FROM resultados_pesquisa
        WHERE ferramenta_origem = 'perplexity'
    """)

    resultados = cursor.fetchall()
    total = len(resultados)
    print(f"Encontrados {total} resultados da Perplexity para corrigir")

    atualizados = 0
    ignorados = 0

    for result_id, titulo_atual, descricao_atual in resultados:
        # Verificar se o título precisa ser corrigido
        # Títulos problemáticos: "Resultado Perplexity", "Resultado Perplexidade", etc.
        # Ou títulos que são apenas pipes: "|---|---|"
        precisa_corrigir = (
            "resultado perpl" in titulo_atual.lower() or
            titulo_atual.strip().startswith("|") or
            len(titulo_atual.strip()) < 5
        )

        # Tentar extrair título da descrição
        titulo_extraido, descricao_limpa = extrair_titulo_da_descricao(descricao_atual)

        if precisa_corrigir and titulo_extraido:
            # Atualizar o registro
            cursor.execute("""
                UPDATE resultados_pesquisa
                SET titulo = ?, descricao = ?, atualizado_em = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (titulo_extraido, descricao_limpa, result_id))
            atualizados += 1

            if atualizados <= 5:  # Mostrar os primeiros 5 exemplos
                print(f"\n[{result_id}] Atualizado:")
                print(f"  Título antigo: {titulo_atual[:80]}...")
                print(f"  Título novo: {titulo_extraido[:80]}...")
        else:
            ignorados += 1

    conn.commit()
    conn.close()

    print(f"\n{'='*60}")
    print(f"Correção concluída!")
    print(f"  Total processados: {total}")
    print(f"  Atualizados: {atualizados}")
    print(f"  Ignorados (já corretos): {ignorados}")
    print(f"{'='*60}")


if __name__ == "__main__":
    print("Iniciando correção de títulos da Perplexity...")
    print("=" * 60)
    corrigir_titulos_perplexity()
