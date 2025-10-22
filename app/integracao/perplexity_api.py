# -*- coding: utf-8 -*-
"""
Cliente para Perplexity AI API
"""
import httpx
from typing import List, Dict, Any
import asyncio


class PerplexityClient:
    """Cliente para pesquisas via Perplexity AI"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai"
        self.model = "sonar"  # Updated from deprecated pplx-7b-online
        self.timeout = httpx.Timeout(60.0)

    async def pesquisar(
        self,
        query: str,
        idioma: str = "en",
        max_resultados: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Realiza pesquisa via Perplexity

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
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Pesquise sobre: {query}. Retorne em {idioma}. Liste 5 fontes com titulo e URL."
                        }
                    ]
                }

                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                    # Parsear resposta e extrair resultados
                    resultados = self._parsear_resposta(content)
                    return resultados[:max_resultados]
                else:
                    raise Exception(f"Perplexity error: {response.status_code}")

        except Exception as e:
            print(f"Erro em PerplexityClient.pesquisar: {e}")
            return []

    def _parsear_resposta(self, content: str) -> List[Dict[str, Any]]:
        """
        Parseia resposta do Perplexity e extrai resultados

        Esperado formato com URLs e titulos
        """
        resultados = []

        # Simples parsing - procura por padroes de URL e texto antes delas
        linhas = content.split("\n")
        titulo_temp = ""

        for linha in linhas:
            linha = linha.strip()

            if not linha:
                continue

            # Detectar URL
            if "http" in linha.lower():
                url = None
                for palavra in linha.split():
                    if "http" in palavra.lower():
                        url = palavra.strip("()[].,")
                        break

                if url:
                    resultados.append({
                        "titulo": titulo_temp or "Resultado Perplexity",
                        "url": url,
                        "descricao": linha
                    })
                    titulo_temp = ""
            else:
                titulo_temp = linha[:100]

        # Se nao encontrou nenhum resultado, retornar placeholder
        if not resultados:
            resultados = [
                {
                    "titulo": "Resultado Perplexity",
                    "url": "https://www.perplexity.ai",
                    "descricao": content[:200]
                }
            ]

        return resultados
