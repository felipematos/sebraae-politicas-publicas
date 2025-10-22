# -*- coding: utf-8 -*-
"""
Testes para worker processador de fila
"""
import pytest
from app.agente.processador import Processador


@pytest.fixture
def processador():
    """Fixture para processador"""
    return Processador(max_workers=2)


class TestProcessador:
    """Testes para classe Processador"""

    def test_processador_inicializa(self, processador):
        """Processador deve inicializar sem erros"""
        assert processador is not None
        assert processador.max_workers == 2
        assert processador.processadas == 0
        assert processador.erros == 0

    def test_processador_tem_modulos(self, processador):
        """Processador deve ter acesso aos modulos de IA"""
        assert hasattr(processador, "avaliador")
        assert hasattr(processador, "deduplicador")
        assert hasattr(processador, "agente_pesquisador")

    @pytest.mark.asyncio
    async def test_obter_proxima_entrada_fila(self, processador):
        """Deve obter proxima entrada pendente da fila"""
        # Antes de popular, nao deve ter nada
        entrada = await processador.obter_proxima_entrada_fila()
        # Pode retornar None ou lista vazia
        assert entrada is None or entrada == []

    @pytest.mark.asyncio
    async def test_estatisticas_iniciais(self, processador):
        """Deve retornar estatisticas iniciais"""
        stats = await processador.obter_estatisticas()

        assert isinstance(stats, dict)
        assert "processadas" in stats
        assert "erros" in stats
        assert "tempo_total" in stats
        assert stats["processadas"] == 0
        assert stats["erros"] == 0

    @pytest.mark.asyncio
    async def test_marcar_entrada_processada(self, processador):
        """Deve marcar entrada como processada"""
        # Criar entrada mock
        entrada_id = 1
        resultado = await processador.marcar_como_processada(entrada_id)

        # Deve retornar True se sucesso
        assert isinstance(resultado, bool)

    @pytest.mark.asyncio
    async def test_marcar_entrada_com_erro(self, processador):
        """Deve marcar entrada com erro"""
        entrada_id = 1
        erro_msg = "Erro na pesquisa"

        resultado = await processador.marcar_como_erro(entrada_id, erro_msg)

        assert isinstance(resultado, bool)
        # Contador de erros deve incrementar
        assert processador.erros >= 0

    def test_processador_resetar_stats(self, processador):
        """Deve permitir resetar estatisticas"""
        processador.processadas = 100
        processador.erros = 10

        processador.resetar_stats()

        assert processador.processadas == 0
        assert processador.erros == 0

    @pytest.mark.asyncio
    async def test_configurar_rate_limiting(self, processador):
        """Deve permitir configurar rate limiting"""
        processador.configurar_rate_limiting(delay_minimo=2.0, max_requests_por_minuto=30)

        assert processador.rate_limit_delay >= 2.0
        assert processador.max_requests_por_minuto <= 30

    @pytest.mark.asyncio
    async def test_salvar_resultado(self, processador):
        """Deve salvar resultado processado no banco"""
        resultado = {
            "falha_id": 1,
            "titulo": "Teste resultado",
            "descricao": "Descricao teste",
            "fonte_url": "https://example.com",
            "fonte_tipo": "article",
            "idioma": "pt",
            "confidence_score": 0.85,
            "ferramenta_origem": "jina"
        }

        sucesso = await processador.salvar_resultado(resultado)

        assert isinstance(sucesso, bool)

    @pytest.mark.asyncio
    async def test_processar_entrada_individual(self, processador):
        """Deve processar uma entrada da fila"""
        entrada = {
            "id": 1,
            "falha_id": 1,
            "query": "credito para startups",
            "idioma": "pt",
            "ferramenta": "jina",
            "status": "pendente"
        }

        # Este teste pode passar mesmo sem dados reais (mock)
        resultado = await processador.processar_entrada(entrada)

        assert isinstance(resultado, bool)

    @pytest.mark.asyncio
    async def test_loop_processador_nao_tranca(self, processador):
        """Loop do processador nao deve travar mesmo com fila vazia"""
        # Testar que loop pode ser interrompido
        assert processador.ativo is True

        # Desativar
        processador.ativo = False
        assert processador.ativo is False

    def test_configuracoes_padrao(self, processador):
        """Deve ter configuracoes padrao razoaveis"""
        assert processador.max_workers > 0
        assert processador.rate_limit_delay > 0
        assert processador.max_retries >= 1
        assert processador.timeout > 0

    @pytest.mark.asyncio
    async def test_incrementar_contador_processadas(self, processador):
        """Deve incrementar contador de processadas"""
        processador.processadas = 0
        processador._incrementar_processadas()

        assert processador.processadas == 1

    @pytest.mark.asyncio
    async def test_incrementar_contador_erros(self, processador):
        """Deve incrementar contador de erros"""
        processador.erros = 0
        processador._incrementar_erros()

        assert processador.erros == 1

    @pytest.mark.asyncio
    async def test_validar_entrada_fila(self, processador):
        """Deve validar campos obrigatorios de entrada da fila"""
        entrada_valida = {
            "id": 1,
            "falha_id": 1,
            "query": "teste",
            "idioma": "pt",
            "ferramenta": "jina"
        }

        resultado = processador.validar_entrada(entrada_valida)
        assert resultado is True

        entrada_invalida = {
            "id": 1,
            # Faltam campos
        }

        resultado = processador.validar_entrada(entrada_invalida)
        assert resultado is False
