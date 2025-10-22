# -*- coding: utf-8 -*-
"""
Testes para agente pesquisador
"""
import pytest
from app.agente.pesquisador import AgentePesquisador


@pytest.fixture
def agente():
    """Fixture para agente pesquisador"""
    return AgentePesquisador()


class TestAgentePesquisador:
    """Testes para classe AgentePesquisador"""

    def test_agente_inicializa(self, agente):
        """Agente deve inicializar sem erros"""
        assert agente is not None
        assert agente.idiomas is not None
        assert len(agente.idiomas) >= 8

    def test_agente_tem_clientes_configurados(self, agente):
        """Agente deve ter acesso aos clientes de API"""
        assert hasattr(agente, "perplexity_client")
        assert hasattr(agente, "jina_client")
        assert hasattr(agente, "deep_research_client")

    @pytest.mark.asyncio
    async def test_gerar_queries_para_falha(self, agente):
        """Deve gerar queries multilingues para uma falha"""
        falha = {
            "id": 1,
            "titulo": "Falta de acesso a credito",
            "descricao": "Startups tem dificuldade em obter financiamento",
            "dica_busca": "credito, financiamento, startup"
        }

        queries = await agente.gerar_queries(falha)

        assert isinstance(queries, list)
        assert len(queries) >= 40  # 5+ variacoes x 8 idiomas

        # Verificar estrutura
        for query in queries:
            assert "query" in query
            assert "idioma" in query
            assert "falha_id" in query
            assert query["falha_id"] == 1

    @pytest.mark.asyncio
    async def test_gerar_queries_quantidade_correta(self, agente):
        """Quantidade de queries deve ser consistente"""
        falha = {
            "id": 1,
            "titulo": "Falta de acesso a credito",
            "descricao": "Startups tem dificuldade em obter financiamento",
            "dica_busca": "credito, financiamento, startup"
        }

        queries = await agente.gerar_queries(falha)

        # 6 variacoes x 9 idiomas = 54 queries (maximo)
        assert 40 <= len(queries) <= 60

    @pytest.mark.asyncio
    async def test_popular_fila_uma_falha(self, agente):
        """Deve popular fila com queries de uma falha"""
        falha = {
            "id": 1,
            "titulo": "Falta de acesso a credito",
            "descricao": "Startups tem dificuldade em obter financiamento",
            "dica_busca": "credito, financiamento"
        }

        # Popular fila
        total_adicionado = await agente.popular_fila([falha])

        assert total_adicionado > 0
        assert total_adicionado >= 40  # Minimo de queries

    @pytest.mark.asyncio
    async def test_popular_fila_multiplas_falhas(self, agente):
        """Deve popular fila com queries de multiplas falhas"""
        falhas = [
            {
                "id": 1,
                "titulo": "Falta de acesso a credito",
                "descricao": "Startups tem dificuldade em obter financiamento",
                "dica_busca": "credito, financiamento"
            },
            {
                "id": 2,
                "titulo": "Falta de talento tech",
                "descricao": "Dificuldade em contratar profissionais",
                "dica_busca": "talento, tech, contratacao"
            }
        ]

        total_adicionado = await agente.popular_fila(falhas)

        # Deve adicionar queries de ambas as falhas
        assert total_adicionado >= 80

    @pytest.mark.asyncio
    async def test_obter_progresso(self, agente):
        """Deve retornar progresso de pesquisa"""
        progresso = await agente.obter_progresso()

        assert isinstance(progresso, dict)
        assert "fila_total" in progresso
        assert "fila_pendente" in progresso
        assert "processadas" in progresso
        assert "percentual" in progresso

    @pytest.mark.asyncio
    async def test_obter_progresso_formato(self, agente):
        """Progresso deve ter valores numericos validos"""
        progresso = await agente.obter_progresso()

        assert isinstance(progresso["fila_total"], int)
        assert isinstance(progresso["fila_pendente"], int)
        assert isinstance(progresso["processadas"], int)
        assert isinstance(progresso["percentual"], float)

        # Percentual entre 0 e 100
        assert 0 <= progresso["percentual"] <= 100

    @pytest.mark.asyncio
    async def test_executar_pesquisa_query_simples(self, agente):
        """Deve executar pesquisa de uma query simples"""
        query = "credito para startups"

        # Nota: Este teste pode falhar se as API keys nao estiverem configuradas
        # Usar mock em producao
        resultado = await agente.executar_pesquisa(
            query=query,
            idioma="pt",
            ferramentas=["jina"]  # Usar apenas Jina para nao usar muitos requests
        )

        assert isinstance(resultado, list)
        # Pode retornar vazio se API nao estiver configurada, mas deve ser lista

    @pytest.mark.asyncio
    async def test_limpar_fila(self, agente):
        """Deve permitir limpar a fila"""
        # Primeiro popular
        falha = {
            "id": 1,
            "titulo": "Teste",
            "descricao": "Teste",
            "dica_busca": "teste"
        }

        await agente.popular_fila([falha])

        progresso_antes = await agente.obter_progresso()
        assert progresso_antes["fila_total"] > 0

        # Limpar
        await agente.limpar_fila()

        progresso_depois = await agente.obter_progresso()
        assert progresso_depois["fila_total"] == 0

    @pytest.mark.asyncio
    async def test_inicializar_com_api_keys(self):
        """Agente deve inicializar mesmo sem API keys configuradas"""
        # Isso testa que nao vai lancar erro ao carregar config
        agente = AgentePesquisador()
        assert agente is not None
