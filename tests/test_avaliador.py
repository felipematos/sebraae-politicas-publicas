# -*- coding: utf-8 -*-
"""
Testes para avaliador de confianca (confidence scorer)
"""
import pytest
from app.agente.avaliador import (
    Avaliador,
    calcular_score_relevancia,
    calcular_score_ponderado,
    extrair_palavras_chave
)


class TestExtrairPalavrasChave:
    """Testes para extracao de palavras-chave"""

    def test_extrair_palavras_chave_simples(self):
        """Extrai palavras-chave de um texto simples"""
        texto = "credito para startups em inovacao"
        resultado = extrair_palavras_chave(texto)

        assert isinstance(resultado, list)
        assert len(resultado) > 0
        assert "credito" in resultado or "startup" in resultado

    def test_extrair_palavras_chave_vazio(self):
        """Texto vazio retorna lista vazia"""
        resultado = extrair_palavras_chave("")
        assert resultado == []

    def test_extrair_remove_stop_words(self):
        """Remove palavras comuns (stop words)"""
        texto = "o acesso ao credito para as startups"
        resultado = extrair_palavras_chave(texto)

        # Nao deve incluir artigos
        assert "o" not in resultado
        assert "a" not in resultado
        assert "ao" not in resultado
        assert "as" not in resultado


class TestCalcularScoreRelevancia:
    """Testes para score de relevancia"""

    @pytest.mark.asyncio
    async def test_score_relevancia_query_presente(self):
        """Query presente no resultado deve ter score maior"""
        query = "credito para startups"
        resultado = "Como obter credito para startups em inovacao"

        score = await calcular_score_relevancia(resultado, query)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Alta relevancia

    @pytest.mark.asyncio
    async def test_score_relevancia_query_ausente(self):
        """Query ausente deve ter score baixo"""
        query = "credito para startups"
        resultado = "Como plantar arvores no jardim"

        score = await calcular_score_relevancia(resultado, query)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert score < 0.3  # Baixa relevancia

    @pytest.mark.asyncio
    async def test_score_relevancia_parcial(self):
        """Palavras-chave parciais devem ter score medio"""
        query = "credito para startups"
        resultado = "Startups precisam de investimento e credito"

        score = await calcular_score_relevancia(resultado, query)

        assert isinstance(score, float)
        assert 0.3 <= score <= 0.8  # Score medio


class TestCalcularScorePonderado:
    """Testes para score ponderado (4 fatores)"""

    def test_score_ponderado_estrutura(self):
        """Score ponderado deve considerar 4 fatores"""
        resultado = {
            "titulo": "Acesso ao credito para startups",
            "descricao": "Como obter credito de forma facil",
            "url": "https://example.com/credito",
            "fonte": "perplexity"
        }

        query = "credito para startups"

        score = calcular_score_ponderado(
            resultado=resultado,
            query=query,
            score_relevancia=0.8,
            num_ocorrencias=2,
            confiabilidade_fonte=0.9
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_score_ponderado_alto(self):
        """Score alto quando todos fatores sao positivos"""
        resultado = {
            "titulo": "Credito para startups",
            "descricao": "Solucao de credito para startups",
            "url": "https://example.com/credito",
            "fonte": "jina"
        }

        query = "credito startups"

        score = calcular_score_ponderado(
            resultado=resultado,
            query=query,
            score_relevancia=0.9,
            num_ocorrencias=5,
            confiabilidade_fonte=1.0
        )

        assert score > 0.7  # Score alto

    def test_score_ponderado_baixo(self):
        """Score baixo quando fatores sao negativos"""
        resultado = {
            "titulo": "Outro topico",
            "descricao": "Descricao irrelevante",
            "url": "https://example.com/outro",
            "fonte": "unknown"
        }

        query = "credito startups"

        score = calcular_score_ponderado(
            resultado=resultado,
            query=query,
            score_relevancia=0.1,
            num_ocorrencias=0,
            confiabilidade_fonte=0.2
        )

        assert score < 0.3  # Score baixo


class TestAvaliador:
    """Testes para classe Avaliador"""

    def test_avaliador_inicializa(self):
        """Avaliador deve inicializar sem erros"""
        avaliador = Avaliador()

        assert avaliador is not None
        assert isinstance(avaliador.fontes_confiabilidade, dict)

    def test_avaliador_confiabilidade_fonte(self):
        """Deve retornar score de confiabilidade por fonte"""
        avaliador = Avaliador()

        # Perplexity e Jina sao mais confiaveis
        score_perplexity = avaliador.get_confiabilidade_fonte("perplexity")
        score_jina = avaliador.get_confiabilidade_fonte("jina")
        score_unknown = avaliador.get_confiabilidade_fonte("unknown")

        assert score_perplexity > score_unknown
        assert score_jina > score_unknown

    @pytest.mark.asyncio
    async def test_avaliar_resultado_completo(self):
        """Metodo avaliar deve processar resultado completo"""
        avaliador = Avaliador()

        resultado = {
            "titulo": "Credito para startups",
            "descricao": "Como obter credito para inovacao",
            "url": "https://example.com",
            "fonte": "jina"
        }

        query = "credito startups"

        score = await avaliador.avaliar(resultado, query)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_avaliar_batch_resultados(self):
        """Deve avaliar multiplos resultados"""
        avaliador = Avaliador()

        resultados = [
            {
                "titulo": "Credito para startups",
                "descricao": "Como obter credito",
                "url": "https://example.com/1",
                "fonte": "jina"
            },
            {
                "titulo": "Investimento em inovacao",
                "descricao": "Oportunidades de investimento",
                "url": "https://example.com/2",
                "fonte": "perplexity"
            }
        ]

        query = "credito startups"

        scores = await avaliador.avaliar_batch(resultados, query)

        assert isinstance(scores, list)
        assert len(scores) == 2
        assert all(isinstance(s, float) for s in scores)
        assert all(0.0 <= s <= 1.0 for s in scores)
