#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste para validar tradução com detecção de idioma

Testa o novo método traduzir_texto_com_deteccao() que:
1. Detecta o idioma real do texto
2. Traduz para português
3. Retorna ambos (tradução + idioma detectado)
"""
import asyncio
import sys
from app.database import db
from app.integracao.openrouter_api import OpenRouterClient
from app.utils.logger import logger


async def testar_traducao_pequeno_lote():
    """
    Testa tradução em um pequeno lote de resultados
    """
    try:
        logger.info("=" * 80)
        logger.info("TESTE DE TRADUÇÃO COM DETECÇÃO DE IDIOMA")
        logger.info("=" * 80)

        # Buscar 5 resultados marcados como "es" mas que podem estar em PT
        query = """
        SELECT id, falha_id, titulo, descricao, idioma, titulo_pt, descricao_pt
        FROM resultados_pesquisa
        WHERE idioma = 'es'
        AND titulo = titulo_pt
        LIMIT 5
        """

        resultados = await db.fetch_all(query)
        logger.info(f"\n📊 Encontrados {len(resultados)} resultados para testar")
        logger.info(f"   (Resultados marcados como ES mas com título = tradução)\n")

        if len(resultados) == 0:
            logger.info("✓ Nenhum resultado com problema encontrado!")
            return

        # Processar cada resultado
        async with OpenRouterClient() as client:
            for i, resultado in enumerate(resultados, 1):
                resultado_dict = dict(resultado)

                logger.info(f"\n{'=' * 80}")
                logger.info(f"TESTE {i}/{len(resultados)} - ID: {resultado_dict['id']}")
                logger.info(f"{'=' * 80}")
                logger.info(f"Idioma no banco: {resultado_dict['idioma']}")
                logger.info(f"Título original: {resultado_dict['titulo'][:100]}...")
                logger.info(f"Título traduzido: {resultado_dict['titulo_pt'][:100] if resultado_dict['titulo_pt'] else 'N/A'}...")

                # Testar detecção de idioma + tradução no TÍTULO
                logger.info(f"\n🔍 Testando detecção de idioma + tradução do TÍTULO...")
                resultado_titulo = await client.traduzir_texto_com_deteccao(
                    texto=resultado_dict['titulo'],
                    idioma_alvo="pt",
                    idioma_origem=resultado_dict['idioma']
                )

                idioma_detectado_titulo = resultado_titulo.get("idioma_real")
                traducao_titulo = resultado_titulo.get("traducao")

                logger.info(f"✓ Idioma detectado: {idioma_detectado_titulo}")
                logger.info(f"✓ Tradução: {traducao_titulo[:100]}...")

                # Testar detecção de idioma + tradução na DESCRIÇÃO
                logger.info(f"\n🔍 Testando detecção de idioma + tradução da DESCRIÇÃO...")
                resultado_descricao = await client.traduzir_texto_com_deteccao(
                    texto=resultado_dict['descricao'],
                    idioma_alvo="pt",
                    idioma_origem=resultado_dict['idioma']
                )

                idioma_detectado_descricao = resultado_descricao.get("idioma_real")
                traducao_descricao = resultado_descricao.get("traducao")

                logger.info(f"✓ Idioma detectado: {idioma_detectado_descricao}")
                logger.info(f"✓ Tradução: {traducao_descricao[:100]}...")

                # Verificar se precisa corrigir idioma
                idioma_correto = idioma_detectado_titulo
                idioma_mudou = idioma_correto != resultado_dict['idioma']

                if idioma_mudou:
                    logger.info(f"\n⚠️  CORREÇÃO NECESSÁRIA!")
                    logger.info(f"   Idioma no banco: {resultado_dict['idioma']}")
                    logger.info(f"   Idioma real: {idioma_correto}")

                    # Atualizar no banco (modo DRY-RUN para teste)
                    logger.info(f"\n💾 Atualizando no banco...")
                    await db.execute(
                        """
                        UPDATE resultados_pesquisa
                        SET titulo_pt = ?, descricao_pt = ?, idioma = ?, atualizado_em = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (traducao_titulo.strip(), traducao_descricao.strip(), idioma_correto, resultado_dict['id'])
                    )
                    logger.info(f"✓ Atualizado: ID {resultado_dict['id']}")
                    logger.info(f"  - Idioma: {resultado_dict['idioma']} -> {idioma_correto}")
                    logger.info(f"  - Título traduzido: {traducao_titulo[:80]}...")
                    logger.info(f"  - Descrição traduzida: {traducao_descricao[:80]}...")
                else:
                    logger.info(f"\n✓ Idioma correto! Apenas atualizando traduções...")
                    await db.execute(
                        """
                        UPDATE resultados_pesquisa
                        SET titulo_pt = ?, descricao_pt = ?, atualizado_em = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (traducao_titulo.strip(), traducao_descricao.strip(), resultado_dict['id'])
                    )
                    logger.info(f"✓ Traduções atualizadas: ID {resultado_dict['id']}")

        logger.info(f"\n{'=' * 80}")
        logger.info("✓ TESTE CONCLUÍDO COM SUCESSO!")
        logger.info(f"{'=' * 80}\n")

    except Exception as e:
        logger.error(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(testar_traducao_pequeno_lote())
