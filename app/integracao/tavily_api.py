# -*- coding: utf-8 -*-
"""
Cliente para Tavily Search API
Usa inteligência artificial para buscar e resumir informações
"""
import httpx
from typing import List, Dict, Any
import asyncio


class TavilyClient:
    """Cliente para pesquisas via Tavily Search API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.tavily.com"
        self.timeout = httpx.Timeout(60.0)

    async def pesquisar(
        self,
        query: str,
        idioma: str = "pt",
        max_resultados: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Realiza pesquisa via Tavily

        Args:
            query: Termos de busca
            idioma: Idioma da pesquisa
            max_resultados: Maximo de resultados

        Returns:
            Lista de resultados com titulo, url, descricao
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "api_key": self.api_key,
                    "query": query,
                    "include_answer": True,
                    "max_results": max_resultados,
                    "topic": "general"
                }

                response = await client.post(
                    f"{self.base_url}/search",
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    resultados = self._parsear_resposta(data)
                    return resultados[:max_resultados]
                else:
                    raise Exception(f"Tavily error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Erro em TavilyClient.pesquisar: {e}")
            return []

    def _parsear_resposta(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parseia resposta do Tavily e extrai resultados

        Args:
            data: Resposta da API Tavily

        Returns:
            Lista de resultados padronizados
        """
        resultados = []

        # Extrair resposta resumida se disponível
        if data.get("answer"):
            resultados.append({
                "titulo": "Resumo da Pesquisa",
                "url": "https://tavily.com",
                "descricao": data.get("answer", "")[:500]
            })

        # Extrair resultados individuais
        for resultado in data.get("results", []):
            resultados.append({
                "titulo": resultado.get("title", "Resultado Tavily"),
                "url": resultado.get("url", ""),
                "descricao": resultado.get("content", "")[:500]
            })

        return resultados
