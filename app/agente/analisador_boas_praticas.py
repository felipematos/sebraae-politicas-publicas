# -*- coding: utf-8 -*-
"""
Agente para análise e extração de boas práticas a partir de fontes
"""
import json
from typing import List, Dict, Any, Optional
from app.llm.openai_client import OpenAIClient
from app.integracao.openrouter_api import OpenRouterClient
from app.utils.logger import logger


class AnalisadorBoasPraticas:
    """
    Agente especializado em identificar boas práticas a partir de
    resultados de pesquisa e documentos da base de conhecimento
    """

    def __init__(self):
        self.llm_client = OpenAIClient()

    async def analisar_boas_praticas(
        self,
        falha: Dict[str, Any],
        fontes: List[Dict[str, Any]],
        modelo: Optional[str] = None,
        usar_openrouter: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Analisa fontes e extrai boas práticas relacionadas à falha

        Args:
            falha: Dicionário com dados da falha (id, titulo, descricao, pilar)
            fontes: Lista de fontes (resultados de pesquisa e documentos)
            modelo: Modelo LLM a usar (ex: "google/gemini-2.0-flash-exp:free")
            usar_openrouter: Se True, usa OpenRouter; se False, usa OpenAI

        Returns:
            Lista de boas práticas identificadas (cada uma com confidence_score 0-100)
        """
        if not fontes:
            return []

        try:
            # Construir contexto das fontes
            contexto_fontes = self._construir_contexto_fontes(fontes)

            # Construir prompt
            prompt = self._construir_prompt(falha, contexto_fontes)

            # Chamar LLM
            if usar_openrouter:
                # Usar modelo recomendado ou default
                modelo_usar = modelo or "google/gemini-2.0-flash-exp:free"

                async with OpenRouterClient() as client:
                    resposta = await client.chamar_modelo(
                        modelo=modelo_usar,
                        prompt=prompt,
                        temperature=0.3,
                        max_tokens=4000
                    )
            else:
                # Fallback para OpenAI (GPT-4o-mini)
                resposta = await self.llm_client.generate_completion(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=3000,
                    model="gpt-4o-mini"
                )

            # Parsear resposta JSON
            praticas = self._parsear_resposta(resposta)

            logger.info(f"Identificadas {len(praticas)} boas práticas para falha {falha['id']} usando modelo {modelo_usar if usar_openrouter else 'gpt-4o-mini'}")
            return praticas

        except Exception as e:
            logger.error(f"Erro ao analisar boas práticas: {str(e)}")
            return []

    def _construir_contexto_fontes(self, fontes: List[Dict[str, Any]]) -> str:
        """Constrói texto formatado das fontes para o LLM

        IMPORTANTE: Para garantir acurácia multilíngue, prioriza traduções
        para português quando disponíveis.
        """
        contexto_parts = []

        for idx, fonte in enumerate(fontes[:15], 1):  # Limitar a 15 fontes
            fonte_tipo = fonte.get('fonte_tipo', 'documento')

            # Priorizar traduções para português quando disponíveis
            # Isso garante análise consistente independente do idioma original
            fonte_titulo = fonte.get('fonte_titulo')
            if not fonte_titulo:
                # Tentar título traduzido primeiro, depois original
                fonte_titulo = fonte.get('titulo_pt') or fonte.get('titulo', 'Sem título')

            # Usar conteúdo enriquecido se disponível, senão usar original
            fonte_conteudo = fonte.get('conteudo_completo') or fonte.get('fonte_conteudo', fonte.get('content', ''))

            # Se não há conteúdo enriquecido, tentar usar tradução da descrição
            if not fonte_conteudo:
                fonte_conteudo = fonte.get('descricao_pt') or fonte.get('descricao', '')

            # Limitar tamanho total (já vem limitado pelo soft cut, mas garantir)
            fonte_conteudo = fonte_conteudo[:12000] if fonte_conteudo else ''

            # Detectar se é do Sebrae
            is_sebrae = self._detectar_sebrae(fonte)
            sebrae_flag = " [SEBRAE]" if is_sebrae else ""

            # Adicionar flag de idioma se for tradução
            idioma = fonte.get('idioma', 'pt')
            idioma_flag = ""
            if idioma != 'pt' and (fonte.get('titulo_pt') or fonte.get('descricao_pt')):
                idioma_map = {
                    "en": "Inglês", "es": "Espanhol", "fr": "Francês",
                    "de": "Alemão", "it": "Italiano", "ja": "Japonês",
                    "ar": "Árabe", "ko": "Coreano", "he": "Hebraico"
                }
                idioma_nome = idioma_map.get(idioma, idioma.upper())
                idioma_flag = f" [TRADUZIDO DE {idioma_nome}]"

            # Adicionar informação de erro se URL falhou
            url_error = fonte.get('url_error')
            error_info = f"\n⚠️ Erro ao buscar conteúdo: {url_error}" if url_error else ""

            contexto_parts.append(
                f"[FONTE {idx}]{sebrae_flag}{idioma_flag}\n"
                f"Tipo: {fonte_tipo}\n"
                f"Título: {fonte_titulo}\n"
                f"Conteúdo:\n{fonte_conteudo}{error_info}\n"
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
5. Atribua um score de confiança (0-100) para cada prática baseado em:
   - Evidências de implementação real (peso 40%)
   - Métricas/resultados quantificáveis apresentados (peso 30%)
   - Relevância para a falha de mercado específica (peso 20%)
   - Qualidade e credibilidade da fonte (peso 10%)
6. Se não houver boas práticas relevantes, retorne array vazio

**FORMATO DE SAÍDA** (JSON válido):
```json
[
  {{
    "titulo": "Nome conciso da prática (máx 100 caracteres)",
    "descricao": "Descrição breve da prática e seus resultados (máx 300 caracteres)",
    "is_sebrae": true,
    "fonte": "FONTE 1",
    "confidence_score": 85
  }}
]
```

**CRITÉRIOS DE QUALIDADE**:
- Prática DEVE ser mencionada explicitamente nas fontes
- Título deve ser claro e objetivo
- Descrição deve explicar O QUE é e QUAL o impacto/resultado
- Evite práticas genéricas ou vagas
- Máximo 10 práticas por falha
- Score de confiança OBRIGATÓRIO (0-100)

**EXEMPLOS DE SCORES**:
- 90-100: Prática comprovada com métricas claras e casos de sucesso documentados
- 70-89: Prática implementada com resultados positivos relatados, mas sem métricas detalhadas
- 50-69: Prática mencionada com evidências parciais de implementação
- 30-49: Prática citada sem evidências robustas de implementação
- 0-29: Prática teórica ou com implementação duvidosa

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
                    # Validar e normalizar confidence_score
                    confidence_score = p.get('confidence_score', 50)  # Default: 50
                    if isinstance(confidence_score, (int, float)):
                        confidence_score = max(0, min(100, int(confidence_score)))  # Garantir 0-100
                    else:
                        confidence_score = 50  # Fallback se não for número

                    praticas_validas.append({
                        'titulo': p.get('titulo', ''),
                        'descricao': p.get('descricao'),
                        'is_sebrae': p.get('is_sebrae', False),
                        'fonte': p.get('fonte'),
                        'confidence_score': confidence_score
                    })

            return praticas_validas[:10]  # Máximo 10 práticas

        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON: {str(e)}")
            logger.debug(f"Resposta recebida: {resposta[:500]}")
            return []
        except Exception as e:
            logger.error(f"Erro inesperado ao parsear resposta: {str(e)}")
            return []
