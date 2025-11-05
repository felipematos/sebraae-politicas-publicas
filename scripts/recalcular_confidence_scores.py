#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para recalcular confidence scores de resultados existentes
usando traduções em português para garantir avaliação justa
"""
import asyncio
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from app.database import Database
from app.agente.avaliador import Avaliador


async def recalcular_scores():
    """
    Recalcula confidence scores de todos os resultados existentes
    usando as traduções quando disponíveis
    """
    db = Database()

    # Buscar todos os resultados
    print("[RECALCULAR] Buscando resultados...")
    resultados = await db.fetch_all(
        """
        SELECT
            id, falha_id, titulo, descricao, fonte_url, fonte_tipo,
            idioma, confidence_score, num_ocorrencias, query,
            titulo_pt, descricao_pt
        FROM resultados_pesquisa
        ORDER BY id
        """
    )

    print(f"[RECALCULAR] Encontrados {len(resultados)} resultados")

    # Inicializar avaliador
    avaliador = Avaliador()

    # Contadores
    total = len(resultados)
    atualizados = 0
    mantidos = 0
    sem_query = 0
    erros = 0

    # Processar cada resultado
    for i, resultado in enumerate(resultados, 1):
        try:
            # Verificar se tem query (necessária para cálculo)
            query = resultado.get('query')
            if not query:
                sem_query += 1
                if i % 100 == 0:
                    print(f"[RECALCULAR] Progresso: {i}/{total} (sem query: {sem_query})")
                continue

            # Preparar dicionário do resultado para avaliador
            resultado_dict = {
                'titulo': resultado['titulo'],
                'descricao': resultado['descricao'],
                'url': resultado['fonte_url'],
                'fonte': resultado.get('fonte_tipo', 'unknown'),
                'idioma': resultado.get('idioma', 'pt'),
                'titulo_pt': resultado.get('titulo_pt'),
                'descricao_pt': resultado.get('descricao_pt')
            }

            # Calcular novo score usando traduções
            novo_score = await avaliador.avaliar(
                resultado=resultado_dict,
                query=query,
                num_ocorrencias=resultado.get('num_ocorrencias', 1)
            )

            # Verificar se houve mudança significativa
            score_antigo = resultado.get('confidence_score', 0.5)
            diferenca = abs(novo_score - score_antigo)

            # Atualizar se diferença >= 0.01 (1%)
            if diferenca >= 0.01:
                await db.execute(
                    """
                    UPDATE resultados_pesquisa
                    SET confidence_score = ?,
                        atualizado_em = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (novo_score, resultado['id'])
                )
                atualizados += 1

                # Log de mudanças significativas (>= 0.1 = 10%)
                if diferenca >= 0.1:
                    idioma = resultado.get('idioma', 'pt')
                    tem_traducao = bool(resultado.get('titulo_pt') or resultado.get('descricao_pt'))
                    print(f"\n[RECALCULAR] ID {resultado['id']} ({idioma}{'*' if tem_traducao else ''}): "
                          f"{score_antigo:.3f} -> {novo_score:.3f} (Δ {diferenca:.3f})")
                    print(f"  Título: {resultado['titulo'][:60]}...")
            else:
                mantidos += 1

            # Log de progresso
            if i % 100 == 0:
                print(f"[RECALCULAR] Progresso: {i}/{total} "
                      f"(atualizados: {atualizados}, mantidos: {mantidos}, "
                      f"sem query: {sem_query})")

        except Exception as e:
            erros += 1
            print(f"[RECALCULAR] Erro no resultado {resultado['id']}: {e}")

    # Resumo final
    print(f"\n[RECALCULAR] ===== RESUMO =====")
    print(f"Total de resultados: {total}")
    print(f"Atualizados: {atualizados} ({atualizados/total*100:.1f}%)")
    print(f"Mantidos: {mantidos} ({mantidos/total*100:.1f}%)")
    print(f"Sem query: {sem_query} ({sem_query/total*100:.1f}%)")
    print(f"Erros: {erros}")

    # Estatísticas por idioma
    print(f"\n[RECALCULAR] ===== POR IDIOMA =====")
    stats_idioma = await db.fetch_all(
        """
        SELECT
            idioma,
            COUNT(*) as total,
            AVG(confidence_score) as media_score,
            COUNT(CASE WHEN titulo_pt IS NOT NULL OR descricao_pt IS NOT NULL THEN 1 END) as com_traducao
        FROM resultados_pesquisa
        GROUP BY idioma
        ORDER BY total DESC
        """
    )

    for stat in stats_idioma:
        idioma = stat['idioma'] or 'unknown'
        total_idioma = stat['total']
        media = stat['media_score']
        com_trad = stat['com_traducao']
        perc_trad = com_trad / total_idioma * 100 if total_idioma > 0 else 0

        print(f"{idioma:8s}: {total_idioma:5d} resultados, "
              f"média {media:.3f}, "
              f"{com_trad:5d} traduzidos ({perc_trad:.1f}%)")


async def main():
    """Função principal"""
    print("[RECALCULAR] Iniciando recálculo de confidence scores...")
    print("[RECALCULAR] Usando traduções para resultados em outros idiomas\n")

    await recalcular_scores()

    print("\n[RECALCULAR] Concluído!")


if __name__ == "__main__":
    asyncio.run(main())
