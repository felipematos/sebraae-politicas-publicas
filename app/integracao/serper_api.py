# -*- coding: utf-8 -*-
"""
Cliente para Serper API
Google Search com acesso via API
"""
import httpx
from typing import List, Dict, Any


class SerperClient:
    """Cliente para pesquisas via Serper (Google Search API)"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://google.serper.dev"
        self.timeout = httpx.Timeout(60.0)

    async def pesquisar(
        self,
        query: str,
        idioma: str = "pt",
        max_resultados: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Realiza pesquisa via Google Search (Serper)

        Args:
            query: Termos de busca
            idioma: Idioma da pesquisa
            max_resultados: Maximo de resultados

        Returns:
            Lista de resultados com titulo, url, descricao
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json"
                }

                payload = {
                    "q": query,
                    "num": max_resultados,
                    "gl": self._get_country_code(idioma),
                    "hl": idioma
                }

                response = await client.post(
                    f"{self.base_url}/search",
                    json=payload,
                    headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    resultados = self._parsear_resposta(data)
                    return resultados[:max_resultados]
                else:
                    raise Exception(f"Serper error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Erro em SerperClient.pesquisar: {e}")
            return []

    def _parsear_resposta(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parseia resposta do Serper e extrai resultados

        Args:
            data: Resposta da API Serper

        Returns:
            Lista de resultados padronizados
        """
        from app.utils.url_validator import eh_url_valida

        resultados = []

        # Extrair resposta de knowledge graph se disponível
        knowledge_graph = data.get("knowledgeGraph", {})
        if knowledge_graph.get("description"):
            url = knowledge_graph.get("website", "").strip()
            # Só incluir se tiver URL válida
            if url and eh_url_valida(url):
                resultados.append({
                    "titulo": knowledge_graph.get("title", "Resultado Serper"),
                    "url": url,
                    "descricao": knowledge_graph.get("description", "")[:500]
                })

        # Extrair resultados de busca orgânica
        for resultado in data.get("organic", []):
            url = resultado.get("link", "").strip()
            # Só incluir se tiver URL válida
            if url and eh_url_valida(url):
                resultados.append({
                    "titulo": resultado.get("title", "Resultado Google"),
                    "url": url,
                    "descricao": resultado.get("snippet", "")[:500]
                })

        return resultados

    def _get_country_code(self, idioma: str) -> str:
        """
        Mapeia idioma para código de país Serper

        Args:
            idioma: Código de idioma (pt, en, es, etc)

        Returns:
            Código de país para Serper
        """
        mapa_paises = {
            "pt": "br",  # Brazil para português
            "en": "us",  # USA para inglês
            "es": "es",  # Spain para espanhol
            "fr": "fr",  # France para francês
            "de": "de",  # Germany para alemão
            "it": "it",  # Italy para italiano
            "ar": "sa",  # Saudi Arabia para árabe
            "ko": "kr",  # South Korea para coreano
            "he": "il",  # Israel para hebraico
        }
        return mapa_paises.get(idioma, "us")
