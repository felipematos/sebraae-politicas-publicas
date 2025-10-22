# -*- coding: utf-8 -*-
"""
Cliente para Jina AI API (web search e content extraction)
Inclui graceful degradation para erros de API (402, 429)
"""
import httpx
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import quote
from datetime import datetime


class JinaClient:
    """Cliente para busca web e extracao de conteudo via Jina com fallback"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.jina.ai"
        self.search_url = "https://s.jina.ai"
        self.timeout = httpx.Timeout(60.0)

        # Rastreamento de status degradado
        self.degradacao_ativa = False
        self.motivo_degradacao = None
        self.timestamp_degradacao = None

    def _detectar_degradacao(self, status_code: int) -> Optional[str]:
        """
        Detecta se deve ativar degradacao baseado em status code

        Args:
            status_code: Código HTTP da resposta

        Returns:
            Motivo da degradacao ou None
        """
        if status_code == 402:
            return "Sem saldo na API Jina (402 Payment Required)"
        elif status_code == 429:
            return "Taxa de requisições excedida (429 Too Many Requests)"
        return None

    async def search_web(
        self,
        query: str,
        idioma: str = "en",
        max_resultados: int = 10
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Busca web via Jina com graceful degradation

        Args:
            query: Termos de busca
            idioma: Idioma da pesquisa
            max_resultados: Maximo de resultados

        Returns:
            Tupla (lista_resultados, usando_fallback)
            - lista_resultados: Lista de resultados com titulo, url, descricao
            - usando_fallback: True se usando fallback sem API
        """
        # Se ja em degradacao, usar fallback
        if self.degradacao_ativa:
            print(f"[JINA DEGRADED] {self.motivo_degradacao} - Usando fallback")
            return [], True

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Jina search API simples
                search_query = f"{query} lang:{idioma}"
                encoded_query = quote(search_query)

                response = await client.get(
                    f"{self.search_url}/{encoded_query}",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )

                # Verificar erros de degradacao
                motivo = self._detectar_degradacao(response.status_code)
                if motivo:
                    self.degradacao_ativa = True
                    self.motivo_degradacao = motivo
                    self.timestamp_degradacao = datetime.now()
                    print(f"[JINA DEGRADATION ACTIVATED] {motivo}")
                    return [], True

                if response.status_code == 200:
                    # Jina retorna em formato estruturado
                    try:
                        data = response.json()
                        resultados = self._parsear_resultados_search(data)
                    except:
                        # Se nao for JSON, parsear como texto
                        resultados = self._parsear_texto_simples(response.text)

                    return resultados[:max_resultados], False
                else:
                    raise Exception(f"Jina search error: {response.status_code}")

        except Exception as e:
            print(f"Erro em JinaClient.search_web: {e}")
            return [], False

    async def read_url(self, url: str) -> Tuple[str, bool]:
        """
        Extrai conteudo de uma URL usando Jina com graceful degradation

        Args:
            url: URL para extrair

        Returns:
            Tupla (conteudo, usando_fallback)
        """
        # Se ja em degradacao, usar fallback
        if self.degradacao_ativa:
            print(f"[JINA DEGRADED] {self.motivo_degradacao} - Usando fallback para read_url")
            return "", True

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/readability",
                    params={"url": url},
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )

                # Verificar erros de degradacao
                motivo = self._detectar_degradacao(response.status_code)
                if motivo:
                    self.degradacao_ativa = True
                    self.motivo_degradacao = motivo
                    self.timestamp_degradacao = datetime.now()
                    print(f"[JINA DEGRADATION ACTIVATED] {motivo}")
                    return "", True

                if response.status_code == 200:
                    try:
                        data = response.json()
                        conteudo = data.get("data", {}).get("content", "")
                        return conteudo, False
                    except:
                        return response.text, False
                else:
                    raise Exception(f"Jina readability error: {response.status_code}")

        except Exception as e:
            print(f"Erro em JinaClient.read_url: {e}")
            return "", False

    def get_status(self) -> Dict[str, Any]:
        """
        Retorna status atual do cliente Jina

        Returns:
            Dicionário com informações de status
        """
        return {
            "degradacao_ativa": self.degradacao_ativa,
            "motivo": self.motivo_degradacao,
            "timestamp_degradacao": self.timestamp_degradacao.isoformat() if self.timestamp_degradacao else None,
            "status": "DEGRADED" if self.degradacao_ativa else "OK"
        }

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
