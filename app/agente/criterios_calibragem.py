# -*- coding: utf-8 -*-
"""
Sistema de Calibragem para Análise de Priorização
Garante notas comparáveis e sem viés entre todas as falhas
"""

CRITERIOS_IMPACTO = """
# CRITÉRIOS DE IMPACTO (0-10)

Avalie o impacto potencial de resolver a falha no ecossistema de inovação brasileiro usando critérios objetivos:

## DIMENSÃO 1: ABRANGÊNCIA (0-3 pontos)
- **0 pontos**: Impacta apenas um nicho específico (< 1% do ecossistema)
- **1 ponto**: Impacta um setor específico (1-5% do ecossistema)
- **2 pontos**: Impacta múltiplos setores (5-20% do ecossistema)
- **3 pontos**: Impacta todo o ecossistema (> 20% ou sistêmico)

**Indicadores objetivos:**
- Número de empresas/startups afetadas
- Número de setores impactados
- Distribuição geográfica (local, regional, nacional)

## DIMENSÃO 2: MAGNITUDE DO PROBLEMA (0-3 pontos)
- **0 pontos**: Problema marginal sem evidências quantitativas
- **1 ponto**: Problema documentado com algumas evidências (< 5 fontes)
- **2 pontos**: Problema bem documentado com evidências sólidas (5-15 fontes)
- **3 pontos**: Problema crítico amplamente documentado (> 15 fontes ou dados oficiais)

**Indicadores objetivos:**
- Número de resultados de pesquisa encontrados
- Citações em documentos oficiais (MEC, MCTI, etc.)
- Estudos acadêmicos ou relatórios técnicos
- Menções em políticas públicas existentes

## DIMENSÃO 3: MATURIDADE DE SOLUÇÕES (0-2 pontos)
- **0 pontos**: Existem programas consolidados resolvendo o problema
- **1 ponto**: Existem programas em implementação parcial
- **2 pontos**: Não existem programas efetivos (gap crítico)

**Indicadores objetivos:**
- Número de programas/iniciativas identificados na base de conhecimento
- Orçamento investido (se > R$ 100 milhões = soluções maduras)
- Legislação existente (Lei federal = programa consolidado)

## DIMENSÃO 4: EFEITO MULTIPLICADOR (0-2 pontos)
- **0 pontos**: Impacto isolado em um pilar
- **1 ponto**: Impacta 2 pilares do ecossistema
- **2 pontos**: Impacta 3+ pilares (transversal)

**Indicadores objetivos:**
- Impacto direto em: Talento, Densidade, Cultura, Capital, Regulação, Mercado, Impacto

**SCORE FINAL DE IMPACTO = Soma das 4 dimensões (máximo 10 pontos)**
"""

CRITERIOS_ESFORCO = """
# CRITÉRIOS DE ESFORÇO (0-10)

Avalie o esforço necessário para implementar soluções usando critérios objetivos:

## DIMENSÃO 1: COMPLEXIDADE DE STAKEHOLDERS (0-3 pontos)
- **0 pontos**: Solução implementável por 1 ator (ex: iniciativa privada)
- **1 ponto**: Requer coordenação de 2-3 atores (ex: empresa + universidade)
- **2 pontos**: Requer coordenação de 4-6 atores (múltiplas esferas)
- **3 pontos**: Requer coordenação de 7+ atores ou mudança constitucional

**Indicadores objetivos:**
- Número de ministérios/órgãos envolvidos
- Necessidade de articulação federativa (União, Estados, Municípios)
- Envolvimento de setor privado, academia, sociedade civil

## DIMENSÃO 2: INVESTIMENTO NECESSÁRIO (0-2 pontos)
- **0 pontos**: Baixo investimento (< R$ 10 milhões)
- **1 ponto**: Investimento médio (R$ 10-100 milhões)
- **2 pontos**: Alto investimento (> R$ 100 milhões)

**Indicadores objetivos:**
- Benchmarks de programas similares existentes
- Orçamento de iniciativas mencionadas nos resultados
- Necessidade de infraestrutura física (laboratórios, equipamentos)

## DIMENSÃO 3: TEMPO DE IMPLEMENTAÇÃO (0-2 pontos)
- **0 pontos**: Implementação rápida (< 1 ano)
- **1 ponto**: Implementação média (1-3 anos)
- **2 pontos**: Implementação longa (> 3 anos)

**Indicadores objetivos:**
- Necessidade de mudança legislativa (+ 2 anos)
- Necessidade de formação de pessoas (educação = + 5 anos)
- Necessidade de mudança cultural (+ 10 anos)
- Complexidade de procurement e contratações

## DIMENSÃO 4: MUDANÇAS ESTRUTURAIS (0-3 pontos)
- **0 pontos**: Expansão de programas existentes
- **1 ponto**: Modificação de programas existentes
- **2 pontos**: Criação de novos programas/estruturas
- **3 pontos**: Mudança sistêmica (legislação federal, reforma curricular nacional)

**Indicadores objetivos:**
- Necessidade de nova legislação (Lei, MP, Decreto)
- Mudanças em currículos nacionais
- Criação de novas autarquias/órgãos
- Reformas em estruturas consolidadas

**SCORE FINAL DE ESFORÇO = Soma das 4 dimensões (máximo 10 pontos)**
"""

EXEMPLOS_CALIBRACAO = """
# EXEMPLOS DE CALIBRAÇÃO

## EXEMPLO 1: Deficiências Estruturais na Educação STEM
**Contexto:**
- 1.016 resultados de pesquisa
- 11 programas nacionais identificados
- Dados PISA: apenas 18,2% em nível básico
- Investimento: R$ 100 milhões (Programa Mais Ciência)
- Legislação federal: Lei 14.533/2023

**IMPACTO = 9**
- Abrangência: 3 (todo sistema educacional)
- Magnitude: 3 (> 1.000 fontes, dados PISA oficiais)
- Maturidade: 1 (programas existem mas são insuficientes)
- Multiplicador: 2 (impacta Talento, Cultura, Densidade)

**ESFORÇO = 8**
- Stakeholders: 3 (MEC, MCTI, Estados, Municípios, 7+ atores)
- Investimento: 2 (> R$ 100 milhões necessários)
- Tempo: 2 (educação = resultados em 5-10 anos)
- Mudanças: 1 (programas existem, precisam expansão)

## EXEMPLO 2: Burocracia em Registro de Propriedade Intelectual
**Contexto:**
- 250 resultados de pesquisa
- 3 programas identificados
- Tempo médio: 5 anos para patente
- OCDE: 2 anos

**IMPACTO = 6**
- Abrangência: 2 (impacta startups tech e pesquisa)
- Magnitude: 2 (bem documentado, 250 fontes)
- Maturidade: 1 (INPI existe mas é lento)
- Multiplicador: 1 (Talento + Capital)

**ESFORÇO = 5**
- Stakeholders: 1 (principalmente INPI/MCTIC)
- Investimento: 1 (modernização de sistemas)
- Tempo: 1 (2-3 anos para digitalizar processos)
- Mudanças: 2 (requer mudança de processos do INPI)

## EXEMPLO 3: Falta de Mentoria para Empreendedores Iniciantes
**Contexto:**
- 120 resultados de pesquisa
- Sebrae tem programas de mentoria
- Problema: baixa cobertura geográfica

**IMPACTO = 5**
- Abrangência: 1 (startups early-stage, ~5% do ecossistema)
- Magnitude: 1 (< 200 fontes)
- Maturidade: 1 (Sebrae já tem programas)
- Multiplicador: 2 (Talento + Cultura + Densidade)

**ESFORÇO = 3**
- Stakeholders: 0 (Sebrae pode executar sozinho)
- Investimento: 0 (< R$ 10 milhões)
- Tempo: 0 (< 1 ano para escalar)
- Mudanças: 3 (requer nova estrutura de rede de mentores)
"""

PROMPT_TEMPLATE_CALIBRADO = """
Você é um especialista em políticas públicas e ecossistema de inovação brasileiro.

IMPORTANTE: Use os critérios objetivos abaixo para garantir análises comparáveis e sem viés.

{criterios_impacto}

{criterios_esforco}

{exemplos}

---

FALHA PARA ANÁLISE:

{contexto}

---

INSTRUÇÕES:
1. Analise cada dimensão objetivamente usando os indicadores fornecidos
2. Some os pontos de cada dimensão para obter o score final
3. Cite as fontes usando [FONTE-X] na justificativa
4. Seja rigoroso e comparativo: use os exemplos como referência de calibragem

Responda EXATAMENTE no seguinte formato JSON:
{{
    "impacto": {{
        "abrangencia": <0-3>,
        "magnitude": <0-3>,
        "maturidade": <0-2>,
        "multiplicador": <0-2>,
        "total": <soma, 0-10>
    }},
    "esforco": {{
        "stakeholders": <0-3>,
        "investimento": <0-2>,
        "tempo": <0-2>,
        "estrutural": <0-3>,
        "total": <soma, 0-10>
    }},
    "justificativa": "<explicação detalhada com citações [FONTE-X] para cada dimensão>",
    "fontes_utilizadas": [<lista dos números de fontes citadas>]
}}

IMPORTANTE: Responda APENAS com o JSON, sem texto adicional.
"""

def get_prompt_calibrado(contexto: str) -> str:
    """Retorna o prompt completo com critérios de calibragem"""
    return PROMPT_TEMPLATE_CALIBRADO.format(
        criterios_impacto=CRITERIOS_IMPACTO,
        criterios_esforco=CRITERIOS_ESFORCO,
        exemplos=EXEMPLOS_CALIBRACAO,
        contexto=contexto
    )
