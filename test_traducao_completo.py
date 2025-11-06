#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste COMPLETO de tradução para garantir salvamento correto no banco

Este teste verifica:
1. Resultados em PT detectados corretamente (não traduzidos)
2. Resultados em EN/ES traduzidos para PT (com tradução real)
3. Traduções diferentes do original
4. Salvamento correto no banco de dados
"""
import asyncio
import sys
from app.database import db
from app.integracao.openrouter_api import OpenRouterClient
from app.utils.logger import logger


async def testar_traducao_completo():
    """
    Teste completo de tradução com verificação de salvamento
    """
    try:
        logger.info("=" * 80)
        logger.info("TESTE COMPLETO DE TRADUÇÃO E SALVAMENTO NO BANCO")
        logger.info("=" * 80)

        # TESTE 1: Buscar resultados marcados como ES mas que estão em PT
        logger.info("\n📊 TESTE 1: Resultados em PT detectados incorretamente como ES")
        logger.info("-" * 80)

        query_pt_incorreto = """
        SELECT id, falha_id, titulo, descricao, idioma, titulo_pt, descricao_pt
        FROM resultados_pesquisa
        WHERE idioma = 'es'
        AND (titulo LIKE '%brasil%' OR titulo LIKE '%educação%' OR titulo LIKE '%inovação%')
        LIMIT 2
        """

        resultados_pt = await db.fetch_all(query_pt_incorreto)
        logger.info(f"✓ Encontrados {len(resultados_pt)} resultados em PT marcados como ES\n")

        # TESTE 2: Buscar resultados REALMENTE em inglês
        logger.info("\n📊 TESTE 2: Resultados REAIS em inglês (precisam tradução)")
        logger.info("-" * 80)

        query_en_real = """
        SELECT id, falha_id, titulo, descricao, idioma, titulo_pt, descricao_pt
        FROM resultados_pesquisa
        WHERE idioma = 'en'
        AND titulo NOT LIKE '%brasil%'
        AND titulo NOT LIKE '%educação%'
        AND (titulo LIKE '%innovation%' OR titulo LIKE '%startup%' OR titulo LIKE '%technology%')
        LIMIT 2
        """

        resultados_en = await db.fetch_all(query_en_real)
        logger.info(f"✓ Encontrados {len(resultados_en)} resultados em inglês\n")

        if len(resultados_pt) == 0 and len(resultados_en) == 0:
            logger.warning("⚠️  Nenhum resultado encontrado para testar!")
            return

        # Processar resultados
        async with OpenRouterClient() as client:
            total_testados = 0
            pt_detectados = 0
            traducoes_feitas = 0
            erros = 0

            # PROCESSAR RESULTADOS EM PT (detectados incorretamente)
            for resultado in resultados_pt:
                total_testados += 1
                resultado_dict = dict(resultado)

                logger.info(f"\n{'=' * 80}")
                logger.info(f"TESTE {total_testados} - ID: {resultado_dict['id']}")
                logger.info(f"{'=' * 80}")
                logger.info(f"Idioma no banco: {resultado_dict['idioma']}")
                logger.info(f"Título original: {resultado_dict['titulo'][:100]}...")

                # Traduzir título
                resultado_titulo = await client.traduzir_texto_com_deteccao(
                    texto=resultado_dict['titulo'],
                    idioma_alvo="pt",
                    idioma_origem=resultado_dict['idioma']
                )

                # Traduzir descrição
                resultado_descricao = await client.traduzir_texto_com_deteccao(
                    texto=resultado_dict['descricao'],
                    idioma_alvo="pt",
                    idioma_origem=resultado_dict['idioma']
                )

                titulo_pt = resultado_titulo.get("traducao")
                idioma_detectado = resultado_titulo.get("idioma_real")

                logger.info(f"✓ Idioma detectado: {idioma_detectado}")
                logger.info(f"✓ Título traduzido: {titulo_pt[:100]}...")

                # VERIFICAR: Se detectou PT, título deve ser igual ao original
                if idioma_detectado == "pt":
                    pt_detectados += 1
                    if titulo_pt == resultado_dict['titulo']:
                        logger.info("✓ CORRETO: Texto em PT não foi alterado")
                    else:
                        logger.warning("⚠️  AVISO: Texto em PT foi modificado!")

                # Salvar no banco
                await db.execute(
                    """
                    UPDATE resultados_pesquisa
                    SET titulo_pt = ?, descricao_pt = ?, idioma = ?, atualizado_em = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (titulo_pt.strip(), resultado_descricao.get("traducao").strip(),
                     idioma_detectado, resultado_dict['id'])
                )
                logger.info(f"💾 Salvo no banco")

            # PROCESSAR RESULTADOS EM INGLÊS (precisam tradução)
            for resultado in resultados_en:
                total_testados += 1
                resultado_dict = dict(resultado)

                logger.info(f"\n{'=' * 80}")
                logger.info(f"TESTE {total_testados} - ID: {resultado_dict['id']}")
                logger.info(f"{'=' * 80}")
                logger.info(f"Idioma no banco: {resultado_dict['idioma']}")
                logger.info(f"Título ORIGINAL (EN): {resultado_dict['titulo'][:100]}...")

                # Traduzir título
                resultado_titulo = await client.traduzir_texto_com_deteccao(
                    texto=resultado_dict['titulo'],
                    idioma_alvo="pt",
                    idioma_origem=resultado_dict['idioma']
                )

                # Traduzir descrição
                resultado_descricao = await client.traduzir_texto_com_deteccao(
                    texto=resultado_dict['descricao'],
                    idioma_alvo="pt",
                    idioma_origem=resultado_dict['idioma']
                )

                titulo_pt = resultado_titulo.get("traducao")
                descricao_pt = resultado_descricao.get("traducao")
                idioma_detectado = resultado_titulo.get("idioma_real")

                logger.info(f"✓ Idioma detectado: {idioma_detectado}")
                logger.info(f"✓ Título TRADUZIDO (PT): {titulo_pt[:100]}...")

                # VERIFICAÇÃO CRÍTICA: Tradução deve ser diferente do original
                if titulo_pt != resultado_dict['titulo']:
                    traducoes_feitas += 1
                    logger.info("✅ SUCESSO: Tradução é diferente do original!")
                else:
                    erros += 1
                    logger.error("❌ ERRO: Tradução é igual ao original (não traduziu)!")

                # Salvar no banco
                await db.execute(
                    """
                    UPDATE resultados_pesquisa
                    SET titulo_pt = ?, descricao_pt = ?, idioma = ?, atualizado_em = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (titulo_pt.strip(), descricao_pt.strip(), idioma_detectado, resultado_dict['id'])
                )
                logger.info(f"💾 Salvo no banco")

                # VERIFICAR NO BANCO SE FOI SALVO CORRETAMENTE
                verificacao = await db.fetch_one(
                    "SELECT titulo, titulo_pt, idioma FROM resultados_pesquisa WHERE id = ?",
                    (resultado_dict['id'],)
                )

                if verificacao:
                    logger.info(f"\n🔍 VERIFICAÇÃO NO BANCO:")
                    logger.info(f"   Título original: {verificacao['titulo'][:80]}...")
                    logger.info(f"   Título PT salvo: {verificacao['titulo_pt'][:80]}...")
                    logger.info(f"   Idioma salvo: {verificacao['idioma']}")

                    if verificacao['titulo_pt'] != verificacao['titulo']:
                        logger.info(f"   ✅ CONFIRMADO: Tradução diferente salva corretamente!")
                    else:
                        logger.error(f"   ❌ PROBLEMA: Tradução igual ao original no banco!")

        # RESUMO FINAL
        logger.info(f"\n{'=' * 80}")
        logger.info("📊 RESUMO DO TESTE")
        logger.info(f"{'=' * 80}")
        logger.info(f"Total testados: {total_testados}")
        logger.info(f"PT detectados corretamente: {pt_detectados}")
        logger.info(f"Traduções feitas com sucesso: {traducoes_feitas}")
        logger.info(f"Erros (não traduziu): {erros}")

        if erros > 0:
            logger.error(f"\n❌ ATENÇÃO: {erros} resultados não foram traduzidos corretamente!")
            logger.error("   NÃO EXECUTE refazer todas as traduções até corrigir este problema!")
            sys.exit(1)
        else:
            logger.info(f"\n✅ TESTE PASSOU! Sistema está traduzindo e salvando corretamente!")
            logger.info("   É SEGURO executar 'Refazer Todas as Traduções'")

    except Exception as e:
        logger.error(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(testar_traducao_completo())
