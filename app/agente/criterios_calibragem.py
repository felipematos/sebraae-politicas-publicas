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

⚠️ **IMPORTANTE: Seja RIGOROSO e CRITERIOSO na avaliação de esforço. A maioria das soluções deve ficar entre 3-6 pontos. Apenas mudanças VERDADEIRAMENTE sistêmicas e complexas merecem 8-10 pontos.**

Avalie o esforço necessário para implementar soluções usando critérios objetivos e estritos:

## DIMENSÃO 1: COMPLEXIDADE DE STAKEHOLDERS (0-3.5 pontos) - SEJA CONSERVADOR
- **0 pontos**: Solução implementável por 1 ator isoladamente (ex: Sebrae, iniciativa privada, ONG)
- **1 ponto**: Requer coordenação de 2 atores (ex: Sebrae + empresas privadas)
- **2 pontos**: Requer coordenação de 3-4 atores de esferas similares (ex: BNDES + Finep + CNPq)
- **2.5 pontos**: Requer coordenação de 4-6 atores de múltiplas esferas (ex: ministério + estados + setor privado)
- **3 pontos**: Requer coordenação de 7-10 atores incluindo múltiplas esferas governamentais
- **3.5 pontos**: Requer coordenação de 10+ atores OU mudança constitucional OU articulação federativa completa (União + todos Estados + Municípios)

**ATENÇÃO:** Dar nota 3+ exige EVIDÊNCIAS de que a solução realmente precisa de articulação federativa ou múltiplos ministérios. Soluções que podem começar em escala piloto devem ter nota reduzida.

**Perguntas críticas:**
- A solução REALMENTE precisa de todos esses atores desde o início ou pode começar menor?
- Há exemplos de soluções similares implementadas com menos atores?
- É possível implementação gradual/faseada reduzindo coordenação inicial?

## DIMENSÃO 2: INVESTIMENTO NECESSÁRIO (0-2.5 pontos) - EXIJA BENCHMARKS
- **0 pontos**: Investimento mínimo (< R$ 5 milhões - ex: consultorias, capacitações, plataformas digitais)
- **0.5 pontos**: Investimento baixo (R$ 5-10 milhões - ex: programas-piloto regionais)
- **1 ponto**: Investimento médio-baixo (R$ 10-50 milhões - ex: programas estaduais, modernização de sistemas)
- **1.5 pontos**: Investimento médio (R$ 50-100 milhões - ex: programas nacionais de capacitação)
- **2 pontos**: Investimento alto (R$ 100-500 milhões - ex: infraestrutura tecnológica nacional)
- **2.5 pontos**: Investimento muito alto (> R$ 500 milhões - ex: reformas estruturais, infraestrutura física nacional)

**ATENÇÃO:** Nota 2+ só para soluções com necessidade COMPROVADA de investimentos massivos. Use benchmarks de programas reais.

**Perguntas críticas:**
- Existem DADOS de orçamentos de programas similares para comparação?
- A solução pode ser implementada em fases menores com menos investimento inicial?
- Há possibilidade de cofinanciamento ou parcerias público-privadas?

## DIMENSÃO 3: TEMPO DE IMPLEMENTAÇÃO (0-2.5 pontos) - CONSIDERE FASES
- **0 pontos**: Implementação imediata (< 6 meses - ex: regulamentações por decreto, programas-piloto)
- **0.5 pontos**: Implementação rápida (6 meses - 1 ano - ex: criação de programas novos sem legislação)
- **1 ponto**: Implementação média-rápida (1-2 anos - ex: programas com necessidade de estruturação)
- **1.5 pontos**: Implementação média (2-3 anos - ex: mudanças legislativas simples, sistemas de TI complexos)
- **2 pontos**: Implementação longa (3-5 anos - ex: reformas curriculares, mudanças culturais graduais)
- **2.5 pontos**: Implementação muito longa (> 5 anos - ex: mudanças educacionais estruturais, transformações culturais profundas)

**ATENÇÃO:** Nota 2+ só para soluções que REALMENTE dependem de ciclos longos (educação, mudança cultural). Soluções que podem mostrar resultados parciais antes devem ter nota reduzida.

**Perguntas críticas:**
- Qual é o prazo MÍNIMO para primeiros resultados visíveis (não implementação completa)?
- A solução pode ter implementação faseada com ganhos incrementais?
- Existem atalhos regulatórios (MPs, decretos) que reduzem tempo legislativo?

## DIMENSÃO 4: MUDANÇAS ESTRUTURAIS (0-2.5 pontos) - AVALIE PROFUNDIDADE REAL
- **0 pontos**: Expansão/escalonamento de programas já existentes (ex: ampliar cobertura de programa do Sebrae)
- **0.5 pontos**: Modificação moderada de programas existentes (ex: ajustar critérios de financiamento)
- **1 ponto**: Modificação substancial de programas existentes (ex: reestruturar modelo de operação)
- **1.5 pontos**: Criação de novos programas/estruturas sem mudança legal (ex: novo departamento, nova linha de financiamento)
- **2 pontos**: Criação de programas que exigem decreto ou resolução normativa
- **2.5 pontos**: Mudança sistêmica que exige legislação federal (Lei, MP) OU reforma curricular nacional OU criação de autarquia/órgão federal

**ATENÇÃO:** Nota 2+ só para mudanças que REALMENTE exigem lei federal ou reformas estruturais. Decretos, portarias e resoluções contam como nota máxima 2.

**Perguntas críticas:**
- A solução REALMENTE precisa de lei federal ou pode ser feita por decreto/portaria?
- Já existe arcabouço legal que permite implementação sem mudança estrutural?
- A mudança afeta TODA estrutura existente ou apenas cria algo novo em paralelo?

---

**SCORE FINAL DE ESFORÇO = Soma das 4 dimensões (máximo 11 pontos, normalizado para escala 0-10)**

**DISTRIBUIÇÃO ESPERADA (para 50 falhas):**
- 0-3 pontos: ~20% das falhas (soluções simples, escalonamento de programas existentes)
- 4-6 pontos: ~50% das falhas (soluções de complexidade moderada)
- 7-8 pontos: ~25% das falhas (soluções complexas mas viáveis)
- 9-10 pontos: ~5% das falhas (apenas mudanças VERDADEIRAMENTE sistêmicas)

**EXEMPLOS DE ESFORÇO 9-10:** Reforma tributária completa, Reforma educacional nacional (BNCC), Criação de ministério
**EXEMPLOS DE ESFORÇO 4-6:** Modernização do INPI, Criação de linhas de crédito específicas, Programas nacionais de capacitação
**EXEMPLOS DE ESFORÇO 0-3:** Expansão geográfica de programas existentes, Consultorias especializadas, Plataformas digitais
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
- **USE VALORES DECIMAIS** com até 2 casas decimais para maior precisão (ex: 5.75, 3.50, 7.25)

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
3. **Some os pontos** de cada dimensão para obter o score final (use valores decimais com até 2 casas)
4. **Cite as fontes** usando [FONTE-X] para CADA afirmação factual na justificativa
5. **Seja comparativo:** Use os exemplos como referência - se a falha não é tão crítica quanto "Educação STEM", não pode ter nota similar
6. **Questione suas próprias suposições:** Antes de dar nota alta, pergunte "Tenho DADOS que comprovam isso?"
7. **Precisão decimal:** Use incrementos de 0.25 ou 0.5 entre categorias quando apropriado (ex: entre 1 e 1.5, use 1.25 se houver evidência parcial)

⚠️ **CHECKLIST ANTES DE FINALIZAR:**
- [ ] Usei APENAS dados quantitativos verificáveis, não impressões qualitativas?
- [ ] Citei fontes específicas [FONTE-X] para cada claim?
- [ ] A nota de impacto está entre 3-6 para problemas "normais" (não sistêmicos)?
- [ ] Dei nota 8+ APENAS se houver dados oficiais (IBGE, OCDE, etc.)?
- [ ] Considerei programas existentes que já abordam parcialmente o problema?

Responda EXATAMENTE no seguinte formato JSON:
{{
    "impacto": {{
        "abrangencia": <0-3, com 2 casas decimais, ex: 1.75>,
        "magnitude": <0-3, com 2 casas decimais, ex: 2.25>,
        "maturidade": <0-2, com 2 casas decimais, ex: 1.50>,
        "multiplicador": <0-2, com 2 casas decimais, ex: 1.00>,
        "total": <soma das dimensões, 0-10.00, com 2 casas decimais>
    }},
    "esforco": {{
        "stakeholders": <0-3.5, com 2 casas decimais, ex: 2.75>,
        "investimento": <0-2.5, com 2 casas decimais, ex: 1.50>,
        "tempo": <0-2.5, com 2 casas decimais, ex: 0.75>,
        "estrutural": <0-2.5, com 2 casas decimais, ex: 1.25>,
        "total": <soma das dimensões normalizada para 0-10.00, com 2 casas decimais>
    }},
    "justificativa": "<explicação detalhada com citações [FONTE-X] para CADA dimensão, sendo crítico e baseado em dados>",
    "fontes_utilizadas": [<lista dos números de fontes citadas>]
}}

**IMPORTANTE SOBRE ESFORÇO:**
- O score de esforço é calculado somando as 4 dimensões (máximo 11 pontos)
- O total deve ser normalizado para escala 0-10.00: `total_normalizado = (soma_dimensoes / 11.0) * 10.0`
- Exemplo: se stakeholders=2.5, investimento=1.5, tempo=1.0, estrutural=2.0, então soma=7.0
- Total normalizado = (7.0 / 11.0) * 10.0 = 6.36

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
