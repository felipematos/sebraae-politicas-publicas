# -*- coding: utf-8 -*-
"""
Cliente OpenAI para geração de texto
"""
import os
from typing import Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()


class OpenAIClient:
    """Cliente para gerar completions usando OpenAI"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa cliente OpenAI

        Args:
            api_key: API key da OpenAI (opcional, usa env var se não fornecido)
        """
        # Se api_key não foi fornecida, busca da env var
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")

        self.client = AsyncOpenAI(api_key=api_key)

    async def generate_completion(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Gera completion para um prompt

        Args:
            prompt: Prompt para o modelo
            model: Modelo a usar (default: gpt-4o-mini)
            temperature: Temperatura (0.0 a 1.0)
            max_tokens: Máximo de tokens na resposta (opcional)

        Returns:
            Texto gerado pelo modelo
        """
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"Erro ao gerar completion: {e}")
            raise
