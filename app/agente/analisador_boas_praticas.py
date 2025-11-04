# -*- coding: utf-8 -*-
"""
Agente para análise e extração de boas práticas a partir de fontes
"""
import json
from typing import List, Dict, Any, Optional
from app.llm.client import LLMClient
from app.utils.logger import logger


class AnalisadorBoasPraticas:
    """
    Agente especializado em identificar boas práticas a partir de
    resultados de pesquisa e documentos da base de conhecimento
    """

    def __init__(self):
        self.llm_client = LLMClient()

    async def analisar_boas_praticas(
        self,
        falha: Dict[str, Any],
        fontes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analisa fontes e extrai boas práticas relacionadas à falha

        Args:
            falha: Dicionário com dados da falha (id, titulo, descricao, pilar)
            fontes: Lista de fontes (resultados de pesquisa e documentos)

        Returns:
            Lista de boas práticas identificadas
        """
        if not fontes:
            return []

        try:
            # Construir contexto das fontes
            contexto_fontes = self._construir_contexto_fontes(fontes)

            # Construir prompt
            prompt = self._construir_prompt(falha, contexto_fontes)

            # Chamar LLM
            resposta = await self.llm_client.gerar(
                prompt=prompt,
                temperatura=0.3,
                max_tokens=3000
            )

            # Parsear resposta JSON
            praticas = self._parsear_resposta(resposta)

            logger.info(f"Identificadas {len(praticas)} boas práticas para falha {falha['id']}")
            return praticas

        except Exception as e:
            logger.error(f"Erro ao analisar boas práticas: {str(e)}")
            return []

    def _construir_contexto_fontes(self, fontes: List[Dict[str, Any]]) -> str:
        """Constrói texto formatado das fontes para o LLM"""
        contexto_parts = []

        for idx, fonte in enumerate(fontes[:15], 1):  # Limitar a 15 fontes
            fonte_tipo = fonte.get('fonte_tipo', 'documento')
            fonte_titulo = fonte.get('fonte_titulo', fonte.get('titulo', 'Sem título'))
            fonte_conteudo = fonte.get('fonte_conteudo', fonte.get('content', ''))[:800]  # Limitar tamanho

            # Detectar se é do Sebrae
            is_sebrae = self._detectar_sebrae(fonte)
            sebrae_flag = " [SEBRAE]" if is_sebrae else ""

            contexto_parts.append(
                f"[FONTE {idx}]{sebrae_flag}\n"
                f"Tipo: {fonte_tipo}\n"
                f"Título: {fonte_titulo}\n"
                f"Conteúdo:\n{fonte_conteudo}\n"
            )

        return "\n---\n".join(contexto_parts)

    def _detectar_sebrae(self, fonte: Dict[str, Any]) -> bool:
        """Detecta se a fonte é do Sebrae"""
        texto_busca = " ".join([
            str(fonte.get('fonte_titulo', '')),
            str(fonte.get('titulo', '')),
            str(fonte.get('fonte_url', '')),
            str(fonte.get('url', '')),
            str(fonte.get('fonte_conteudo', ''))[:500]
        ]).lower()

        return 'sebrae' in texto_busca

    def _construir_prompt(self, falha: Dict[str, Any], contexto_fontes: str) -> str:
        """Constrói o prompt para o LLM"""
        return f"""Você é um especialista em políticas públicas e ecossistemas de inovação.

**TAREFA**: Analise as fontes fornecidas e identifique BOAS PRÁTICAS concretas que podem ajudar a resolver ou mitigar a seguinte falha de mercado:

**FALHA DE MERCADO**:
ID: {falha['id']}
Título: {falha['titulo']}
Pilar: {falha['pilar']}
Descrição: {falha.get('descricao', 'N/A')}

**FONTES DISPONÍVEIS**:
{contexto_fontes}

**INSTRUÇÕES**:
1. Identifique práticas, programas, políticas ou soluções concretas mencionadas nas fontes
2. Cada boa prática deve ser ESPECÍFICA e ACIONÁVEL
3. Priorize práticas que têm evidências de sucesso ou resultados positivos
4. Identifique se a prática vem do Sebrae (marcado com [SEBRAE] nas fontes)
5. Se não houver boas práticas relevantes, retorne array vazio

**FORMATO DE SAÍDA** (JSON válido):
```json
[
  {{
    "titulo": "Nome conciso da prática (máx 100 caracteres)",
    "descricao": "Descrição breve da prática e seus resultados (máx 300 caracteres)",
    "is_sebrae": true,
    "fonte": "FONTE 1"
  }}
]
```

**CRITÉRIOS DE QUALIDADE**:
- Prática DEVE ser mencionada explicitamente nas fontes
- Título deve ser claro e objetivo
- Descrição deve explicar O QUE é e QUAL o impacto/resultado
- Evite práticas genéricas ou vagas
- Máximo 5 práticas por falha

Retorne APENAS o JSON, sem texto adicional."""

    def _parsear_resposta(self, resposta: str) -> List[Dict[str, Any]]:
        """Parseia a resposta do LLM em formato JSON"""
        try:
            # Tentar extrair JSON da resposta
            resposta = resposta.strip()

            # Remover markdown code blocks se existirem
            if resposta.startswith("```"):
                resposta = resposta.split("```")[1]
                if resposta.startswith("json"):
                    resposta = resposta[4:]
                resposta = resposta.strip()

            # Parsear JSON
            praticas = json.loads(resposta)

            # Validar estrutura
            if not isinstance(praticas, list):
                logger.warning("Resposta não é uma lista")
                return []

            # Validar cada prática
            praticas_validas = []
            for p in praticas:
                if isinstance(p, dict) and 'titulo' in p:
                    praticas_validas.append({
                        'titulo': p.get('titulo', ''),
                        'descricao': p.get('descricao'),
                        'is_sebrae': p.get('is_sebrae', False),
                        'fonte': p.get('fonte')
                    })

            return praticas_validas[:5]  # Máximo 5 práticas

        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON: {str(e)}")
            logger.debug(f"Resposta recebida: {resposta[:500]}")
            return []
        except Exception as e:
            logger.error(f"Erro inesperado ao parsear resposta: {str(e)}")
            return []
