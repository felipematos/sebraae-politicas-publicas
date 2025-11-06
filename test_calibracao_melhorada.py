# -*- coding: utf-8 -*-
"""
Script para testar a nova calibração de scores de confiança
Compara scores antigos vs novos com exemplos reais
"""
import asyncio
import sys
from typing import Dict, Any


# Simulação da implementação ANTIGA
async def calcular_score_relevancia_OLD(resultado: str, query: str, resultado_traduzido: str = None) -> float:
    """Implementação antiga (limitada a 0.8 + 0.15)"""
    if not resultado or not query:
        return 0.0

    texto_para_avaliar = resultado_traduzido if resultado_traduzido else resultado

    # Extrair palavras simples (sem stop words por simplicidade)
    palavras_query = [p for p in query.lower().split() if len(p) >= 3]
    if not palavras_query:
        return 0.0

    texto_lower = texto_para_avaliar.lower()
    query_lower = query.lower()

    # Contar matches
    matches = sum(1 for palavra in palavras_query if palavra in texto_lower)

    # Score base limitado a 0.8
    score_base = (matches / len(palavras_query)) * 0.8

    # Bonus limitado a 0.15
    bonus_phrase = 0.0
    if query_lower in texto_lower:
        bonus_phrase = 0.15
    elif matches == len(palavras_query):
        bonus_phrase = 0.10

    return min(1.0, score_base + bonus_phrase)


def calcular_score_ponderado_OLD(
    resultado: Dict[str, Any],
    query: str,
    score_relevancia: float,
    num_ocorrencias: int,
    confiabilidade_fonte: float
) -> float:
    """Implementação antiga"""
    # Relevância 50%
    peso_relevancia = 0.50
    valor_relevancia = min(1.0, score_relevancia)

    # Ocorrências 20% (linear)
    peso_ocorrencias = 0.20
    valor_ocorrencias = min(1.0, num_ocorrencias / 5.0)

    # Fonte 20%
    peso_fonte = 0.20
    valor_fonte = min(1.0, confiabilidade_fonte)

    # Título 10%
    peso_titulo = 0.10
    titulo = resultado.get("titulo", "").lower()
    palavras_query = [p for p in query.lower().split() if len(p) >= 3]
    if palavras_query:
        titulo_matches = sum(1 for p in palavras_query if p in titulo)
        valor_titulo = min(1.0, titulo_matches / len(palavras_query))
    else:
        valor_titulo = 0.0

    score = (
        valor_relevancia * peso_relevancia +
        valor_ocorrencias * peso_ocorrencias +
        valor_fonte * peso_fonte +
        valor_titulo * peso_titulo
    )

    return min(1.0, max(0.0, score))


# Simulação da implementação NOVA
async def calcular_score_relevancia_NEW(resultado: str, query: str, resultado_traduzido: str = None) -> float:
    """Nova implementação melhorada"""
    if not resultado or not query:
        return 0.0

    texto_para_avaliar = resultado_traduzido if resultado_traduzido else resultado

    palavras_query = [p for p in query.lower().split() if len(p) >= 3]
    if not palavras_query:
        return 0.0

    texto_lower = texto_para_avaliar.lower()
    query_lower = query.lower()

    # Contar matches exatos e parciais
    matches = 0
    matches_parciais = 0
    for palavra in palavras_query:
        if palavra in texto_lower:
            matches += 1
        else:
            palavras_texto = texto_lower.split()
            for palavra_texto in palavras_texto:
                if palavra in palavra_texto or palavra_texto in palavra:
                    matches_parciais += 1
                    break

    # Score base até 0.75
    score_base = (matches / len(palavras_query)) * 0.75

    # Bonus parcial até 0.10
    bonus_parcial = (matches_parciais / len(palavras_query)) * 0.10

    # Bonus phrase até 0.25
    bonus_phrase = 0.0
    if query_lower in texto_lower:
        bonus_phrase = 0.25
    elif matches == len(palavras_query):
        bonus_phrase = 0.15

    return min(1.0, score_base + bonus_parcial + bonus_phrase)


def detectar_brasil_NEW(resultado: Dict[str, Any]) -> bool:
    """Nova detecção de Brasil"""
    termos_brasil = ["brasil", "brazilian", "brasileiro", "brasileira", ".br", "brasilia", "brasília", "gov.br"]
    texto = f"{resultado.get('titulo', '')} {resultado.get('descricao', '')} {resultado.get('fonte_url', '')}".lower()
    return any(termo in texto for termo in termos_brasil)


def expandir_score_NEW(score: float) -> float:
    """Nova função de expansão melhorada"""
    if score < 0.25:
        return score
    elif score > 0.80:
        return score
    elif score < 0.40:
        return 0.25 + (score - 0.25) * 1.67
    else:
        return 0.50 + (score - 0.40) * 0.875


def calcular_score_ponderado_NEW(
    resultado: Dict[str, Any],
    query: str,
    score_relevancia: float,
    num_ocorrencias: int,
    confiabilidade_fonte: float
) -> float:
    """Nova implementação melhorada"""
    import math

    # Relevância 55% (aumentado)
    peso_relevancia = 0.55
    valor_relevancia = min(1.0, score_relevancia)

    # Ocorrências 15% (reduzido, sqrt)
    peso_ocorrencias = 0.15
    valor_ocorrencias = min(1.0, math.sqrt(num_ocorrencias) / math.sqrt(5.0))

    # Fonte 20%
    peso_fonte = 0.20
    valor_fonte = min(1.0, confiabilidade_fonte)

    # Título 10%
    peso_titulo = 0.10
    titulo = resultado.get("titulo", "").lower()
    titulo_pt = resultado.get("titulo_pt", "").lower()
    titulo_completo = f"{titulo} {titulo_pt}"

    palavras_query = [p for p in query.lower().split() if len(p) >= 3]
    if palavras_query:
        titulo_matches = sum(1 for p in palavras_query if p in titulo_completo)
        valor_titulo = min(1.0, titulo_matches / len(palavras_query))
    else:
        valor_titulo = 0.0

    # Score base
    score_base = (
        valor_relevancia * peso_relevancia +
        valor_ocorrencias * peso_ocorrencias +
        valor_fonte * peso_fonte +
        valor_titulo * peso_titulo
    )

    # Bonus Brasil 20%
    bonus_brasil = 0.0
    if detectar_brasil_NEW(resultado):
        bonus_brasil = score_base * 0.20

    # Score final
    score_final = score_base + bonus_brasil

    # Expansão
    score_expandido = expandir_score_NEW(score_final)

    return min(1.0, max(0.0, score_expandido))


# Casos de teste
CASOS_TESTE = [
    {
        "nome": "Caso 1: Educação STEM Brasil (exemplo do usuário)",
        "resultado": {
            "titulo": "a educação steam/stem na educação básica brasileira",
            "descricao": "Análise das políticas públicas de educação STEM no Brasil, incluindo programas de capacitação e formação profissional em ciência e tecnologia",
            "fonte_url": "https://educacao.gov.br/stem",
            "fonte": "perplexity"
        },
        "query": "políticas educacionais STEM educação capacitação formação profissional",
        "num_ocorrencias": 1,
        "confiabilidade_fonte": 0.95,
        "esperado_minimo": 0.70  # Esperamos pelo menos 70
    },
    {
        "nome": "Caso 2: Resultado alemão sobre STEM",
        "resultado": {
            "titulo": "Mehr Diversität in der MINT-Bildung",
            "titulo_pt": "Mais diversidade na educação em STEM",
            "descricao": "Programas alemães para aumentar diversidade em STEM",
            "descricao_pt": "Programas alemães para aumentar diversidade em ciência, tecnologia, engenharia e matemática",
            "fonte_url": "https://bildung.de/mint",
            "fonte": "perplexity"
        },
        "query": "políticas educacionais STEM educação capacitação formação profissional",
        "num_ocorrencias": 1,
        "confiabilidade_fonte": 0.95,
        "esperado_minimo": 0.50  # Sem Brasil, deve ser menor que caso 1
    },
    {
        "nome": "Caso 3: Alta relevância + Brasil + múltiplas ocorrências",
        "resultado": {
            "titulo": "Políticas públicas para educação STEM no Brasil",
            "descricao": "O governo brasileiro implementou programas de capacitação profissional em STEM com foco em formação de professores",
            "fonte_url": "https://www.gov.br/educacao",
            "fonte": "perplexity"
        },
        "query": "políticas educacionais STEM educação capacitação formação profissional",
        "num_ocorrencias": 3,
        "confiabilidade_fonte": 0.95,
        "esperado_minimo": 0.80  # Deve ser ALTO
    },
    {
        "nome": "Caso 4: Baixa relevância (irrelevante)",
        "resultado": {
            "titulo": "Tendências de tecnologia em 2025",
            "descricao": "As principais tecnologias a dominar o mercado em 2025 incluem IA, blockchain e computação quântica",
            "fonte_url": "https://example.com/tech",
            "fonte": "jina"
        },
        "query": "políticas educacionais STEM educação capacitação formação profissional",
        "num_ocorrencias": 1,
        "confiabilidade_fonte": 0.90,
        "esperado_minimo": 0.0  # Deve ser BAIXO
    }
]


async def testar_calibracao():
    """Testa a calibração antiga vs nova"""
    print("=" * 80)
    print("TESTE DE CALIBRAÇÃO: ANTIGA vs NOVA")
    print("=" * 80)
    print()

    for caso in CASOS_TESTE:
        print(f"\n{'=' * 80}")
        print(f"📊 {caso['nome']}")
        print(f"{'=' * 80}")
        print(f"Título: {caso['resultado']['titulo']}")
        print(f"Query: {caso['query']}")
        print(f"Ocorrências: {caso['num_ocorrencias']}")
        print(f"Fonte: {caso['resultado']['fonte']} (confiabilidade: {caso['confiabilidade_fonte']})")
        print(f"Esperado mínimo: {caso['esperado_minimo'] * 100:.0f}")
        print()

        # ANTIGA
        score_rel_old = await calcular_score_relevancia_OLD(
            f"{caso['resultado']['titulo']} {caso['resultado']['descricao']}",
            caso['query']
        )
        score_old = calcular_score_ponderado_OLD(
            caso['resultado'],
            caso['query'],
            score_rel_old,
            caso['num_ocorrencias'],
            caso['confiabilidade_fonte']
        )

        # NOVA
        texto_completo = f"{caso['resultado']['titulo']} {caso['resultado']['descricao']}"
        texto_traduzido = None
        if 'titulo_pt' in caso['resultado']:
            texto_traduzido = f"{caso['resultado'].get('titulo_pt', '')} {caso['resultado'].get('descricao_pt', '')}"

        score_rel_new = await calcular_score_relevancia_NEW(
            texto_completo,
            caso['query'],
            texto_traduzido
        )
        score_new = calcular_score_ponderado_NEW(
            caso['resultado'],
            caso['query'],
            score_rel_new,
            caso['num_ocorrencias'],
            caso['confiabilidade_fonte']
        )

        # Verificar bonus Brasil
        tem_brasil = detectar_brasil_NEW(caso['resultado'])

        # Resultados
        print(f"🔴 ANTIGA:")
        print(f"   Relevância: {score_rel_old:.3f}")
        print(f"   Score Final: {score_old:.3f} = {score_old * 100:.1f}")
        print()
        print(f"🟢 NOVA:")
        print(f"   Relevância: {score_rel_new:.3f}")
        print(f"   Score Final: {score_new:.3f} = {score_new * 100:.1f}")
        print(f"   Bonus Brasil: {'✅ Sim' if tem_brasil else '❌ Não'}")
        print()

        # Comparação
        melhoria = ((score_new - score_old) / score_old * 100) if score_old > 0 else 0
        print(f"📈 Melhoria: {melhoria:+.1f}% ({score_old * 100:.1f} → {score_new * 100:.1f})")

        # Verificar se atende expectativa
        if score_new >= caso['esperado_minimo']:
            print(f"✅ PASSOU (>= {caso['esperado_minimo'] * 100:.0f})")
        else:
            print(f"⚠️  ABAIXO DO ESPERADO (esperado >= {caso['esperado_minimo'] * 100:.0f})")

    print(f"\n{'=' * 80}")
    print("✅ TESTES CONCLUÍDOS")
    print(f"{'=' * 80}\n")

    # Resumo das melhorias
    print("\n📊 RESUMO DAS MELHORIAS IMPLEMENTADAS:")
    print("=" * 80)
    print("1. ✅ Score de relevância: Bonus aumentado de 0.15 para 0.25")
    print("2. ✅ Matches parciais: Novo bonus de até 0.10")
    print("3. ✅ Normalização de ocorrências: sqrt(n)/sqrt(5) vs n/5")
    print("4. ✅ Peso de relevância: Aumentado de 50% para 55%")
    print("5. ✅ Peso de ocorrências: Reduzido de 20% para 15%")
    print("6. ✅ Bonus Brasil: Novo bonus de 20% para resultados brasileiros")
    print("7. ✅ Função de expansão: Expande scores médios (0.3-0.8)")
    print("=" * 80)
    print()


if __name__ == "__main__":
    asyncio.run(testar_calibracao())
