# -*- coding: utf-8 -*-
"""
Cliente para integração com Exa AI Search
Exa é um search engine especializado para aplicações de IA
Documentação: https://docs.exa.ai/reference
"""
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime


class ExaClient:
    """Cliente para realizar buscas usando Exa AI"""

    def __init__(self, api_key: str):
        """
        Inicializa o cliente Exa

        Args:
            api_key: Chave da API Exa
        """
        self.api_key = api_key
        self.base_url = "https://api.exa.ai"
        self.timeout = httpx.Timeout(60.0)

    async def pesquisar(
        self,
        query: str,
        idioma: str = "pt",
        max_resultados: int = 5,
        search_type: str = "auto"
    ) -> List[Dict[str, Any]]:
        """
        Realiza uma busca usando Exa AI

        Args:
            query: Termo de busca
            idioma: Idioma (pt, en, es, etc) - nota: Exa busca em qualquer idioma automaticamente
            max_resultados: Número máximo de resultados (máximo 100 para neural)
            search_type: Tipo de busca ("keyword", "neural", "fast", "auto")

        Returns:
            Lista de dicionários com resultado de busca
            Cada item contém: titulo, url, descricao, data_publicacao (opcional)
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Limitar número de resultados
                num_results = min(max_resultados, 100)

                # Preparar payload para Exa
                payload = {
                    "query": query,
                    "numResults": num_results,
                    "type": search_type,
                    "contents": {
                        "text": True,
                    }
                }

                # Headers com autenticação
                headers = {
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json"
                }

                # Realizar a requisição
                response = await client.post(
                    f"{self.base_url}/search",
                    json=payload,
                    headers=headers
                )

                # Verificar status
                if response.status_code == 401:
                    raise Exception("Exa API: Chave da API inválida ou expirada")
                elif response.status_code == 429:
                    raise Exception("Exa API: Rate limit atingido")
                elif response.status_code != 200:
                    raise Exception(f"Exa API: Erro {response.status_code} - {response.text[:200]}")

                # Parsear resposta
                data = response.json()
                results = data.get("results", [])

                # Transformar formato para padronizado
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        "titulo": result.get("title", ""),
                        "url": result.get("url", ""),
                        "descricao": result.get("text", "")[:500],  # Limitar descrição
                        "data_publicacao": result.get("publishedDate", None),
                        "fonte": "Exa AI"
                    })

                return formatted_results

        except httpx.TimeoutException:
            raise Exception("Exa API: Timeout na requisição")
        except httpx.RequestError as e:
            raise Exception(f"Exa API: Erro de conexão - {str(e)}")
        except ValueError as e:
            raise Exception(f"Exa API: Erro ao parsear resposta - {str(e)}")

    async def buscar_similar(
        self,
        url: str,
        max_resultados: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Encontra páginas semanticamente similares a uma URL fornecida

        Args:
            url: URL base para encontrar similares
            max_resultados: Número máximo de resultados

        Returns:
            Lista de URLs similares
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "url": url,
                    "numResults": min(max_resultados, 100),
                    "contents": {
                        "text": True,
                    }
                }

                headers = {
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json"
                }

                response = await client.post(
                    f"{self.base_url}/find-similar",
                    json=payload,
                    headers=headers
                )

                if response.status_code != 200:
                    raise Exception(f"Exa API (similar): Erro {response.status_code}")

                data = response.json()
                results = data.get("results", [])

                formatted_results = []
                for result in results:
                    formatted_results.append({
                        "titulo": result.get("title", ""),
                        "url": result.get("url", ""),
                        "descricao": result.get("text", "")[:500],
                        "fonte": "Exa AI (Similar)"
                    })

                return formatted_results

        except Exception as e:
            raise Exception(f"Exa API (buscar_similar): {str(e)}")
