# -*- coding: utf-8 -*-
"""
Testes para clientes de APIs externas
"""
import pytest
import os
from app.integracao.perplexity_api import PerplexityClient
from app.integracao.jina_api import JinaClient


@pytest.fixture
def perplexity_client():
    """Fixture para cliente Perplexity"""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        pytest.skip("PERPLEXITY_API_KEY nao configurada")
    return PerplexityClient(api_key)


@pytest.fixture
def jina_client():
    """Fixture para cliente Jina"""
    api_key = os.getenv("JINA_API_KEY")
    if not api_key:
        pytest.skip("JINA_API_KEY nao configurada")
    return JinaClient(api_key)


class TestPerplexityClient:
    """Testes para Perplexity API"""

    def test_cliente_inicializa(self, perplexity_client):
        """Perplexity client deve inicializar sem erros"""
        assert perplexity_client is not None
        assert perplexity_client.api_key is not None

    @pytest.mark.asyncio
    async def test_pesquisa_retorna_resultado(self, perplexity_client):
        """Pesquisa deve retornar resultado"""
        resultado = await perplexity_client.pesquisar(
            "startup financing best practices",
            "en"
        )

        assert resultado is not None
        assert isinstance(resultado, list)
        assert len(resultado) > 0

        # Verificar estrutura dos resultados
        for item in resultado:
            assert "titulo" in item
            assert "url" in item


class TestJinaClient:
    """Testes para Jina AI"""

    def test_cliente_inicializa(self, jina_client):
        """Jina client deve inicializar sem erros"""
        assert jina_client is not None
        assert jina_client.api_key is not None

    @pytest.mark.asyncio
    async def test_busca_web(self, jina_client):
        """Busca web deve retornar resultados"""
        resultado = await jina_client.search_web(
            "startup policy support",
            "en"
        )

        assert resultado is not None
        assert isinstance(resultado, list)
        assert len(resultado) > 0

    @pytest.mark.asyncio
    async def test_ler_url(self, jina_client):
        """Ler URL deve retornar conteudo"""
        # URL de exemplo (blog sobre empreendedorismo)
        resultado = await jina_client.read_url(
            "https://en.wikipedia.org/wiki/Startup_company"
        )

        assert resultado is not None
        assert isinstance(resultado, str)
        assert len(resultado) > 0
