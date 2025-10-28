#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar o preenchimento de traduções com alguns registros
"""
import asyncio
import sys
sys.path.insert(0, '/Users/felipematossardinhapinto/Library/CloudStorage/GoogleDrive-Felipe@felipematos.net/My Drive/10K/Projetos/2025/Sebrae Nacional/Code')

from app.database import db
from app.utils.idiomas import traduzir_query


async def test_backfill():
    """Testa preenchimento de traduções com 2-3 registros"""
    print("=" * 80)
    print("TESTE DE PREENCHIMENTO DE TRADUÇÕES (2-3 REGISTROS)")
    print("=" * 80)

    try:
        # Buscar apenas 3 resultados não-portugueses com traduções faltantes
        print("\n📊 Buscando 3 resultados não-portugueses com traduções faltantes...")
        resultados = await db.fetch_all("""
            SELECT id, titulo, descricao, idioma
            FROM resultados_pesquisa
            WHERE idioma != 'pt' AND (titulo_pt IS NULL OR descricao_pt IS NULL OR titulo_en IS NULL OR descricao_en IS NULL)
            LIMIT 3
        """)

        total = len(resultados)
        print(f"   Encontrados: {total} resultados para testar")

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

            print(f"\n🔄 Processando resultado {i}/{total} (ID: {resultado_id}, idioma: {idioma})")
            print(f"   Título original: {titulo[:50]}...")
            print(f"   Descrição original: {descricao[:50]}...")

            try:
                atualizacoes = {}

                # Traduzir para português
                if titulo:
                    print(f"   → Traduzindo título para PT...")
                    atualizacoes['titulo_pt'] = await traduzir_query(titulo, idioma, 'pt')
                if descricao:
                    print(f"   → Traduzindo descrição para PT...")
                    atualizacoes['descricao_pt'] = await traduzir_query(descricao, idioma, 'pt')

                # Traduzir para inglês (ou usar original se já é inglês)
                if idioma == 'en':
                    # Se já é inglês, usar o original
                    if titulo:
                        atualizacoes['titulo_en'] = titulo
                    if descricao:
                        atualizacoes['descricao_en'] = descricao
                    print(f"   → Usando original para EN (já é inglês)")
                else:
                    # Traduzir para inglês
                    if titulo:
                        print(f"   → Traduzindo título para EN...")
                        atualizacoes['titulo_en'] = await traduzir_query(titulo, idioma, 'en')
                    if descricao:
                        print(f"   → Traduzindo descrição para EN...")
                        atualizacoes['descricao_en'] = await traduzir_query(descricao, idioma, 'en')

                # Atualizar no banco se houver traduções
                if atualizacoes:
                    campos = ', '.join([f'{k} = ?' for k in atualizacoes.keys()])
                    valores = tuple(list(atualizacoes.values()) + [resultado_id])

                    await db.execute(
                        f"UPDATE resultados_pesquisa SET {campos} WHERE id = ?",
                        valores
                    )
                    processados += 1
                    print(f"   ✅ Atualizado: {', '.join(atualizacoes.keys())}")

            except Exception as e:
                erros += 1
                print(f"   ❌ Erro ao traduzir resultado {resultado_id}: {str(e)[:100]}")
                continue

        print(f"\n{'=' * 80}")
        print(f"✅ Teste concluído!")
        print(f"   Total: {total}")
        print(f"   Traduzidos: {processados}")
        print(f"   Erros: {erros}")
        print("=" * 80)

        # Mostrar os resultados atualizados
        if processados > 0:
            print("\n📋 Verificando resultados atualizados no banco:")
            resultado_ids = tuple(r['id'] for r in resultados[:3])
            resultados_atualizados = await db.fetch_all(f"""
                SELECT id, titulo_pt, titulo_en, descricao_pt, descricao_en
                FROM resultados_pesquisa
                WHERE id IN ({','.join('?' * len(resultado_ids))})
            """, resultado_ids)

            for res in resultados_atualizados:
                print(f"\nID {res['id']}:")
                print(f"  PT título: {res['titulo_pt'][:50] if res['titulo_pt'] else 'NULL'}...")
                print(f"  EN título: {res['titulo_en'][:50] if res['titulo_en'] else 'NULL'}...")

    except Exception as e:
        print(f"\n❌ Erro crítico: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_backfill())
