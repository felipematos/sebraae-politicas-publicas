# -*- coding: utf-8 -*-
"""
Testes para deduplicador de resultados
"""
import pytest
from app.agente.deduplicador import (
    Deduplicador,
    calcular_hash_conteudo,
    calcular_similaridade,
    normalizar_para_hash
)


class TestNormalizarParaHash:
    """Testes para normalizacao de texto para hash"""

    def test_normalizar_remover_espacos(self):
        """Remove espacos extras"""
        texto = "credito   para    startups"
        resultado = normalizar_para_hash(texto)

        assert "   " not in resultado
        assert isinstance(resultado, str)

    def test_normalizar_lowercase(self):
        """Converte para minusculas"""
        texto = "CREDITO Para Startups"
        resultado = normalizar_para_hash(texto)

        assert resultado == resultado.lower()

    def test_normalizar_remove_pontuacao(self):
        """Remove pontuacao e caracteres especiais"""
        texto = "credito para startups!!! ???"
        resultado = normalizar_para_hash(texto)

        assert "!" not in resultado
        assert "?" not in resultado


class TestCalcularHashConteudo:
    """Testes para calculo de hash de conteudo"""

    def test_hash_mesmo_conteudo_mesmo_hash(self):
        """Mesmo conteudo produz mesmo hash"""
        conteudo = "Como obter credito para startups"

        hash1 = calcular_hash_conteudo(conteudo)
        hash2 = calcular_hash_conteudo(conteudo)

        assert hash1 == hash2

    def test_hash_conteudo_diferente_hash_diferente(self):
        """Conteudo diferente produz hash diferente"""
        conteudo1 = "Como obter credito"
        conteudo2 = "Como obter investimento"

        hash1 = calcular_hash_conteudo(conteudo1)
        hash2 = calcular_hash_conteudo(conteudo2)

        assert hash1 != hash2

    def test_hash_vazio(self):
        """Hash de conteudo vazio"""
        resultado = calcular_hash_conteudo("")

        assert isinstance(resultado, str)
        assert len(resultado) > 0

    def test_hash_case_insensitive(self):
        """Hash nao diferencia maiusculas/minusculas"""
        conteudo_upper = "CREDITO PARA STARTUPS"
        conteudo_lower = "credito para startups"

        hash_upper = calcular_hash_conteudo(conteudo_upper)
        hash_lower = calcular_hash_conteudo(conteudo_lower)

        assert hash_upper == hash_lower


class TestCalcularSimilaridade:
    """Testes para calculo de similaridade entre textos"""

    def test_similaridade_textos_identicos(self):
        """Textos identicos tem similaridade 1.0"""
        texto = "Como obter credito para startups"

        similaridade = calcular_similaridade(texto, texto)

        assert similaridade == 1.0

    def test_similaridade_textos_diferentes(self):
        """Textos completamente diferentes tem similaridade baixa"""
        texto1 = "Como obter credito para startups"
        texto2 = "Como plantar arvores no jardim"

        similaridade = calcular_similaridade(texto1, texto2)

        assert 0.0 <= similaridade < 0.3

    def test_similaridade_textos_parciais(self):
        """Textos parcialmente similares tem similaridade media"""
        texto1 = "credito para startups em inovacao"
        texto2 = "credito para startups em tecnologia"

        similaridade = calcular_similaridade(texto1, texto2)

        assert 0.5 <= similaridade <= 0.9

    def test_similaridade_ordem_irrelevante(self):
        """Similaridade por palavras, nao por ordem"""
        texto1 = "startups credito inovacao"
        texto2 = "inovacao credito startups"

        similaridade = calcular_similaridade(texto1, texto2)

        assert similaridade > 0.8


class TestDeduplicador:
    """Testes para classe Deduplicador"""

    def test_deduplicador_inicializa(self):
        """Deduplicador deve inicializar sem erros"""
        dedup = Deduplicador(threshold=0.8)

        assert dedup is not None
        assert dedup.threshold == 0.8
        assert len(dedup.hashes_vistos) == 0

    def test_deduplicador_adiciona_resultado(self):
        """Deve adicionar resultado unico"""
        dedup = Deduplicador()

        resultado = {
            "titulo": "Credito para startups",
            "descricao": "Como obter credito",
            "url": "https://example.com/1"
        }

        eh_novo = dedup.eh_novo(resultado)

        assert eh_novo is True

        # Segundo mesmo resultado eh duplicado
        eh_novo_again = dedup.eh_novo(resultado)
        assert eh_novo_again is False

    def test_deduplicador_detecta_duplicados_similares(self):
        """Deve detectar resultados muito similares como duplicados"""
        dedup = Deduplicador(threshold=0.7)

        resultado1 = {
            "titulo": "Credito para startups",
            "descricao": "Como obter credito",
            "url": "https://example.com/1"
        }

        resultado2 = {
            "titulo": "Credito para startups",
            "descricao": "Como obter credito",  # Identico
            "url": "https://example.com/2"
        }

        # Primeiro eh novo
        assert dedup.eh_novo(resultado1) is True

        # Segundo eh duplicado
        assert dedup.eh_novo(resultado2) is False

    def test_deduplicador_permite_similares_diferentes(self):
        """Deve permitir resultados diferentes mesmo parcialmente similares"""
        dedup = Deduplicador(threshold=0.8)

        resultado1 = {
            "titulo": "Credito para startups",
            "descricao": "Como obter credito bancario",
            "url": "https://example.com/1"
        }

        resultado2 = {
            "titulo": "Investimento para startups",
            "descricao": "Como obter investimento anjo",
            "url": "https://example.com/2"
        }

        # Ambos devem ser novos
        assert dedup.eh_novo(resultado1) is True
        assert dedup.eh_novo(resultado2) is True

    def test_deduplicador_incrementa_score_duplicados(self):
        """Deve incrementar score quando detecta duplicados"""
        dedup = Deduplicador()

        resultado = {
            "titulo": "Credito para startups",
            "descricao": "Como obter credito",
            "url": "https://example.com/1",
            "score": 0.8
        }

        # Primeiro eh novo
        resultado1_saida = dedup.processar(resultado)
        assert resultado1_saida["score"] == 0.8

        # Segundo incrementa score
        resultado2_saida = dedup.processar(resultado)
        assert resultado2_saida["score"] > 0.8

    def test_deduplicador_limpa_cache(self):
        """Deve permitir limpar o cache"""
        dedup = Deduplicador()

        resultado = {
            "titulo": "Credito para startups",
            "descricao": "Como obter credito",
            "url": "https://example.com/1"
        }

        dedup.eh_novo(resultado)
        assert len(dedup.hashes_vistos) > 0

        # Limpar
        dedup.limpar()
        assert len(dedup.hashes_vistos) == 0

    def test_deduplicador_batch(self):
        """Deve processar lote de resultados"""
        dedup = Deduplicador()

        resultados = [
            {
                "titulo": "Credito para startups",
                "descricao": "Como obter credito",
                "url": "https://example.com/1",
                "score": 0.8
            },
            {
                "titulo": "Credito para startups",  # Duplicado
                "descricao": "Como obter credito",
                "url": "https://example.com/1",
                "score": 0.8
            },
            {
                "titulo": "Investimento para startups",
                "descricao": "Como obter investimento",
                "url": "https://example.com/2",
                "score": 0.7
            }
        ]

        resultados_processados = dedup.processar_batch(resultados)

        # Deve ter removido ou marcado o duplicado
        assert len(resultados_processados) <= len(resultados)
        # Primeiro resultado intacto
        assert resultados_processados[0]["titulo"] == "Credito para startups"
