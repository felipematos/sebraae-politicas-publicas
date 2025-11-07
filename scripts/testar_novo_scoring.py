#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar o novo sistema de scoring antes de aplicar em massa
Verifica os casos problemáticos identificados e mostra o impacto das mudanças
"""
import asyncio
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.database import Database
from app.agente.avaliador import Avaliador


async def testar_casos_problematicos():
    """
    Testa o novo scoring nos casos problemáticos identificados:
    1. Meta-respostas de APIs (240 resultados)
    2. Resultados "não encontrado"
    3. Resultados em hebraico com conteúdo irrelevante
    """
    db = Database()
    avaliador = Avaliador()

    print("=" * 80)
    print("TESTE DO NOVO SISTEMA DE SCORING")
    print("=" * 80)

    # Teste 1: Meta-respostas de APIs
    print("\n" + "=" * 80)
    print("TESTE 1: Meta-respostas de APIs")
    print("=" * 80)

    meta_respostas = await db.fetch_all(
        """
        SELECT
            id, titulo, descricao, confidence_score, query, idioma,
            titulo_pt, descricao_pt, fonte_tipo
        FROM resultados_pesquisa
        WHERE titulo LIKE 'Here are%'
           OR titulo LIKE 'Voici %'
           OR titulo LIKE 'Ecco %'
           OR titulo LIKE '%fuentes relevantes%'
           OR titulo LIKE 'Aquí tienes%'
        ORDER BY confidence_score DESC
        LIMIT 10
        """
    )

    print(f"\nEncontradas {len(meta_respostas)} meta-respostas para testar")
    print("\nTestando primeiros 10 casos:")

    for resultado in meta_respostas:
        resultado_dict = {
            'titulo': resultado['titulo'],
            'descricao': resultado['descricao'],
            'url': '',
            'fonte': resultado.get('fonte_tipo', 'unknown'),
            'idioma': resultado.get('idioma', 'pt'),
            'titulo_pt': resultado.get('titulo_pt'),
            'descricao_pt': resultado.get('descricao_pt')
        }

        novo_score = await avaliador.avaliar(
            resultado=resultado_dict,
            query=resultado.get('query', ''),
            num_ocorrencias=1
        )

        score_antigo = resultado['confidence_score']
        diferenca = novo_score - score_antigo
        print(f"\nID {resultado['id']} ({resultado['idioma']})")
        print(f"  Score antigo: {score_antigo:.3f}")
        print(f"  Score novo:   {novo_score:.3f}")
        print(f"  Diferença:    {diferenca:+.3f} ({diferenca/score_antigo*100:+.1f}%)")
        print(f"  Título: {resultado['titulo'][:70]}...")

    # Teste 2: Resultado "não encontrado" específico (ID 21634)
    print("\n" + "=" * 80)
    print("TESTE 2: Resultado 'não encontrado' (ID 21634 - hebraico)")
    print("=" * 80)

    resultado_vazio = await db.fetch_one(
        """
        SELECT
            id, titulo, descricao, confidence_score, query, idioma,
            titulo_pt, descricao_pt, fonte_tipo
        FROM resultados_pesquisa
        WHERE id = 21634
        """
    )

    if resultado_vazio:
        resultado_dict = {
            'titulo': resultado_vazio['titulo'],
            'descricao': resultado_vazio['descricao'],
            'url': '',
            'fonte': resultado_vazio.get('fonte_tipo', 'unknown'),
            'idioma': resultado_vazio.get('idioma', 'pt'),
            'titulo_pt': resultado_vazio.get('titulo_pt'),
            'descricao_pt': resultado_vazio.get('descricao_pt')
        }

        novo_score = await avaliador.avaliar(
            resultado=resultado_dict,
            query=resultado_vazio.get('query', ''),
            num_ocorrencias=resultado_vazio.get('num_ocorrencias', 1)
        )

        score_antigo = resultado_vazio['confidence_score']
        diferenca = novo_score - score_antigo

        print(f"\nID {resultado_vazio['id']} - Caso reportado pelo usuário")
        print(f"  Score antigo: {score_antigo:.3f}")
        print(f"  Score novo:   {novo_score:.3f}")
        print(f"  Diferença:    {diferenca:+.3f} ({diferenca/score_antigo*100:+.1f}%)")
        print(f"  Título (PT): {resultado_vazio['titulo_pt'][:100]}")
        print(f"  Descrição (PT): {resultado_vazio['descricao_pt'][:150]}...")

    # Teste 3: Estatísticas gerais dos resultados em hebraico
    print("\n" + "=" * 80)
    print("TESTE 3: Resultados em hebraico (he)")
    print("=" * 80)

    resultados_he = await db.fetch_all(
        """
        SELECT
            id, titulo, descricao, confidence_score, query, idioma,
            titulo_pt, descricao_pt, fonte_tipo
        FROM resultados_pesquisa
        WHERE idioma = 'he'
        ORDER BY confidence_score DESC
        LIMIT 5
        """
    )

    print(f"\nTestando 5 resultados em hebraico com scores mais altos:")

    for resultado in resultados_he:
        resultado_dict = {
            'titulo': resultado['titulo'],
            'descricao': resultado['descricao'],
            'url': '',
            'fonte': resultado.get('fonte_tipo', 'unknown'),
            'idioma': resultado.get('idioma', 'pt'),
            'titulo_pt': resultado.get('titulo_pt'),
            'descricao_pt': resultado.get('descricao_pt')
        }

        novo_score = await avaliador.avaliar(
            resultado=resultado_dict,
            query=resultado.get('query', ''),
            num_ocorrencias=1
        )

        score_antigo = resultado['confidence_score']
        diferenca = novo_score - score_antigo
        print(f"\nID {resultado['id']}")
        print(f"  Score antigo: {score_antigo:.3f}")
        print(f"  Score novo:   {novo_score:.3f}")
        print(f"  Diferença:    {diferenca:+.3f} ({diferenca/score_antigo*100:+.1f}%)")
        if resultado.get('titulo_pt'):
            print(f"  Título (PT): {resultado['titulo_pt'][:80]}...")

    # Estatísticas de impacto
    print("\n" + "=" * 80)
    print("ESTATÍSTICAS DE IMPACTO DAS MUDANÇAS")
    print("=" * 80)

    # Contar quantos resultados serão afetados significativamente
    print("\n[INFO] Calculando estatísticas de todos os resultados...")
    print("[INFO] Isso pode levar alguns minutos...\n")

    total_stats = {
        'total': 0,
        'meta_respostas': 0,
        'conteudo_vazio': 0,
        'ambos': 0,
        'sem_problemas': 0
    }

    # Buscar todos os resultados para análise
    todos = await db.fetch_all(
        """
        SELECT
            id, titulo, descricao, titulo_pt, descricao_pt
        FROM resultados_pesquisa
        """
    )

    from app.agente.avaliador import detectar_meta_resposta, detectar_conteudo_vazio

    for resultado in todos:
        total_stats['total'] += 1

        resultado_dict = {
            'titulo': resultado['titulo'],
            'descricao': resultado['descricao'],
            'titulo_pt': resultado.get('titulo_pt'),
            'descricao_pt': resultado.get('descricao_pt')
        }

        eh_meta = detectar_meta_resposta(resultado_dict)
        eh_vazio = detectar_conteudo_vazio(resultado_dict)

        if eh_meta and eh_vazio:
            total_stats['ambos'] += 1
        elif eh_meta:
            total_stats['meta_respostas'] += 1
        elif eh_vazio:
            total_stats['conteudo_vazio'] += 1
        else:
            total_stats['sem_problemas'] += 1

    print(f"Total de resultados: {total_stats['total']}")
    print(f"  • Meta-respostas apenas: {total_stats['meta_respostas']} "
          f"({total_stats['meta_respostas']/total_stats['total']*100:.1f}%) - Penalização: -70%")
    print(f"  • Conteúdo vazio apenas: {total_stats['conteudo_vazio']} "
          f"({total_stats['conteudo_vazio']/total_stats['total']*100:.1f}%) - Penalização: -80%")
    print(f"  • Ambos os problemas: {total_stats['ambos']} "
          f"({total_stats['ambos']/total_stats['total']*100:.1f}%) - Penalização: -95%")
    print(f"  • Sem problemas detectados: {total_stats['sem_problemas']} "
          f"({total_stats['sem_problemas']/total_stats['total']*100:.1f}%)")

    total_afetados = total_stats['meta_respostas'] + total_stats['conteudo_vazio'] + total_stats['ambos']
    print(f"\n✓ Total de resultados que serão penalizados: {total_afetados} "
          f"({total_afetados/total_stats['total']*100:.1f}%)")

    print("\n" + "=" * 80)
    print("TESTE CONCLUÍDO")
    print("=" * 80)


async def main():
    """Função principal"""
    await testar_casos_problematicos()


if __name__ == "__main__":
    asyncio.run(main())
