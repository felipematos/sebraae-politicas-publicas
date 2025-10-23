#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Tradução de Resultados

Traduz todos os resultados não-português para português, mantendo o conteúdo original.

Executa:
1. Identifica resultados que ainda não têm tradução para português
2. Traduz título e descrição via OpenRouter (modelos gratuitos)
3. Armazena traduções nos campos titulo_pt e descricao_pt
4. Mantém conteúdo original intacto
"""

import asyncio
import sys
from pathlib import Path

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import (
    db,
    traduzir_todos_resultados,
)


async def main():
    """Executa o processo completo de tradução"""

    print("\n" + "=" * 80)
    print(" " * 20 + "TRADUÇÃO DE RESULTADOS PARA PORTUGUÊS")
    print("=" * 80 + "\n")

    try:
        # Verificar quantos resultados precisam de tradução
        resultados_sem_traducao = await db.fetch_all("""
            SELECT COUNT(*) as total FROM resultados_pesquisa
            WHERE idioma != 'pt'
            AND (titulo_pt IS NULL OR descricao_pt IS NULL)
        """)

        total_sem_traducao = resultados_sem_traducao[0]['total']

        print(f"[ANÁLISE] Resultados que precisam tradução: {total_sem_traducao}")

        if total_sem_traducao == 0:
            print("\n✓ Todos os resultados já possuem tradução para português!")
            return True

        # Iniciar tradução
        print("\n[TRADUÇÃO] Iniciando processo de tradução...")
        print("-" * 80)
        stats_traducao = await traduzir_todos_resultados()

        print(f"\n[RESULTADO]")
        print(f"  Total processados: {stats_traducao['total_processados']}")
        print(f"  Traduzidos com sucesso: {stats_traducao['traduzidos']}")
        print(f"  Falhados: {stats_traducao['falhados']}")

        # Resumo final
        print("\n" + "=" * 80)
        print(" " * 30 + "✅ PROCESSO CONCLUÍDO")
        print("=" * 80 + "\n")

        print(f"[RESUMO EXECUTIVO]")
        print(f"  Total de resultados traduzidos: {stats_traducao['traduzidos']}")
        print(f"  Falhas na tradução: {stats_traducao['falhados']}")
        print(f"  Taxa de sucesso: {(stats_traducao['traduzidos'] / max(stats_traducao['total_processados'], 1) * 100):.1f}%")
        print()

        return stats_traducao['sucesso']

    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
