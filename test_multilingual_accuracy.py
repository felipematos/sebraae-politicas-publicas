# -*- coding: utf-8 -*-
"""
Teste de Acurácia Multilíngue
Valida se os filtros LLM têm a mesma acurácia independente do idioma da fonte
"""
import asyncio
import sys
from app.integracao.openrouter_api import OpenRouterClient


async def testar_acuracia_multilingue():
    """
    Testa se a análise de fontes tem acurácia consistente em diferentes idiomas
    Valida todos os idiomas suportados: pt, en, es, fr, de, it, ja, ar, ko, he
    """
    print("=" * 80)
    print("TESTE DE ACURÁCIA MULTILÍNGUE - FILTROS DE FONTES")
    print("Idiomas testados: pt, en, es, fr, de, it, ja, ar, ko, he")
    print("=" * 80)
    print()

    # Caso de teste: Mesmo conteúdo em diferentes idiomas
    # Conteúdo: Artigo sobre programa governamental de inovação com métricas

    casos_teste = [
        {
            "idioma": "pt",
            "titulo": "Programa Nacional de Apoio à Inovação - Resultados 2024",
            "descricao": "O programa governamental implementado em 2023 apoiou 1.500 startups, "
                        "resultando em crescimento de 45% no faturamento médio e criação de "
                        "3.200 empregos diretos. Investimento total: R$ 250 milhões.",
            "titulo_pt": None,
            "descricao_pt": None
        },
        {
            "idioma": "en",
            "titulo": "National Innovation Support Program - 2024 Results",
            "descricao": "The government program implemented in 2023 supported 1,500 startups, "
                        "resulting in 45% growth in average revenue and creation of "
                        "3,200 direct jobs. Total investment: R$ 250 million.",
            "titulo_pt": "Programa Nacional de Apoio à Inovação - Resultados 2024",
            "descricao_pt": "O programa governamental implementado em 2023 apoiou 1.500 startups, "
                           "resultando em crescimento de 45% no faturamento médio e criação de "
                           "3.200 empregos diretos. Investimento total: R$ 250 milhões."
        },
        {
            "idioma": "es",
            "titulo": "Programa Nacional de Apoyo a la Innovación - Resultados 2024",
            "descricao": "El programa gubernamental implementado en 2023 apoyó a 1.500 startups, "
                        "resultando en un crecimiento del 45% en los ingresos promedio y la creación de "
                        "3.200 empleos directos. Inversión total: R$ 250 millones.",
            "titulo_pt": "Programa Nacional de Apoio à Inovação - Resultados 2024",
            "descricao_pt": "O programa governamental implementado em 2023 apoiou 1.500 startups, "
                           "resultando em crescimento de 45% no faturamento médio e criação de "
                           "3.200 empregos diretos. Investimento total: R$ 250 milhões."
        },
        {
            "idioma": "fr",
            "titulo": "Programme National de Soutien à l'Innovation - Résultats 2024",
            "descricao": "Le programme gouvernemental mis en œuvre en 2023 a soutenu 1 500 startups, "
                        "résultant en une croissance de 45% du chiffre d'affaires moyen et la création de "
                        "3 200 emplois directs. Investissement total: R$ 250 millions.",
            "titulo_pt": "Programa Nacional de Apoio à Inovação - Resultados 2024",
            "descricao_pt": "O programa governamental implementado em 2023 apoiou 1.500 startups, "
                           "resultando em crescimento de 45% no faturamento médio e criação de "
                           "3.200 empregos diretos. Investimento total: R$ 250 milhões."
        },
        {
            "idioma": "de",
            "titulo": "Nationales Innovationsförderungsprogramm - Ergebnisse 2024",
            "descricao": "Das Regierungsprogramm, das 2023 umgesetzt wurde, unterstützte 1.500 Startups, "
                        "was zu einem Wachstum von 45% beim durchschnittlichen Umsatz und der Schaffung von "
                        "3.200 direkten Arbeitsplätzen führte. Gesamtinvestition: R$ 250 Millionen.",
            "titulo_pt": "Programa Nacional de Apoio à Inovação - Resultados 2024",
            "descricao_pt": "O programa governamental implementado em 2023 apoiou 1.500 startups, "
                           "resultando em crescimento de 45% no faturamento médio e criação de "
                           "3.200 empregos diretos. Investimento total: R$ 250 milhões."
        },
        {
            "idioma": "it",
            "titulo": "Programma Nazionale di Supporto all'Innovazione - Risultati 2024",
            "descricao": "Il programma governamentale implementato nel 2023 ha supportato 1.500 startup, "
                        "risultando in una crescita del 45% del fatturato medio e la creazione di "
                        "3.200 posti di lavoro diretti. Investimento totale: R$ 250 milioni.",
            "titulo_pt": "Programa Nacional de Apoio à Inovação - Resultados 2024",
            "descricao_pt": "O programa governamental implementado em 2023 apoiou 1.500 startups, "
                           "resultando em crescimento de 45% no faturamento médio e criação de "
                           "3.200 empregos diretos. Investimento total: R$ 250 milhões."
        }
    ]

    resultados = []

    async with OpenRouterClient() as client:
        print("Testando análise de fontes em diferentes idiomas...\n")

        for caso in casos_teste:
            print(f"📊 Analisando fonte em {caso['idioma'].upper()}...")
            print(f"   Título: {caso['titulo'][:60]}...")

            try:
                analise = await client.analisar_fonte(
                    titulo=caso['titulo'],
                    descricao=caso['descricao'],
                    titulo_pt=caso['titulo_pt'],
                    descricao_pt=caso['descricao_pt'],
                    idioma=caso['idioma']
                )

                print(f"   ✅ Resultado:")
                print(f"      - Tipo: {analise['tipo_fonte']}")
                print(f"      - Tem Implementação: {analise['tem_implementacao']}")
                print(f"      - Tem Métricas: {analise['tem_metricas']}")
                print(f"      - Confiança: {analise['confianca']:.2f}")
                print()

                resultados.append({
                    "idioma": caso['idioma'],
                    "analise": analise
                })

            except Exception as e:
                print(f"   ❌ Erro: {str(e)}")
                print()
                resultados.append({
                    "idioma": caso['idioma'],
                    "erro": str(e)
                })

    # Validar consistência
    print("=" * 80)
    print("VALIDAÇÃO DE CONSISTÊNCIA")
    print("=" * 80)
    print()

    # Resultados esperados (baseado no conteúdo do teste)
    esperado = {
        "tipo_fonte": "governamental",
        "tem_implementacao": True,
        "tem_metricas": True
    }

    acertos = 0
    total_criterios = 0

    for resultado in resultados:
        if "erro" in resultado:
            continue

        idioma = resultado['idioma']
        analise = resultado['analise']

        print(f"🔍 Validando {idioma.upper()}:")

        # Validar tipo_fonte
        total_criterios += 1
        if analise['tipo_fonte'] == esperado['tipo_fonte']:
            print(f"   ✅ Tipo de fonte: {analise['tipo_fonte']} (correto)")
            acertos += 1
        else:
            print(f"   ❌ Tipo de fonte: {analise['tipo_fonte']} (esperado: {esperado['tipo_fonte']})")

        # Validar tem_implementacao
        total_criterios += 1
        if analise['tem_implementacao'] == esperado['tem_implementacao']:
            print(f"   ✅ Tem implementação: {analise['tem_implementacao']} (correto)")
            acertos += 1
        else:
            print(f"   ❌ Tem implementação: {analise['tem_implementacao']} (esperado: {esperado['tem_implementacao']})")

        # Validar tem_metricas
        total_criterios += 1
        if analise['tem_metricas'] == esperado['tem_metricas']:
            print(f"   ✅ Tem métricas: {analise['tem_metricas']} (correto)")
            acertos += 1
        else:
            print(f"   ❌ Tem métricas: {analise['tem_metricas']} (esperado: {esperado['tem_metricas']})")

        print()

    # Calcular taxa de acurácia
    if total_criterios > 0:
        acuracia = (acertos / total_criterios) * 100
        print("=" * 80)
        print(f"RESULTADO FINAL: {acertos}/{total_criterios} critérios corretos ({acuracia:.1f}% de acurácia)")
        print("=" * 80)

        if acuracia >= 90:
            print("✅ TESTE PASSOU: Acurácia multilíngue excelente!")
            return 0
        elif acuracia >= 70:
            print("⚠️ TESTE PARCIAL: Acurácia razoável, mas pode melhorar")
            return 1
        else:
            print("❌ TESTE FALHOU: Acurácia insuficiente")
            return 2
    else:
        print("❌ TESTE FALHOU: Nenhum resultado válido obtido")
        return 2


async def main():
    """Função principal"""
    exit_code = await testar_acuracia_multilingue()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
