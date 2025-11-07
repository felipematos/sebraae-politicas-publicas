# -*- coding: utf-8 -*-
"""
Cliente para Perplexity AI API
"""
import httpx
from typing import List, Dict, Any
import asyncio

# Mapeamento de códigos de idioma para nomes em inglês (para melhor compreensão)
IDIOMA_NOMES_EN = {
    "pt": "Portuguese",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "ar": "Arabic",
    "ja": "Japanese",
    "ko": "Korean",
    "he": "Hebrew",
}


class PerplexityClient:
    """Cliente para pesquisas via Perplexity AI"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai"
        self.model = "sonar"  # Updated from deprecated pplx-7b-online
        self.timeout = httpx.Timeout(60.0)

    def _get_idioma_nome(self, codigo_idioma: str) -> str:
        """Converte código de idioma para nome em inglês."""
        return IDIOMA_NOMES_EN.get(codigo_idioma, codigo_idioma).upper()

    async def pesquisar(
        self,
        query: str,
        idioma: str = "en",
        max_resultados: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Realiza pesquisa via Perplexity

        Args:
            query: Termos de busca (esperado em outro idioma ou sem tradução)
            idioma: Código do idioma da pesquisa (pt, en, es, etc)
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

                idioma_nome = self._get_idioma_nome(idioma)

                # Prompt mais rigoroso para garantir resposta no idioma correto
                prompt = f"""Search for: {query}

IMPORTANT: Your response MUST be ENTIRELY in {idioma_nome}.
- Do NOT use any other language
- All titles, descriptions, and text must be in {idioma_nome}
- List 5 sources with title and URL
- Format: Title - URL - Brief description"""

                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
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

        Esperado formato com URLs e titulos entre pipes: | Título | URL | Descrição |
        """
        from app.utils.url_validator import eh_url_valida

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

                # Validar URL antes de adicionar
                if url and eh_url_valida(url):
                    # Extrair título entre pipes se disponível
                    titulo_final = titulo_temp or "Resultado Perplexity"
                    descricao_final = linha

                    # Se a linha contém pipes, extrair o título de entre eles
                    if "|" in linha:
                        partes = [p.strip() for p in linha.split("|")]
                        # Filtrar partes vazias
                        partes = [p for p in partes if p and "http" not in p.lower()]
                        if partes:
                            # Primeira parte não-vazia é o título
                            titulo_final = partes[0]
                            # Restante é a descrição (se houver)
                            if len(partes) > 1:
                                descricao_final = " ".join(partes[1:])
                            else:
                                descricao_final = titulo_final

                    resultados.append({
                        "titulo": titulo_final,
                        "url": url,
                        "descricao": descricao_final
                    })
                    titulo_temp = ""
            else:
                titulo_temp = linha[:100]

        # NOTA: Se não encontrou nenhum resultado válido, retornar lista vazia
        # Pois não devemos gerar URLs de placeholder/mecanismo de pesquisa
        # O processador saberá lidar com resultados vazios

        return resultados
