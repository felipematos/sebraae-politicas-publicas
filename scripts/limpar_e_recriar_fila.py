#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Limpeza e Recreação da Fila de Pesquisa

Executa:
1. Remove resultados contaminados (português de buscas em outros idiomas)
2. Recria a fila com base nas atualizações:
   - Suporte a 10 idiomas (incluindo Japonês)
   - Múltiplas ferramentas com rotação
   - Queries traduzidas via OpenRouter
"""

import asyncio
import sys
from pathlib import Path

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import (
    db,
    limpar_resultados_contaminados,
    recriar_fila_pesquisa,
)


async def main():
    """Executa o processo completo de limpeza e recreação"""

    print("\n" + "=" * 80)
    print(" " * 20 + "LIMPEZA E RECREAÇÃO DA FILA")
    print("=" * 80 + "\n")

    try:
        # Etapa 1: Limpeza de resultados contaminados
        print("[1/2] Limpando resultados contaminados...")
        print("-" * 80)
        stats_limpeza = await limpar_resultados_contaminados()

        print(f"\n[RESULTADO]")
        print(f"  Total de resultados contaminados identificados: {stats_limpeza['total_contaminados']}")
        print(f"  Resultados deletados: {stats_limpeza['deletados']}")
        print(f"  Entradas de fila restauradas: {stats_limpeza['fila_restaurada']}")

        # Etapa 2: Recreação da fila
        print("\n[2/2] Recriando fila de pesquisa...")
        print("-" * 80)
        stats_fila = await recriar_fila_pesquisa()

        print(f"\n[RESULTADO]")
        print(f"  Resultados preservados: {stats_fila['resultados_preservados']}")
        print(f"  Entradas na fila criada: {stats_fila['fila_criada']}")
        print(f"\n  Distribuição por idioma:")
        for dist in stats_fila['distribuicao']:
            print(f"    {dist['idioma']}: {dist['total']}")

        # Resumo final
        print("\n" + "=" * 80)
        print(" " * 30 + "✅ PROCESSO CONCLUÍDO")
        print("=" * 80 + "\n")

        print(f"[RESUMO EXECUTIVO]")
        print(f"  Resultados contaminados removidos: {stats_limpeza['deletados']}")
        print(f"  Filas restauradas automaticamente: {stats_limpeza['fila_restaurada']}")
        print(f"  Total na fila (nova): {stats_fila['fila_criada']}")
        print(f"  Resultados mantidos: {stats_fila['resultados_preservados']}")
        print(f"  Idiomas suportados: 10 (pt, en, es, fr, de, it, ar, ja, ko, he)")
        print()

        return True

    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
