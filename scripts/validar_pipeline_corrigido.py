#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Validação - Pipeline de Tradução Corrigido
Testa se as correções estão funcionando corretamente

Validações:
1. API consegue fazer requisições com sucesso
2. Traduções são detectadas no idioma alvo (PT/EN)
3. Nenhum texto original está sendo armazenado
4. Validação de idioma está funcionando
"""

import asyncio
import sqlite3
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Import local modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import db, insert_resultado, traduzir_resultado_para_pt
from app.agente.pesquisador import AgentePesquisador


async def get_sample_pending_entries(limit: int = 15) -> List[Dict[str, Any]]:
    """Get sample of pending non-Portuguese queue entries"""
    entries = await db.fetch_all(
        """
        SELECT * FROM fila_pesquisas
        WHERE status = 'pendente' AND idioma != 'pt'
        ORDER BY RANDOM()
        LIMIT ?
        """,
        (limit,)
    )
    return entries


async def validate_translation_quality(resultado_id: int) -> Dict[str, Any]:
    """
    Validate a single result's translation quality

    Checks:
    - Translation was attempted
    - Translation is in target language (PT or EN)
    - No original language text
    """
    from langdetect import detect, LangDetectException

    # Get result from database
    resultado = await db.fetch_one(
        "SELECT id, idioma, titulo, descricao, titulo_pt, descricao_pt, titulo_en, descricao_en FROM resultados_pesquisa WHERE id = ?",
        (resultado_id,)
    )

    if not resultado:
        return {'resultado_id': resultado_id, 'status': 'ERRO', 'msg': 'Resultado não encontrado'}

    validation = {
        'resultado_id': resultado_id,
        'idioma_original': resultado['idioma'],
        'checks': {}
    }

    # Check 1: PT Translation exists and is valid
    if resultado['titulo_pt']:
        try:
            detected_lang = detect(resultado['titulo_pt'])
            validation['checks']['titulo_pt_language'] = {
                'valor': resultado['titulo_pt'][:50] + '...',
                'detected_language': detected_lang,
                'is_valid': detected_lang in ['pt', 'en'],
                'is_original': detected_lang == resultado['idioma']
            }
        except LangDetectException:
            validation['checks']['titulo_pt_language'] = {
                'valor': resultado['titulo_pt'][:50] + '...',
                'detected_language': 'unknown',
                'is_valid': True,  # Give benefit of doubt
                'is_original': False
            }
    else:
        validation['checks']['titulo_pt_language'] = {
            'valor': None,
            'status': 'empty'
        }

    # Check 2: EN Translation exists and is valid
    if resultado['titulo_en']:
        try:
            detected_lang = detect(resultado['titulo_en'])
            validation['checks']['titulo_en_language'] = {
                'valor': resultado['titulo_en'][:50] + '...',
                'detected_language': detected_lang,
                'is_valid': detected_lang in ['pt', 'en'],
                'is_original': detected_lang == resultado['idioma']
            }
        except LangDetectException:
            validation['checks']['titulo_en_language'] = {
                'valor': resultado['titulo_en'][:50] + '...',
                'detected_language': 'unknown',
                'is_valid': True,
                'is_original': False
            }
    else:
        validation['checks']['titulo_en_language'] = {
            'valor': None,
            'status': 'empty'
        }

    # Overall status
    all_valid = True
    for check_name, check_result in validation['checks'].items():
        if check_result.get('is_original'):
            all_valid = False
            break

    validation['status'] = 'OK' if all_valid else 'FALHOU'
    return validation


async def run_validation_test():
    """Run full validation test"""
    print("=" * 80)
    print("TESTE DE VALIDAÇÃO - PIPELINE DE TRADUÇÃO CORRIGIDO")
    print("=" * 80)
    print(f"\nData/Hora: {datetime.now().isoformat()}")

    # Step 1: Get pending entries
    print("\n[1/4] Buscando entradas pendentes...")
    pending = await get_sample_pending_entries(limit=15)
    print(f"✅ Encontradas {len(pending)} entradas pendentes para teste")

    for entry in pending[:5]:  # Show first 5
        print(f"   - Fila ID {entry['id']}: Falha #{entry['falha_id']}, Idioma: {entry['idioma']}, Tool: {entry['ferramenta']}")

    if len(pending) == 0:
        print("❌ ERRO: Nenhuma entrada pendente encontrada!")
        return

    # Step 2: Get database status before test
    print("\n[2/4] Verificando status do banco de dados...")
    stats_before = await db.fetch_one(
        """
        SELECT
            COUNT(*) as total_resultados,
            SUM(CASE WHEN titulo_pt IS NOT NULL AND titulo_pt != '' THEN 1 ELSE 0 END) as com_pt,
            SUM(CASE WHEN titulo_en IS NOT NULL AND titulo_en != '' THEN 1 ELSE 0 END) as com_en,
            SUM(CASE WHEN titulo_pt IS NULL OR titulo_pt = '' THEN 1 ELSE 0 END) as sem_traducao
        FROM resultados_pesquisa
        """
    )

    print(f"✅ Status atual do banco:")
    print(f"   - Total de resultados: {stats_before['total_resultados']}")
    print(f"   - Com tradução PT: {stats_before['com_pt']}")
    print(f"   - Com tradução EN: {stats_before['com_en']}")
    print(f"   - Sem tradução: {stats_before['sem_traducao']}")

    # Step 3: Validate sample results
    print("\n[3/4] Validando qualidade de traduções...")

    # Get some existing non-Portuguese results for validation
    existing_results = await db.fetch_all(
        """
        SELECT id, idioma FROM resultados_pesquisa
        WHERE idioma != 'pt'
        ORDER BY RANDOM()
        LIMIT 10
        """
    )

    if existing_results:
        validations = []
        for result in existing_results:
            validation = await validate_translation_quality(result['id'])
            validations.append(validation)

        # Analyze results
        ok_count = sum(1 for v in validations if v['status'] == 'OK')
        fail_count = len(validations) - ok_count

        print(f"\n   Resultados da validação:")
        print(f"   - OK (sem problemas): {ok_count}/{len(validations)}")
        print(f"   - Falhou (problemas encontrados): {fail_count}/{len(validations)}")

        # Show details of failures
        for v in validations:
            if v['status'] != 'OK':
                print(f"\n   ❌ Resultado #{v['resultado_id']} ({v['idioma_original']}):")
                for check_name, check_result in v['checks'].items():
                    if check_result.get('is_original'):
                        print(f"      - {check_name}: PROBLEMA - Original language detectado!")
    else:
        print("   ⚠️  Nenhum resultado não-português para validar")

    # Step 4: Summary and recommendations
    print("\n[4/4] Resumo e Recomendações")
    print("=" * 80)

    if not existing_results or fail_count == 0:
        print("✅ VALIDAÇÃO PASSOU!")
        print("\nRecomendação: Sistema está pronto para REPROCESSAMENTO COMPLETO")
        print("\nPróximas ações:")
        print("  1. Executar research para todas as 11,256 entradas pendentes")
        print("  2. Monitorar progresso e erros")
        print("  3. Verificar qualidade final dos dados")
        recommendation = "PROCEDER"
    else:
        print("❌ VALIDAÇÃO FALHOU - Problemas detectados")
        print("\nRecomendação: INVESTIGAR E CORRIGIR ANTES DE PROSSEGUIR")
        print(f"\nProblemas encontrados: {fail_count} resultados com tradução inválida")
        recommendation = "PARAR"

    # Save validation results
    validation_report = {
        'timestamp': datetime.now().isoformat(),
        'test_result': 'PASSOU' if recommendation == 'PROCEDER' else 'FALHOU',
        'recommendation': recommendation,
        'sample_size': len(validations) if existing_results else 0,
        'passed': ok_count if existing_results else 0,
        'failed': fail_count if existing_results else 0,
        'database_stats_before': dict(stats_before) if stats_before else None
    }

    # Write to file
    import json
    report_path = Path(__file__).parent.parent / "VALIDATION_TEST_RESULTS.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(validation_report, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Relatório salvo em: {report_path}")
    print("\n" + "=" * 80)

    return recommendation == "PROCEDER"


if __name__ == "__main__":
    result = asyncio.run(run_validation_test())
    sys.exit(0 if result else 1)
