#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para preencher traduções faltantes nos resultados existentes.
Este script traduz títulos e descrições para PT e EN nos resultados que estão NULL.
"""

import asyncio
import sys
sys.path.insert(0, '/Users/felipematossardinhapinto/Library/CloudStorage/GoogleDrive-Felipe@felipematos.net/My Drive/10K/Projetos/2025/Sebrae Nacional/Code')

from app.database import db
from app.utils.idiomas import traduzir_query


async def preencher_traducoes():
    """Preenche traduções faltantes nos resultados do banco de dados"""
    print("=" * 80)
    print("PREENCHENDO TRADUÇÕES FALTANTES NOS RESULTADOS")
    print("=" * 80)

    try:
        # Conectar ao banco
        await db.initialize()

        # Buscar todos os resultados com traduções faltantes
        print("\n📊 Buscando resultados com traduções faltantes...")
        resultados = await db.fetch_all("""
            SELECT id, titulo, descricao, idioma
            FROM resultados_pesquisa
            WHERE (titulo_pt IS NULL OR descricao_pt IS NULL OR titulo_en IS NULL OR descricao_en IS NULL)
            ORDER BY id DESC
        """)

        total = len(resultados)
        print(f"   Encontrados: {total} resultados para traduzir")

        if total == 0:
            print("\n✅ Nenhuma tradução faltante encontrada!")
            return

        # Processar cada resultado
        processados = 0
        erros = 0

        for i, resultado in enumerate(resultados, 1):
            resultado_id = resultado['id']
            titulo = resultado['titulo']
            descricao = resultado['descricao']
            idioma = resultado['idioma']

            try:
                atualizacoes = {}

                # Traduzir para português se necessário
                if idioma != 'pt':
                    if titulo:
                        atualizacoes['titulo_pt'] = await traduzir_query(titulo, idioma, 'pt')
                    if descricao:
                        atualizacoes['descricao_pt'] = await traduzir_query(descricao, idioma, 'pt')

                # Traduzir para inglês se necessário
                if idioma != 'en':
                    if titulo:
                        atualizacoes['titulo_en'] = await traduzir_query(titulo, idioma, 'en')
                    if descricao:
                        atualizacoes['descricao_en'] = await traduzir_query(descricao, idioma, 'en')
                else:
                    # Se já é inglês
                    if titulo:
                        atualizacoes['titulo_en'] = titulo
                    if descricao:
                        atualizacoes['descricao_en'] = descricao

                # Atualizar no banco se houver traduções
                if atualizacoes:
                    campos = ', '.join([f'{k} = ?' for k in atualizacoes.keys()])
                    valores = list(atualizacoes.values()) + [resultado_id]

                    await db.execute(
                        f"UPDATE resultados_pesquisa SET {campos} WHERE id = ?",
                        valores
                    )
                    processados += 1

                # Mostrar progresso
                if i % 10 == 0:
                    print(f"   Processados: {i}/{total} ({processados} traduzidos)")

            except Exception as e:
                erros += 1
                print(f"   ⚠️ Erro ao traduzir resultado {resultado_id}: {str(e)[:50]}")
                continue

        print(f"\n✅ Processamento concluído!")
        print(f"   Total: {total}")
        print(f"   Traduzidos: {processados}")
        print(f"   Erros: {erros}")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Erro crítico: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(preencher_traducoes())
