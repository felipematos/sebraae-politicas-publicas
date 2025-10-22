# -*- coding: utf-8 -*-
"""
Testes para busca adaptativa
Verifica se os limites min/max e qualidade são respeitados
"""
import asyncio
import pytest
from app.agente.pesquisador import AgentePesquisador
from app.agente.avaliador import Avaliador
from app.config import settings


@pytest.mark.asyncio
async def test_pesquisa_respeita_minimo():
    """Verifica se sempre executa no mínimo MIN_BUSCAS_POR_FALHA buscas"""
    pesquisador = AgentePesquisador()

    # Query simples e genérica
    query = "inovação tecnológica"

    resultado = await pesquisador.executar_pesquisa_adaptativa(
        query=query,
        idioma="pt",
        ferramentas=pesquisador.ferramentas
    )

    # Verificar se o modo é adaptativo
    assert resultado.get("modo") == "adaptativo", "Deve estar em modo adaptativo"

    # Verificar se respeita mínimo
    num_buscas = resultado.get("num_buscas", 0)
    assert num_buscas >= settings.MIN_BUSCAS_POR_FALHA, \
        f"Deve ter no mínimo {settings.MIN_BUSCAS_POR_FALHA} buscas, teve {num_buscas}"

    print(f"\n✓ Teste passou: {num_buscas} buscas >= {settings.MIN_BUSCAS_POR_FALHA} (mínimo)")


@pytest.mark.asyncio
async def test_pesquisa_respeita_maximo():
    """Verifica se nunca executa mais de MAX_BUSCAS_POR_FALHA buscas"""
    pesquisador = AgentePesquisador()

    # Query simples
    query = "políticas públicas"

    resultado = await pesquisador.executar_pesquisa_adaptativa(
        query=query,
        idioma="pt",
        ferramentas=pesquisador.ferramentas
    )

    # Verificar se respeita máximo
    num_buscas = resultado.get("num_buscas", 0)
    assert num_buscas <= settings.MAX_BUSCAS_POR_FALHA, \
        f"Deve ter no máximo {settings.MAX_BUSCAS_POR_FALHA} buscas, teve {num_buscas}"

    print(f"\n✓ Teste passou: {num_buscas} buscas <= {settings.MAX_BUSCAS_POR_FALHA} (máximo)")


@pytest.mark.asyncio
async def test_pesquisa_retorna_resultados():
    """Verifica se retorna resultados na estrutura correta"""
    pesquisador = AgentePesquisador()

    query = "startup"
    resultado = await pesquisador.executar_pesquisa_adaptativa(
        query=query,
        idioma="pt",
        ferramentas=pesquisador.ferramentas
    )

    # Verificar estrutura
    assert "resultados" in resultado, "Deve ter 'resultados' na resposta"
    assert "num_buscas" in resultado, "Deve ter 'num_buscas' na resposta"
    assert "qualidade" in resultado, "Deve ter 'qualidade' na resposta"
    assert "motivo_parada" in resultado, "Deve ter 'motivo_parada' na resposta"

    # Verificar tipos
    assert isinstance(resultado["resultados"], list), "resultados deve ser uma lista"
    assert isinstance(resultado["num_buscas"], int), "num_buscas deve ser int"
    assert isinstance(resultado["qualidade"], (int, float)), "qualidade deve ser numérico"

    # Se tem resultados, verificar estrutura deles
    if resultado["resultados"]:
        primeiro = resultado["resultados"][0]
        assert "titulo" in primeiro or "title" in primeiro, "Resultado deve ter título"
        assert "url" in primeiro or "source" in primeiro, "Resultado deve ter URL"

    print(f"\n✓ Teste passou: Estrutura correta com {len(resultado['resultados'])} resultados")


@pytest.mark.asyncio
async def test_avaliador_qualidade_conjunto():
    """Testa se o avaliador consegue avaliar qualidade de um conjunto"""
    avaliador = Avaliador()

    # Resultados mock
    resultados = [
        {
            "titulo": "Inovação no Brasil",
            "descricao": "A inovação é fundamental para o desenvolvimento",
            "url": "https://exemplo1.com",
            "fonte": "google"
        },
        {
            "titulo": "Políticas de Inovação",
            "descricao": "Políticas públicas para fomentar inovação",
            "url": "https://exemplo2.com",
            "fonte": "perplexity"
        }
    ]

    query = "inovação"

    avaliacao = await avaliador.avaliar_qualidade_conjunto(resultados, query)

    # Verificar estrutura da avaliação
    assert "qualidade_geral" in avaliacao, "Deve ter qualidade_geral"
    assert "confianca" in avaliacao, "Deve ter confianca"
    assert "diversidade" in avaliacao, "Deve ter diversidade"
    assert "recomendacao" in avaliacao, "Deve ter recomendacao"

    # Verificar valores
    assert 0.0 <= avaliacao["qualidade_geral"] <= 1.0, "Qualidade deve estar entre 0 e 1"
    assert 0.0 <= avaliacao["confianca"] <= 1.0, "Confiança deve estar entre 0 e 1"
    assert avaliacao["recomendacao"] in ["parar", "talvez", "continuar"], \
        "Recomendação deve ser parar, talvez ou continuar"

    print(f"\n✓ Teste passou: Qualidade={avaliacao['qualidade_geral']:.3f}, "
          f"Confiança={avaliacao['confianca']:.3f}, Recomendação={avaliacao['recomendacao']}")


@pytest.mark.asyncio
async def test_modo_adaptativo_vs_tradicional():
    """Compara comportamento adaptativo vs tradicional"""
    pesquisador = AgentePesquisador()

    query = "tecnologia"
    ferramentas = ["perplexity", "jina"]  # Limitar a 2 ferramentas

    # Busca adaptativa
    resultado_adaptativo = await pesquisador.executar_pesquisa_adaptativa(
        query=query,
        idioma="pt",
        ferramentas=ferramentas
    )

    # Verificar que usa modo correto baseado em settings
    if settings.USAR_BUSCA_ADAPTATIVA:
        assert resultado_adaptativo["modo"] == "adaptativo"
    else:
        assert resultado_adaptativo["modo"] == "tradicional"

    print(f"\n✓ Teste passou: Modo={resultado_adaptativo['modo']}, "
          f"Buscas={resultado_adaptativo['num_buscas']}")


@pytest.mark.asyncio
async def test_calculo_metricas_qualidade():
    """Testa cálculo correto das métricas de qualidade"""
    avaliador = Avaliador()

    # Criar dois conjuntos: um com boa qualidade, outro com baixa
    bom_conjunto = [
        {
            "titulo": "Regulação de Startups no Brasil",
            "descricao": "Análise completa das regulações para startups",
            "url": "https://exemplo1.com",
            "fonte": "perplexity"
        },
        {
            "titulo": "Marco Legal da Inovação",
            "descricao": "Lei de incentivos fiscais para inovação",
            "url": "https://exemplo2.com",
            "fonte": "jina"
        }
    ]

    ruim_conjunto = [
        {
            "titulo": "Gato",
            "descricao": "Um animal doméstico",
            "url": "https://exemplo3.com",
            "fonte": "unknown"
        }
    ]

    query = "regulação de startups"

    avaliacao_boa = await avaliador.avaliar_qualidade_conjunto(bom_conjunto, query)
    avaliacao_ruim = await avaliador.avaliar_qualidade_conjunto(ruim_conjunto, query)

    # A boa deve ter qualidade melhor que a ruim
    assert avaliacao_boa["qualidade_geral"] > avaliacao_ruim["qualidade_geral"], \
        "Conjunto com conteúdo relevante deve ter melhor qualidade"

    print(f"\n✓ Teste passou: Boa qualidade={avaliacao_boa['qualidade_geral']:.3f} > "
          f"Ruim qualidade={avaliacao_ruim['qualidade_geral']:.3f}")


if __name__ == "__main__":
    # Rodar testes manualmente
    print("Executando testes de busca adaptativa...\n")

    try:
        asyncio.run(test_pesquisa_respeita_minimo())
    except Exception as e:
        print(f"✗ Erro em test_pesquisa_respeita_minimo: {e}")

    try:
        asyncio.run(test_pesquisa_respeita_maximo())
    except Exception as e:
        print(f"✗ Erro em test_pesquisa_respeita_maximo: {e}")

    try:
        asyncio.run(test_pesquisa_retorna_resultados())
    except Exception as e:
        print(f"✗ Erro em test_pesquisa_retorna_resultados: {e}")

    try:
        asyncio.run(test_avaliador_qualidade_conjunto())
    except Exception as e:
        print(f"✗ Erro em test_avaliador_qualidade_conjunto: {e}")

    try:
        asyncio.run(test_modo_adaptativo_vs_tradicional())
    except Exception as e:
        print(f"✗ Erro em test_modo_adaptativo_vs_tradicional: {e}")

    try:
        asyncio.run(test_calculo_metricas_qualidade())
    except Exception as e:
        print(f"✗ Erro em test_calculo_metricas_qualidade: {e}")

    print("\n✓ Testes de busca adaptativa completados!")
