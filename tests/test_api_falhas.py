# -*- coding: utf-8 -*-
"""
Testes para endpoints de falhas de mercado
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Fixture para cliente de teste"""
    return TestClient(app)


class TestEndpointsFalhas:
    """Testes para endpoints de falhas"""

    def test_get_falhas_retorna_lista(self, client):
        """GET /api/falhas deve retornar lista de falhas"""
        response = client.get("/api/falhas")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_falhas_estrutura_correta(self, client):
        """GET /api/falhas deve retornar estrutura correta"""
        response = client.get("/api/falhas")
        data = response.json()
        falha = data[0]

        assert "id" in falha
        assert "titulo" in falha
        assert "pilar" in falha
        assert "descricao" in falha
        assert "dica_busca" in falha

    def test_get_falha_por_id(self, client):
        """GET /api/falhas/{id} deve retornar uma falha especifica"""
        response = client.get("/api/falhas/1")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == 1
        assert "titulo" in data
        assert "pilar" in data

    def test_get_falha_id_invalido(self, client):
        """GET /api/falhas/{id} com ID invalido deve retornar 404"""
        response = client.get("/api/falhas/99999")
        assert response.status_code == 404

    def test_get_resultados_falha(self, client):
        """GET /api/falhas/{id}/resultados deve retornar lista de resultados"""
        response = client.get("/api/falhas/1/resultados")
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        assert "falha" in data
        assert "resultados" in data
        assert isinstance(data["resultados"], list)
        assert "total_resultados" in data

    def test_get_resultados_falha_vazio(self, client):
        """GET /api/falhas/{id}/resultados com falha sem resultados"""
        response = client.get("/api/falhas/1/resultados")
        data = response.json()

        # Mesmo sem resultados, deve retornar estrutura valida
        assert data["total_resultados"] == 0
        assert data["resultados"] == []

    def test_get_falhas_com_paginacao(self, client):
        """GET /api/falhas com parametros de paginacao"""
        response = client.get("/api/falhas?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10

    def test_get_falhas_filtro_por_pilar(self, client):
        """GET /api/falhas com filtro por pilar"""
        response = client.get("/api/falhas?pilar=6.%20Regulacao")
        assert response.status_code == 200
        data = response.json()

        # Todos os resultados devem ter o pilar solicitado
        for falha in data:
            assert "Regulacao" in falha["pilar"] or len(data) == 0
