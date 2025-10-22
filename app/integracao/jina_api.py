# -*- coding: utf-8 -*-
"""
Cliente para Jina AI API (web search e content extraction)
"""
import httpx
from typing import List, Dict, Any
from urllib.parse import quote


class JinaClient:
    """Cliente para busca web e extracao de conteudo via Jina"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.jina.ai"
        self.search_url = "https://s.jina.ai"
        self.timeout = httpx.Timeout(60.0)

    async def search_web(
        self,
        query: str,
        idioma: str = "en",
        max_resultados: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busca web via Jina

        Args:
            query: Termos de busca
            idioma: Idioma da pesquisa
            max_resultados: Maximo de resultados

        Returns:
            Lista de resultados com titulo, url, descricao
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Jina search API simples
                search_query = f"{query} lang:{idioma}"
                encoded_query = quote(search_query)

                response = await client.get(
                    f"{self.search_url}/{encoded_query}",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )

                if response.status_code == 200:
                    # Jina retorna em formato estruturado
                    try:
                        data = response.json()
                        resultados = self._parsear_resultados_search(data)
                    except:
                        # Se nao for JSON, parsear como texto
                        resultados = self._parsear_texto_simples(response.text)

                    return resultados[:max_resultados]
                else:
                    raise Exception(f"Jina search error: {response.status_code}")

        except Exception as e:
            print(f"Erro em JinaClient.search_web: {e}")
            return []

    async def read_url(self, url: str) -> str:
        """
        Extrai conteudo de uma URL usando Jina

        Args:
            url: URL para extrair

        Returns:
            Conteudo extraido em texto limpo
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/readability",
                    params={"url": url},
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )

                if response.status_code == 200:
                    try:
                        data = response.json()
                        return data.get("data", {}).get("content", "")
                    except:
                        return response.text
                else:
                    raise Exception(f"Jina readability error: {response.status_code}")

        except Exception as e:
            print(f"Erro em JinaClient.read_url: {e}")
            return ""

    def _parsear_resultados_search(self, data: Dict) -> List[Dict[str, Any]]:
        """Parseia resultado estruturado do Jina"""
        resultados = []

        # Estrutura esperada do Jina
        if isinstance(data, dict):
            items = data.get("results", []) or data.get("data", []) or []
        else:
            items = []

        for item in items:
            if isinstance(item, dict):
                resultados.append({
                    "titulo": item.get("title", ""),
                    "url": item.get("url", ""),
                    "descricao": item.get("description", "")[:200]
                })

        return resultados

    def _parsear_texto_simples(self, texto: str) -> List[Dict[str, Any]]:
        """Fallback: parseia resposta como texto simples"""
        resultados = []

        # Simples fallback
        linhas = texto.split("\n")
        for linha in linhas:
            if "http" in linha.lower():
                resultados.append({
                    "titulo": "Resultado Jina",
                    "url": linha.strip(),
                    "descricao": ""
                })

        # Se vazio, retornar algo
        if not resultados:
            resultados = [{
                "titulo": "Resultado Jina",
                "url": "https://jina.ai",
                "descricao": texto[:200]
            }]

        return resultados
