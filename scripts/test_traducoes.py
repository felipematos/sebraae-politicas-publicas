#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar a integração de tradução com OpenRouter
"""
import asyncio
import sys
sys.path.insert(0, '/Users/felipematossardinhapinto/Library/CloudStorage/GoogleDrive-Felipe@felipematos.net/My Drive/10K/Projetos/2025/Sebrae Nacional/Code')

from app.utils.idiomas import traduzir_query

async def test_traducoes():
    """Testa a tradução com dados mockados"""
    print("=" * 80)
    print("TESTANDO INTEGRAÇÃO DE TRADUÇÃO COM OPENROUTER")
    print("=" * 80)

    # Dados de teste
    testes = [
        {
            "texto": "Falta de acesso a crédito para startups",
            "origem": "pt",
            "alvo": "en",
            "esperado": "tradução para inglês"
        },
        {
            "texto": "Lack of access to credit for startups",
            "origem": "en",
            "alvo": "pt",
            "esperado": "tradução para português"
        },
        {
            "texto": "Dificuldade em regulação e compliance",
            "origem": "pt",
            "alvo": "es",
            "esperado": "tradução para espanhol"
        },
    ]

    for i, teste in enumerate(testes, 1):
        print(f"\n📝 Teste {i}: {teste['origem'].upper()} → {teste['alvo'].upper()}")
        print(f"   Texto original: {teste['texto']}")
        print(f"   Esperado: {teste['esperado']}")

        try:
            resultado = await traduzir_query(
                teste['texto'],
                teste['origem'],
                teste['alvo']
            )
            print(f"   ✅ Resultado: {resultado}")
        except Exception as e:
            print(f"   ❌ Erro: {str(e)[:100]}")

    print("\n" + "=" * 80)
    print("TESTE CONCLUÍDO")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_traducoes())
