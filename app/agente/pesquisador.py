# -*- coding: utf-8 -*-
"""
Agente pesquisador IA
Orquestra pesquisas multilingues usando multiplas ferramentas
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from app.config import settings
from app.database import (
    get_falhas_mercado,
    inserir_fila_pesquisa,
    listar_fila_pesquisas,
    deletar_fila_pesquisa,
    contar_fila_pesquisas
)
from app.utils.idiomas import gerar_queries_multilingues
from app.agente.avaliador import Avaliador
from app.agente.deduplicador import Deduplicador
from app.integracao.perplexity_api import PerplexityClient
from app.integracao.jina_api import JinaClient
from app.integracao.deep_research_mcp import DeepResearchClient


class AgentePesquisador:
    """Agente principal para pesquisa de solucoes de politica publica"""

    def __init__(self):
        """Inicializa agente com clientes e modulos auxiliares"""
        # Idiomas suportados
        self.idiomas = settings.IDIOMAS

        # Ferramentas de pesquisa
        self.ferramentas = settings.FERRAMENTAS

        # Clients de APIs externas
        self._inicializar_clientes()

        # Modulos auxiliares
        self.avaliador = Avaliador()
        self.deduplicador = Deduplicador(threshold=0.8)

        # Estatisticas
        self.queries_executadas = 0
        self.resultados_encontrados = 0
        self.tempo_inicio = None

    def _inicializar_clientes(self):
        """Inicializa clients de APIs externas"""
        try:
            self.perplexity_client = PerplexityClient(
                settings.PERPLEXITY_API_KEY
            )
        except Exception as e:
            print(f"Aviso: Perplexity client nao inicializado: {e}")
            self.perplexity_client = None

        try:
            self.jina_client = JinaClient(
                settings.JINA_API_KEY
            )
        except Exception as e:
            print(f"Aviso: Jina client nao inicializado: {e}")
            self.jina_client = None

        # Deep Research nao precisa de API key (usa MCP)
        self.deep_research_client = DeepResearchClient()

    async def gerar_queries(self, falha: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Gera queries multilingues para uma falha de mercado

        Args:
            falha: Dicionario com id, titulo, descricao, dica_busca

        Returns:
            Lista de queries geradas
        """
        queries = await gerar_queries_multilingues(falha)
        return queries

    async def popular_fila(
        self,
        falhas: Optional[List[Dict[str, Any]]] = None,
        falhas_ids: Optional[List[int]] = None,
        ferramentas_filtro: Optional[List[str]] = None,
        idiomas_filtro: Optional[List[str]] = None
    ) -> int:
        """
        Popular fila de pesquisas com queries para falhas

        Args:
            falhas: Lista de falhas (se None, busca todas do banco)
            falhas_ids: IDs especificas de falhas (alternativa)
            ferramentas_filtro: Listar apenas ferramentas especificas
            idiomas_filtro: Limitar a idiomas especificos

        Returns:
            Total de queries adicionadas a fila
        """
        # Se nao passou falhas, buscar do banco
        if falhas is None:
            if falhas_ids:
                # TODO: Implementar filtro por IDs no database.py
                falhas = await get_falhas_mercado()
                falhas = [f for f in falhas if f["id"] in falhas_ids]
            else:
                falhas = await get_falhas_mercado()

        # Ferramentas para usar
        ferramentas = ferramentas_filtro or self.ferramentas

        # Idiomas para usar
        idiomas = idiomas_filtro or self.idiomas

        total_adicionado = 0

        # Para cada falha
        for falha in falhas:
            # Gerar queries
            queries = await self.gerar_queries(falha)

            # Filtrar por idioma e ferramenta se necessario
            if idiomas_filtro or ferramentas_filtro:
                queries = [
                    q for q in queries
                    if (not idiomas_filtro or q["idioma"] in idiomas_filtro)
                ]

            # Para cada query, gerar uma entrada para cada ferramenta
            for query in queries:
                for ferramenta in ferramentas:
                    entrada_fila = {
                        "falha_id": falha["id"],
                        "query": query["query"],
                        "idioma": query["idioma"],
                        "ferramenta": ferramenta,
                        "status": "pendente",
                        "criado_em": datetime.now().isoformat()
                    }

                    # Inserir na fila
                    await inserir_fila_pesquisa(entrada_fila)
                    total_adicionado += 1

                    # Rate limiting
                    await asyncio.sleep(0.01)

        return total_adicionado

    async def obter_progresso(self) -> Dict[str, Any]:
        """
        Obtem progresso atual de pesquisas

        Returns:
            Dicionario com stats de progresso
        """
        total_fila = await contar_fila_pesquisas()
        pendentes = await contar_fila_pesquisas(status="pendente")
        processadas = total_fila - pendentes

        percentual = 0.0
        if total_fila > 0:
            percentual = (processadas / total_fila) * 100

        return {
            "fila_total": total_fila,
            "fila_pendente": pendentes,
            "processadas": processadas,
            "percentual": percentual,
            "queries_executadas": self.queries_executadas,
            "resultados_encontrados": self.resultados_encontrados
        }

    async def executar_pesquisa(
        self,
        query: str,
        idioma: str = "pt",
        ferramentas: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executa pesquisa com uma query especifica

        Args:
            query: Query para pesquisar
            idioma: Idioma da pesquisa
            ferramentas: Lista de ferramentas a usar

        Returns:
            Lista de resultados encontrados
        """
        ferramentas = ferramentas or self.ferramentas
        resultados = []

        for ferramenta in ferramentas:
            try:
                if ferramenta == "perplexity" and self.perplexity_client:
                    resultado = await self.perplexity_client.pesquisar(
                        query=query,
                        idioma=idioma,
                        max_resultados=5
                    )
                    resultados.extend(resultado)

                elif ferramenta == "jina" and self.jina_client:
                    resultado = await self.jina_client.search_web(
                        query=query,
                        idioma=idioma,
                        max_resultados=10
                    )
                    resultados.extend(resultado)

                elif ferramenta == "deep_research":
                    resultado = await self.deep_research_client.pesquisar(
                        query=query,
                        sources="both"
                    )
                    resultados.extend(resultado)

                # Rate limiting entre ferramentas
                await asyncio.sleep(1.0)

            except Exception as e:
                print(f"Erro executando pesquisa com {ferramenta}: {e}")
                continue

        self.queries_executadas += 1
        self.resultados_encontrados += len(resultados)

        return resultados

    async def limpar_fila(self):
        """Limpa toda a fila de pesquisas"""
        # Get todas as entradas
        fila = await listar_fila_pesquisas()

        # Deletar uma por uma (no futuro, adicionar DELETE bulk)
        for entrada in fila:
            await deletar_fila_pesquisa(entrada["id"])

    def resetar_estatisticas(self):
        """Reseta contadores de estatisticas"""
        self.queries_executadas = 0
        self.resultados_encontrados = 0
        self.tempo_inicio = None

    async def executar_pesquisa_completa(
        self,
        falha_id: int,
        max_resultados_por_ferramenta: int = 10
    ) -> Dict[str, Any]:
        """
        Executa pesquisa completa para uma falha especifica

        Args:
            falha_id: ID da falha a pesquisar
            max_resultados_por_ferramenta: Maximo de resultados por fonte

        Returns:
            Dicionario com resultados e stats
        """
        # TODO: Implementar logica completa de pesquisa
        # 1. Get falha do banco
        # 2. Gerar queries
        # 3. Executar pesquisas
        # 4. Avaliar resultados
        # 5. Deduplicar
        # 6. Salvar no banco

        return {
            "status": "not_implemented",
            "message": "Metodo sera implementado na proxima versao"
        }

    async def sincronizar_com_banco(self):
        """
        Sincroniza agente com banco de dados
        Carrega falhas e gera queries se necessario
        """
        # Get falhas do banco
        falhas = await get_falhas_mercado()

        # Verificar quantas queries ja existem na fila
        fila_atual = await contar_fila_pesquisas()

        if fila_atual == 0:
            # Fila vazia, popular
            print(f"Populando fila com {len(falhas)} falhas...")
            total = await self.popular_fila(falhas)
            print(f"Fila populada com {total} queries")

        return fila_atual


async def main_popular_fila():
    """
    CLI: Popular fila de pesquisas
    Uso: python -m app.agente.pesquisador popular_fila
    """
    print("Iniciando populacao da fila de pesquisas...")

    agente = AgentePesquisador()

    # Get todas as falhas
    falhas = await get_falhas_mercado()
    print(f"Total de falhas: {len(falhas)}")

    # Popular fila
    total = await agente.popular_fila(falhas)
    print(f"Total de queries adicionadas: {total}")

    # Mostrar progresso
    progresso = await agente.obter_progresso()
    print(f"\nProgresso: {progresso}")


async def main_limpar_fila():
    """
    CLI: Limpar fila de pesquisas
    Uso: python -m app.agente.pesquisador limpar_fila
    """
    print("Limpando fila de pesquisas...")

    agente = AgentePesquisador()
    await agente.limpar_fila()

    print("Fila limpa com sucesso")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        comando = sys.argv[1]

        if comando == "popular_fila":
            asyncio.run(main_popular_fila())
        elif comando == "limpar_fila":
            asyncio.run(main_limpar_fila())
        else:
            print(f"Comando desconhecido: {comando}")
            print("Comandos disponibles:")
            print("  popular_fila - Popular fila com queries")
            print("  limpar_fila - Limpar toda a fila")
    else:
        print("Agente pesquisador IA - Sebrae Nacional")
        print("\nUso: python -m app.agente.pesquisador <comando>")
        print("\nComandos:")
        print("  popular_fila - Popular fila com queries de todas as falhas")
        print("  limpar_fila - Limpar toda a fila de pesquisas")
