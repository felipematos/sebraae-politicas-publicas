# -*- coding: utf-8 -*-
"""
Testes para modulo de idiomas (traducao e geracao de queries)
"""
import pytest
from app.utils.idiomas import (
    gerar_queries_multilingues,
    traduzir_query,
    normalizar_query,
    MAPA_IDIOMAS_NOMES
)


class TestMapaIdiomas:
    """Testes para mapa de idiomas"""

    def test_mapa_idiomas_completo(self):
        """Deve ter mapping completo dos 8 idiomas"""
        assert len(MAPA_IDIOMAS_NOMES) >= 8
        assert "pt" in MAPA_IDIOMAS_NOMES
        assert "en" in MAPA_IDIOMAS_NOMES
        assert "es" in MAPA_IDIOMAS_NOMES


class TestNormalizarQuery:
    """Testes para normalizacao de queries"""

    def test_normalizar_remove_caracteres_especiais(self):
        """Query normalizada remove caracteres especiais"""
        query = "Falta de acesso à crédito para startups"
        resultado = normalizar_query(query)

        assert isinstance(resultado, str)
        assert len(resultado) > 0
        # Deve manter palavras principais
        assert "crédito" in resultado.lower() or "credito" in resultado.lower()

    def test_normalizar_lowercase(self):
        """Query normalizada em minusculas"""
        query = "FALTA DE ACESSO"
        resultado = normalizar_query(query)

        assert resultado == resultado.lower()

    def test_normalizar_query_vazia(self):
        """Query vazia retorna string vazia"""
        resultado = normalizar_query("")
        assert resultado == ""


class TestTraduzirQuery:
    """Testes para traducao de queries"""

    @pytest.mark.asyncio
    async def test_traduzir_query_mesmo_idioma(self):
        """Traduzir para mesmo idioma retorna query original"""
        query = "Falta de acesso a credito"
        resultado = await traduzir_query(query, "pt", "pt")

        assert resultado == query

    @pytest.mark.asyncio
    async def test_traduzir_query_estructura(self):
        """Query traduzida deve ser string nao vazia"""
        query = "Lack of access to credit"
        resultado = await traduzir_query(query, "en", "es")

        assert isinstance(resultado, str)
        assert len(resultado) > 0

    @pytest.mark.asyncio
    async def test_traduzir_multiplos_idiomas(self):
        """Deve traduzir para multiplos idiomas"""
        query = "Market access for startups"
        idiomas_alvo = ["pt", "es", "fr", "de"]

        for idioma in idiomas_alvo:
            resultado = await traduzir_query(query, "en", idioma)
            assert isinstance(resultado, str)
            assert len(resultado) > 0


class TestGerarQueriesMultilingues:
    """Testes para geracao de queries multilingues"""

    @pytest.mark.asyncio
    async def test_gerar_queries_estructura(self):
        """Queries geradas devem ter estrutura correta"""
        falha = {
            "id": 1,
            "titulo": "Falta de acesso a credito",
            "descricao": "Startups tem dificuldade em obter financiamento inicial",
            "dica_busca": "credito, financiamento, startup"
        }

        resultado = await gerar_queries_multilingues(falha)

        assert isinstance(resultado, list)
        assert len(resultado) > 0

        # Cada item deve ter os campos obrigatorios
        for item in resultado:
            assert "query" in item
            assert "idioma" in item
            assert "variacao" in item
            assert "falha_id" in item

    @pytest.mark.asyncio
    async def test_gerar_queries_quantidade_minima(self):
        """Deve gerar no minimo 5 variacoes por idioma"""
        falha = {
            "id": 1,
            "titulo": "Falta de acesso a credito",
            "descricao": "Startups tem dificuldade em obter financiamento inicial",
            "dica_busca": "credito, financiamento, startup"
        }

        resultado = await gerar_queries_multilingues(falha)

        # Com 8 idiomas e 5+ variacoes = 40+ queries
        assert len(resultado) >= 40

    @pytest.mark.asyncio
    async def test_gerar_queries_idiomas_distribuidos(self):
        """Queries devem estar distribuidas entre idiomas"""
        falha = {
            "id": 1,
            "titulo": "Falta de acesso a credito",
            "descricao": "Startups tem dificuldade em obter financiamento inicial",
            "dica_busca": "credito, financiamento, startup"
        }

        resultado = await gerar_queries_multilingues(falha)

        idiomas_presentes = {q["idioma"] for q in resultado}

        # Deve ter pelo menos 7 dos 8 idiomas
        assert len(idiomas_presentes) >= 7

    @pytest.mark.asyncio
    async def test_gerar_queries_variacoes_diferentes(self):
        """Variacoes de uma mesma falha devem ser diferentes"""
        falha = {
            "id": 1,
            "titulo": "Falta de acesso a credito",
            "descricao": "Startups tem dificuldade em obter financiamento inicial",
            "dica_busca": "credito, financiamento, startup"
        }

        resultado = await gerar_queries_multilingues(falha)

        # Agrupar queries do mesmo idioma
        queries_por_idioma = {}
        for item in resultado:
            idioma = item["idioma"]
            if idioma not in queries_por_idioma:
                queries_por_idioma[idioma] = []
            queries_por_idioma[idioma].append(item["query"])

        # Verificar que temos variacoes diferentes
        for idioma, queries in queries_por_idioma.items():
            # Deve ter pelo menos 2 queries diferentes
            assert len(set(queries)) >= 2, f"Idioma {idioma} nao tem variacoes suficientes"

    @pytest.mark.asyncio
    async def test_gerar_queries_falha_id_correto(self):
        """Todas as queries devem referenciar falha_id corretamente"""
        falha = {
            "id": 42,
            "titulo": "Falta de acesso a credito",
            "descricao": "Startups tem dificuldade em obter financiamento inicial",
            "dica_busca": "credito, financiamento, startup"
        }

        resultado = await gerar_queries_multilingues(falha)

        for item in resultado:
            assert item["falha_id"] == 42
