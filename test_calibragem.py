# -*- coding: utf-8 -*-
"""
Script de teste para validar o sistema de calibragem de priorização
Testa 3 falhas com perfis diferentes
"""
import asyncio
import sys
from app.agente.priorizador import AgentePriorizador
from app.utils.logger import logger

async def testar_calibragem():
    """
    Testa o sistema de calibragem com 3 falhas:
    - Falha 1: Alto impacto, Alto esforço (Educação STEM)
    - Falha 5: Médio impacto, Médio esforço
    - Falha 10: Baixo impacto, Baixo esforço
    """
    priorizador = AgentePriorizador()

    # IDs de teste
    falhas_teste = [1, 5, 10]

    logger.info("=" * 80)
    logger.info("TESTE DE CALIBRAGEM DO SISTEMA DE PRIORIZAÇÃO")
    logger.info("=" * 80)

    resultados = []

    for falha_id in falhas_teste:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"ANALISANDO FALHA #{falha_id}")
        logger.info(f"{'=' * 80}\n")

        resultado = await priorizador.analisar_falha(falha_id)

        if resultado['sucesso']:
            resultados.append({
                'falha_id': falha_id,
                'impacto': resultado['impacto'],
                'esforco': resultado['esforco'],
                'fontes': len(resultado.get('fontes', []))
            })

            logger.info(f"\n✓ RESULTADO:")
            logger.info(f"  Impacto: {resultado['impacto']}/10")
            logger.info(f"  Esforço: {resultado['esforco']}/10")
            logger.info(f"  Fontes utilizadas: {len(resultado.get('fontes', []))}")
            logger.info(f"  Quadrante: {classificar_quadrante(resultado['impacto'], resultado['esforco'])}")
        else:
            logger.error(f"✗ Erro ao analisar falha {falha_id}: {resultado.get('erro')}")

        # Delay entre requisições
        if falha_id != falhas_teste[-1]:
            logger.info("\nAguardando 2 segundos antes da próxima análise...")
            await asyncio.sleep(2)

    # Sumário final
    logger.info(f"\n{'=' * 80}")
    logger.info("SUMÁRIO DOS RESULTADOS")
    logger.info(f"{'=' * 80}\n")

    logger.info(f"{'ID':<5} {'Impacto':<10} {'Esforço':<10} {'Fontes':<10} {'Quadrante':<20}")
    logger.info("-" * 80)

    for r in resultados:
        quadrante = classificar_quadrante(r['impacto'], r['esforco'])
        logger.info(f"{r['falha_id']:<5} {r['impacto']:<10} {r['esforco']:<10} {r['fontes']:<10} {quadrante:<20}")

    logger.info(f"\n{'=' * 80}")
    logger.info("VALIDAÇÃO DE CALIBRAGEM")
    logger.info(f"{'=' * 80}\n")

    # Validar distribuição
    impactos = [r['impacto'] for r in resultados]
    esforcos = [r['esforco'] for r in resultados]

    logger.info(f"✓ Impactos: min={min(impactos)}, max={max(impactos)}, média={sum(impactos)/len(impactos):.1f}")
    logger.info(f"✓ Esforços: min={min(esforcos)}, max={max(esforcos)}, média={sum(esforcos)/len(esforcos):.1f}")

    # Verificar se há variação (não todas iguais)
    if len(set(impactos)) > 1 and len(set(esforcos)) > 1:
        logger.info("\n✓ CALIBRAGEM OK: Sistema está diferenciando falhas corretamente")
    else:
        logger.warning("\n⚠ ATENÇÃO: Baixa variação nos scores - revisar critérios de calibragem")

def classificar_quadrante(impacto: int, esforco: int) -> str:
    """Classifica a falha em um dos 4 quadrantes"""
    if impacto >= 7 and esforco <= 4:
        return "GANHOS RÁPIDOS"
    elif impacto >= 7 and esforco >= 5:
        return "INVESTIR C/ CAUTELA"
    elif impacto <= 6 and esforco <= 4:
        return "CONSIDERAR"
    else:
        return "BAIXA PRIORIDADE"

if __name__ == "__main__":
    asyncio.run(testar_calibragem())
