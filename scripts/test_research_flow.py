#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar o fluxo completo de pesquisa com validação
Processa 2-3 entradas da fila e valida todos os aspectos
"""
import asyncio
import sys
sys.path.insert(0, '/Users/felipematossardinhapinto/Library/CloudStorage/GoogleDrive-Felipe@felipematos.net/My Drive/10K/Projetos/2025/Sebrae Nacional/Code')

from app.database import db
from app.agente.processador import Processador
from app.config import settings


async def validar_resultado(resultado: dict, entrada_original: dict) -> tuple[bool, list]:
    """
    Valida um resultado processado

    Retorna: (é_válido, lista_de_problemas)
    """
    problemas = []

    # 1. Validar campos obrigatórios
    campos_obrigatorios = ['falha_id', 'titulo', 'descricao', 'idioma', 'ferramenta_origem']
    for campo in campos_obrigatorios:
        if not resultado.get(campo):
            problemas.append(f"❌ Campo obrigatório ausente: {campo}")

    # 2. Validar correspondência de falha_id
    if resultado.get('falha_id') != entrada_original.get('falha_id'):
        problemas.append(f"❌ falha_id não corresponde: esperado {entrada_original.get('falha_id')}, obtido {resultado.get('falha_id')}")

    # 3. Validar idioma
    idioma_esperado = entrada_original.get('idioma')
    idioma_obtido = resultado.get('idioma')
    if idioma_obtido and idioma_obtido not in ['pt', 'en', 'es', 'fr', 'de', 'it', 'ar', 'ko']:
        problemas.append(f"❌ Idioma inválido: {idioma_obtido}")

    # 4. Validar que traduções foram criadas
    if not resultado.get('titulo_pt'):
        problemas.append(f"⚠️ titulo_pt não preenchido (idioma original: {idioma_obtido})")
    if not resultado.get('titulo_en') and idioma_obtido != 'en':
        problemas.append(f"⚠️ titulo_en não preenchido para idioma não-inglês")

    # 5. Validar tamanhos de conteúdo (não vazio)
    if resultado.get('titulo') and len(resultado['titulo']) < 5:
        problemas.append(f"⚠️ Título muito curto: {resultado['titulo']}")
    if resultado.get('descricao') and len(resultado['descricao']) < 10:
        problemas.append(f"⚠️ Descrição muito curta: {resultado['descricao']}")

    # 6. Validar ferramenta
    ferramenta = resultado.get('ferramenta_origem')
    ferramentas_validas = ['perplexity', 'jina', 'tavily', 'serper', 'exa', 'deep_research']
    if ferramenta and ferramenta not in ferramentas_validas:
        problemas.append(f"⚠️ Ferramenta desconhecida: {ferramenta}")

    # 7. Validar confidence_score
    confidence = resultado.get('confidence_score', 0)
    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
        problemas.append(f"⚠️ confidence_score inválido: {confidence}")

    # 8. Validar hash_conteudo
    if not resultado.get('hash_conteudo'):
        problemas.append(f"⚠️ hash_conteudo não gerado")

    eh_valido = len(problemas) == 0
    return eh_valido, problemas


async def test_research_flow():
    """Testa o fluxo completo de pesquisa com validação"""
    print("=" * 80)
    print("TESTE DO FLUXO COMPLETO DE PESQUISA")
    print("=" * 80)

    # 1. Pegar 3 entradas da fila
    print("\n📋 PASSO 1: Obtendo entradas da fila...")
    entradas_fila = await db.fetch_all("""
        SELECT * FROM fila_pesquisas
        WHERE status = 'pendente'
        LIMIT 3
    """)

    total = len(entradas_fila)
    print(f"   Encontradas: {total} entradas para processar")

    if total == 0:
        print("   ❌ Nenhuma entrada pendente na fila!")
        return

    # 2. Inicializar processador
    print("\n⚙️  PASSO 2: Inicializando processador...")
    processador = Processador()
    print("   ✅ Processador inicializado")

    # 3. Processar cada entrada
    print(f"\n🔄 PASSO 3: Processando {total} entradas...")
    resultados_por_entrada = {}

    for i, entrada in enumerate(entradas_fila, 1):
        entrada_id = entrada['id']
        print(f"\n   [{i}/{total}] Processando entrada #{entrada_id}")
        print(f"       - Falha ID: {entrada['falha_id']}")
        print(f"       - Query: {entrada['query'][:50]}...")
        print(f"       - Idioma: {entrada['idioma']}")
        print(f"       - Ferramenta: {entrada['ferramenta']}")

        try:
            # Processar entrada
            sucesso = await processador.processar_entrada(entrada)

            if not sucesso:
                print(f"       ❌ Falha ao processar")
                resultados_por_entrada[entrada_id] = {'sucesso': False, 'resultados': []}
                continue

            # Buscar resultados salvos para esta entrada
            resultados = await db.fetch_all(f"""
                SELECT * FROM resultados_pesquisa
                WHERE falha_id = ? AND query = ?
                ORDER BY criado_em DESC
                LIMIT 5
            """, (entrada['falha_id'], entrada['query']))

            print(f"       ✅ Processado com sucesso")
            print(f"       📊 Resultados encontrados: {len(resultados)}")
            resultados_por_entrada[entrada_id] = {'sucesso': True, 'resultados': resultados, 'entrada': entrada}

        except Exception as e:
            print(f"       ❌ Erro: {str(e)[:100]}")
            resultados_por_entrada[entrada_id] = {'sucesso': False, 'resultados': [], 'erro': str(e)}

    # 4. Validar resultados
    print(f"\n✅ PASSO 4: Validando resultados...")
    problemas_encontrados = []
    resultados_validos = 0
    resultados_com_avisos = 0

    for entrada_id, dados in resultados_por_entrada.items():
        if not dados['sucesso']:
            continue

        entrada = dados['entrada']
        for resultado in dados['resultados']:
            eh_valido, problemas = await validar_resultado(resultado, entrada)

            if eh_valido:
                resultados_validos += 1
                print(f"\n   ✅ Resultado #{resultado['id']} válido")
                print(f"      - Título: {resultado['titulo'][:60]}...")
                print(f"      - Idioma: {resultado['idioma']} → PT: {bool(resultado.get('titulo_pt'))}, EN: {bool(resultado.get('titulo_en'))}")
            else:
                resultados_com_avisos += 1
                print(f"\n   ⚠️ Resultado #{resultado['id']} tem problemas:")
                for problema in problemas:
                    print(f"      {problema}")
                problemas_encontrados.extend(problemas)

    # 5. Relatório final
    print(f"\n{'='*80}")
    print(f"📊 RELATÓRIO FINAL")
    print(f"{'='*80}")
    print(f"\n✅ Resultados válidos: {resultados_validos}")
    print(f"⚠️  Resultados com avisos: {resultados_com_avisos}")
    print(f"📈 Total processado: {resultados_validos + resultados_com_avisos}")

    if problemas_encontrados:
        print(f"\n❌ PROBLEMAS ENCONTRADOS ({len(problemas_encontrados)}):")
        for problema in set(problemas_encontrados):  # Remove duplicatas
            print(f"   {problema}")

    # 6. Estatísticas do processador
    stats = processador.obter_estatisticas()
    print(f"\n📈 Estatísticas do processador:")
    print(f"   - Processadas: {stats['processadas']}")
    print(f"   - Erros: {stats['erros']}")
    print(f"   - Taxa de sucesso: {stats['taxa_sucesso']:.1%}")

    print(f"\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(test_research_flow())
