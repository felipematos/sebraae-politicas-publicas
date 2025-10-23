# Detalhes do Cálculo de Confidence Score - Exemplo Prático

## Fórmula Completa

```
confidence_score = 
    (score_relevancia × 0.40) +
    (valor_ocorrencias × 0.30) +
    (confiabilidade_fonte × 0.20) +
    (valor_titulo_match × 0.10)
```

## Exemplo 1: Resultado com Alta Relevância

### Dados de Entrada
- **Resultado**: 
  - titulo: "Políticas de apoio ao empreendedorismo no Brasil"
  - descricao: "O governo brasileiro implementou programas para facilitar o acesso a crédito e mentoria para startups"
  - fonte: "perplexity"
  - url: "https://example.com/artigo"
  
- **Query**: "apoio empreendedorismo crédito startups Brasil"
- **Num Ocorrências**: 2
- **Ferramenta**: perplexity

### Cálculo Passo a Passo

#### 1. Score de Relevância (40%)
```python
# Palavras-chave da query (após remover stop words)
palavras_query = ["apoio", "empreendedorismo", "credito", "startups", "brasil"]

# Extrair texto completo
texto_resultado = "Políticas de apoio ao empreendedorismo no Brasil O governo brasileiro..."

# Contar matches
matches = 5  # todas as 5 palavras aparecem
proporcao = 5/5 = 1.0

# Score base = (matches / total) × 0.7
score_base = 1.0 × 0.7 = 0.7

# Bônus de phrase: a query completa aparece? Não
# Mas todas as palavras aparecem em sequência
bonus = 0.05

# Score de relevância final
score_relevancia = 0.7 + 0.05 = 0.75
```

#### 2. Score de Ocorrências (30%)
```python
num_ocorrencias = 2
valor_ocorrencias = min(1.0, 2/10) = 0.2
```

#### 3. Confiabilidade da Fonte (20%)
```python
fonte = "perplexity"
confiabilidade_fonte = 0.95  # Tabela de fontes confiáveis
```

#### 4. Match no Título (10%)
```python
titulo = "Políticas de apoio ao empreendedorismo no Brasil"

# Palavras-chave encontradas no título
titulo_matches = 3  # "apoio", "empreendedorismo", "Brasil"
valor_titulo = 3/5 = 0.6
```

#### 5. Score Final
```python
score_final = (0.75 × 0.40) + (0.2 × 0.30) + (0.95 × 0.20) + (0.6 × 0.10)
score_final = 0.30 + 0.06 + 0.19 + 0.06
score_final = 0.61

# Clipped entre 0.0 e 1.0
confidence_score = 0.61  ✅ MUITO BOM!
```

---

## Exemplo 2: Resultado com Baixa Relevância (Realista)

### Dados de Entrada
- **Resultado**:
  - titulo: "Tendências de tecnologia em 2025"
  - descricao: "As principais tecnologias a dominar o mercado em 2025 incluem IA, blockchain e computação quântica"
  - fonte: "jina" 
  - url: "https://example.com/tech-trends"
  
- **Query**: "regulação startups financiamento Brasil governo"
- **Num Ocorrências**: 1
- **Ferramenta**: jina

### Cálculo Passo a Passo

#### 1. Score de Relevância (40%)
```python
# Palavras-chave da query
palavras_query = ["regulacao", "startups", "financiamento", "brasil", "governo"]

# Procurar no texto do resultado
# "Tendências de tecnologia em 2025 As principais tecnologias..."
matches = 0  # Nenhuma palavra-chave aparece!

# Score base
score_base = (0/5) × 0.7 = 0.0

# Bônus de phrase
bonus = 0.0  # Query não aparece

# Score de relevância final
score_relevancia = 0.0
```

#### 2. Score de Ocorrências (30%)
```python
num_ocorrencias = 1
valor_ocorrencias = min(1.0, 1/10) = 0.1
```

#### 3. Confiabilidade da Fonte (20%)
```python
fonte = "jina"
confiabilidade_fonte = 0.90  # Tabela de fontes confiáveis
```

#### 4. Match no Título (10%)
```python
titulo = "Tendências de tecnologia em 2025"

# Procurar palavras-chave
titulo_matches = 0  # Nenhuma palavra-chave no título
valor_titulo = 0.0
```

#### 5. Score Final
```python
score_final = (0.0 × 0.40) + (0.1 × 0.30) + (0.90 × 0.20) + (0.0 × 0.10)
score_final = 0.0 + 0.03 + 0.18 + 0.0
score_final = 0.21

# Clipped entre 0.0 e 1.0
confidence_score = 0.21  ❌ BAIXO
```

### Por Que Está Baixo?

1. **Relevância = 0%**: Nenhuma palavra-chave da query aparece (peso 40%)
2. **Ocorrências = 1**: Apareceu apenas uma vez (peso 30%, valor = 0.1)
3. **Fonte = 0.90**: Mesmo com boa fonte, não é suficiente (peso 20%)
4. **Título = 0%**: Nenhuma palavra-chave no título (peso 10%)

**Conclusão**: Score baixo é principalmente por irrelevância (0 relevância + 0 título match).

---

## Análise dos Dados Reais

### Por que a média é 0.193?

Analisando a estrutura:

```python
# Assumindo distribuição típica dos dados observados:

# 1. Relevância (40%) - PROBLEMA PRINCIPAL
#    - Muitos resultados não combinam bem com queries genéricas
#    - Média observada: ~0.30 de relevância
#    Contribuição: 0.30 × 0.40 = 0.12

# 2. Ocorrências (30%)
#    - Maioria tem num_ocorrencias = 1
#    - Média: ~0.1 (= 1/10)
#    Contribuição: 0.1 × 0.30 = 0.03

# 3. Fonte (20%)
#    - Perplexity (0.95), Jina (0.90), Tavily (0.85), Serper (0.80)
#    - Média das 3 ferramentas: 0.88
#    Contribuição: 0.88 × 0.20 = 0.176

# 4. Título Match (10%)
#    - Muitos títulos não contêm palavras-chave específicas
#    - Média: ~0.05
#    Contribuição: 0.05 × 0.10 = 0.005

# TOTAL: 0.12 + 0.03 + 0.176 + 0.005 = 0.331 teoricamente
# REAL: 0.193 observado (45% mais baixo)

# Possíveis motivos da discrepância:
# - Dados podem estar parseados incorretamente
# - Queries podem ser muito amplas ou não específicas
# - Descrições vazias (não preenchidas), reduzindo relevância
# - Hash duplicadas podem estar eliminando bons resultados
```

---

## Impacto de cada Fator (Simulação)

### Cenário 1: Score Máximo Teórico
```
Relevância:    1.0 × 0.40 = 0.40
Ocorrências:   1.0 × 0.30 = 0.30
Fonte:         1.0 × 0.20 = 0.20
Título Match:  1.0 × 0.10 = 0.10
─────────────────────────────
TOTAL:                    = 1.00  ✅ MÁXIMO
```

### Cenário 2: Score Mínimo Teórico
```
Relevância:    0.0 × 0.40 = 0.00
Ocorrências:   0.0 × 0.30 = 0.00
Fonte:         0.4 × 0.20 = 0.08
Título Match:  0.0 × 0.10 = 0.00
─────────────────────────────
TOTAL:                    = 0.08  ❌ MÍNIMO (apenas fonte)
```

### Cenário 3: Score Típico Observado (0.193)
```
Relevância:    0.35 × 0.40 = 0.14  (relevância mediana baixa)
Ocorrências:   0.10 × 0.30 = 0.03  (maioria aparece 1x)
Fonte:         0.80 × 0.20 = 0.16  (média das ferramentas)
Título Match:  0.20 × 0.10 = 0.02  (match parcial)
─────────────────────────────
TOTAL:                    ≈ 0.35  (mas real é 0.193?)
```

**Nota**: Há uma discrepância. Possível que:
1. Descrições vazias (NULL) reduzem relevância
2. Queries sejam muito genéricas
3. Parseamento de resultados das APIs está incompleto
4. Hash_conteudo está eliminando duplicatas erroneamente

---

## Estrutura de Stop Words Português

O sistema remove estas palavras antes de calcular relevância:

```python
STOP_WORDS_PT = {
    "o", "a", "os", "as", "um", "uma", "uns", "umas",
    "e", "ou", "mas", "por", "para", "com", "sem",
    "de", "do", "da", "dos", "das", "ao", "aos", "a", "ante",
    "sob", "sobre", "em", "entre", "desde", "ate", "que",
    "qual", "quais", "quanto", "quantos", "quanta", "quantas",
    "quando", "onde", "como", "porque", "se", "nao",
    "sim", "talvez", "eh", "sao", "serao", "seria", "fosse",
    "foi", "era", "sendo", "ter", "tendo", "tido", "tenha"
}
```

**Exemplo**:
- Query: "o que são políticas de regulação de startups"
- Após remover stop words: ["que", "politicas", "regulacao", "startups"]
- Depois remove palavras <3 caracteres: ["politicas", "regulacao", "startups"]

