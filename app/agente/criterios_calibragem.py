# -*- coding: utf-8 -*-
"""
Sistema de Calibragem para Análise de Priorização
Garante notas comparáveis e sem viés entre todas as falhas
"""

CRITERIOS_IMPACTO = """
# CRITÉRIOS DE IMPACTO (0-10)

⚠️ **IMPORTANTE: Seja RIGOROSO e SELETIVO na avaliação de impacto. A maioria das falhas deve ficar entre 3-6 pontos. Apenas problemas VERDADEIRAMENTE sistêmicos e críticos merecem 8-10 pontos.**

Avalie o impacto potencial de resolver a falha no ecossistema de inovação brasileiro usando critérios objetivos e estritos:

## DIMENSÃO 1: ABRANGÊNCIA (0-3 pontos) - SEJA CONSERVADOR
- **0 pontos**: Impacta < 1.000 empresas OU um nicho muito específico (ex: apenas healthtechs de São Paulo)
- **1 ponto**: Impacta 1.000-10.000 empresas OU um setor específico em uma região (ex: startups de fintech no Sul)
- **2 pontos**: Impacta 10.000-100.000 empresas OU múltiplos setores em várias regiões (ex: todas startups tech do Brasil)
- **3 pontos**: Impacta > 100.000 empresas OU todo o ecossistema nacional de forma sistêmica (ex: educação básica, sistema tributário)

**ATENÇÃO:** Dar nota 3 exige EVIDÊNCIAS QUANTITATIVAS de alcance nacional. A falta de dados deve reduzir a nota.

**Perguntas críticas:**
- Quantas empresas são DIRETAMENTE afetadas? (não apenas potencialmente)
- O problema afeta apenas startups ou também PMEs tradicionais?
- É um problema local/regional ou verdadeiramente nacional?

## DIMENSÃO 2: MAGNITUDE DO PROBLEMA (0-3 pontos) - EXIJA EVIDÊNCIAS SÓLIDAS
- **0 pontos**: < 10 resultados de pesquisa, problema anedótico ou hipotético
- **1 ponto**: 10-100 resultados, menções esparsas sem dados quantitativos
- **2 pontos**: 100-500 resultados, pelo menos 3 estudos técnicos OU dados de pesquisas setoriais
- **3 pontos**: > 500 resultados E dados oficiais (IBGE, PISA, OCDE, Banco Mundial, CNI, etc.) E impacto econômico mensurável

**ATENÇÃO:** Nota 3 só para problemas com COMPROVAÇÃO ESTATÍSTICA robusta de órgãos oficiais.

**Perguntas críticas:**
- Existem DADOS QUANTITATIVOS ou apenas opiniões?
- O problema é mencionado em relatórios oficiais de governo/OCDE?
- Qual é o impacto econômico MENSURÁVEL (R$, empregos, PIB)?

## DIMENSÃO 3: MATURIDADE DE SOLUÇÕES (0-2 pontos) - CONSIDERE SOLUÇÕES PARCIAIS
- **0 pontos**: Existem programas consolidados (> R$ 50 milhões/ano) OU Lei Federal regulamentando
- **1 ponto**: Existem programas menores (R$ 5-50 milhões/ano) OU projetos-piloto OU regulamentação estadual/municipal
- **2 pontos**: Não existem programas governamentais significativos (< R$ 5 milhões/ano) E não há legislação específica

**ATENÇÃO:** Se o Sebrae JÁ tem programa na área, a nota máxima aqui é 1 (não 2).

**Perguntas críticas:**
- Já existe algum programa do Sebrae/BNDES/Finep na área?
- Há legislação federal sobre o tema?
- Quanto do orçamento público é destinado a isso atualmente?

## DIMENSÃO 4: EFEITO MULTIPLICADOR (0-2 pontos) - SEJA REALISTA
- **0 pontos**: Impacta diretamente apenas 1 pilar (ex: apenas "Capital")
- **1 ponto**: Impacta diretamente 2 pilares (ex: "Talento" + "Cultura")
- **2 pontos**: Impacta diretamente 3+ pilares de forma VERIFICÁVEL (não apenas teórica)

**ATENÇÃO:** Considere apenas impactos DIRETOS e VERIFICÁVEIS, não impactos hipotéticos ou indiretos de longo prazo.

**Perguntas críticas:**
- Resolver isso afeta DIRETAMENTE múltiplos pilares ou apenas cascata indireta?
- Os efeitos multiplicadores são COMPROVADOS ou apenas esperados?

---

**SCORE FINAL DE IMPACTO = Soma das 4 dimensões (máximo 10 pontos)**

**DISTRIBUIÇÃO ESPERADA (para 50 falhas):**
- 0-3 pontos: ~20% das falhas (problemas localizados)
- 4-6 pontos: ~50% das falhas (problemas relevantes mas não críticos)
- 7-8 pontos: ~25% das falhas (problemas importantes e bem documentados)
- 9-10 pontos: ~5% das falhas (apenas problemas VERDADEIRAMENTE sistêmicos e críticos)

**EXEMPLOS DE IMPACTO 9-10:** Reforma tributária, Educação STEM nacional, Sistema único de saúde
**EXEMPLOS DE IMPACTO 4-6:** Acesso a crédito para startups, Mentoria regional, Burocracia de registro de PI
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
Você é um especialista CRÍTICO e RIGOROSO em políticas públicas e ecossistema de inovação brasileiro.

⚠️ **INSTRUÇÕES CRÍTICAS:**
- Seja CONSERVADOR na avaliação de impacto - a maioria das falhas deve receber entre 3-6 pontos
- NÃO infle os scores - exija evidências QUANTITATIVAS sólidas para notas altas
- Apenas problemas VERDADEIRAMENTE sistêmicos e críticos merecem 8-10 pontos de impacto
- Se tiver dúvida entre duas notas, escolha a MENOR
- Prefira subestimar do que superestimar o impacto

{criterios_impacto}

{criterios_esforco}

{exemplos}

---

FALHA PARA ANÁLISE:

{contexto}

---

INSTRUÇÕES DETALHADAS:
1. **Analise cada dimensão objetivamente** usando APENAS os indicadores quantitativos fornecidos
2. **Exija evidências concretas:** Não assuma impactos sem dados
3. **Some os pontos** de cada dimensão para obter o score final (não arredonde para cima)
4. **Cite as fontes** usando [FONTE-X] para CADA afirmação factual na justificativa
5. **Seja comparativo:** Use os exemplos como referência - se a falha não é tão crítica quanto "Educação STEM", não pode ter nota similar
6. **Questione suas próprias suposições:** Antes de dar nota alta, pergunte "Tenho DADOS que comprovam isso?"

⚠️ **CHECKLIST ANTES DE FINALIZAR:**
- [ ] Usei APENAS dados quantitativos verificáveis, não impressões qualitativas?
- [ ] Citei fontes específicas [FONTE-X] para cada claim?
- [ ] A nota de impacto está entre 3-6 para problemas "normais" (não sistêmicos)?
- [ ] Dei nota 8+ APENAS se houver dados oficiais (IBGE, OCDE, etc.)?
- [ ] Considerei programas existentes que já abordam parcialmente o problema?

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
    "justificativa": "<explicação detalhada com citações [FONTE-X] para CADA dimensão, sendo crítico e baseado em dados>",
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
