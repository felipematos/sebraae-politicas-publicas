# Fluxo Completo de Dados - Sebrae Nacional

## 1. FLUXO DE CRIAÇÃO DE QUERIES

```
┌─────────────────────────────────────────────────────────────────┐
│ ENTRADA: 50 Falhas de Mercado                                   │
│ (ID, título, pilar, descrição, dica_busca)                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ AGENTE PESQUISADOR                                              │
│ AgentePesquisador.popular_fila()                                │
│                                                                 │
│ Para cada falha:                                                │
│  ├─ Chamar gerar_queries_multilingues(falha)                    │
│  └─ Retorna N queries (1 por idioma)                            │
│                                                                 │
│ Idiomas: [pt, en, es, fr, de, it, ar, ko]                      │
│ Total de queries: 50 falhas × 6-8 idiomas = ~400 queries       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ ROTAÇÃO DE FERRAMENTAS                                          │
│ Para CADA query:                                                │
│  └─ Inserir 4 entradas na fila (1 por ferramenta ativada)      │
│                                                                 │
│ Ferramentas: [perplexity, jina, tavily, serper]                │
│ Rotação:                                                        │
│  - Query 1: [perp, jina, tav, serp]                             │
│  - Query 2: [jina, tav, serp, perp]                             │
│  - Query 3: [tav, serp, perp, jina]                             │
│  - Query 4: [serp, perp, jina, tav]                             │
│  - Query 5: [perp, jina, tav, serp] (repete)                    │
│                                                                 │
│ Total na fila: ~400 queries × 4 ferramentas × 6-8 idiomas       │
│            = 10,800 entradas em fila_pesquisas                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────┐
        │   FILA DE PESQUISAS (10,800 entradas)    │
        │                                          │
        │ Status: pendente, processando, concluido │
        │ Campos:                                  │
        │ • falha_id, query, idioma, ferramenta    │
        │ • prioridade, tentativas, status         │
        │ • criado_em                              │
        └──────────────────────────────────────────┘
```

---

## 2. FLUXO DE EXECUÇÃO DE PESQUISA

```
┌──────────────────────────────────────────────────────────────────┐
│ WORKER / API ENDPOINT                                            │
│ Processar fila_pesquisas[1]                                      │
│                                                                  │
│ entrada = {                                                      │
│   falha_id: 1,                                                   │
│   query: "inovação tecnologia empreendedorismo Brasil",          │
│   idioma: "pt",                                                  │
│   ferramenta: "perplexity",                                      │
│   status: "pendente"                                             │
│ }                                                                │
└──────────────────────────────┬─────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│ CHAMAR API EXTERNA                                               │
│ PerplexityClient.pesquisar(                                      │
│   query="inovação tecnologia empreendedorismo Brasil",           │
│   idioma="pt",                                                   │
│   max_resultados=5                                               │
│ )                                                                │
│                                                                  │
│ Retorna lista de resultados:                                     │
│ [                                                                │
│   {                                                              │
│     titulo: "Inovação em startups brasileiras...",               │
│     descricao: "Como as startups inovam...",                     │
│     url: "https://example.com/...",                              │
│     fonte: "startups.com.br"                                     │
│   },                                                             │
│   {...},                                                         │
│   ...                                                            │
│ ]                                                                │
└──────────────────────────────┬─────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│ PARA CADA RESULTADO RETORNADO:                                   │
│                                                                  │
│ 1. GERAR HASH PARA DEDUPLICAÇÃO                                  │
│    hash = SHA256(titulo + descricao + url)                       │
│    Verificar se hash já existe em resultados_pesquisa            │
│    - Se existe: PULAR (duplicata)                                │
│    - Se não existe: CONTINUAR                                    │
│                                                                  │
│ 2. AVALIAR CONFIANÇA (Avaliador)                                 │
│    score = avaliador.avaliar(                                    │
│      resultado={titulo, descricao, url, fonte},                  │
│      query=entrada.query,                                        │
│      num_ocorrencias=1                                           │
│    )                                                             │
│                                                                  │
│    Cálculo:                                                      │
│    - score_relevancia = 0.35 (ex)                                │
│    - valor_ocorrencias = 0.1 (1 vez)                             │
│    - confiab_fonte = 0.95 (perplexity)                           │
│    - valor_titulo = 0.6 (match parcial)                          │
│                                                                  │
│    confidence_score = (0.35×0.40) + (0.1×0.30) +                 │
│                       (0.95×0.20) + (0.6×0.10)                   │
│                    = 0.14 + 0.03 + 0.19 + 0.06                   │
│                    = 0.42                                        │
│                                                                  │
│ 3. INSERIR EM RESULTADOS_PESQUISA                                │
│    insert_resultado({                                            │
│      falha_id: 1,                                                │
│      titulo: "Inovação em startups brasileiras...",              │
│      descricao: "Como as startups inovam...",                    │
│      fonte_url: "https://example.com/...",                       │
│      fonte_tipo: "web",                                          │
│      pais_origem: null,                                          │
│      idioma: "pt",                                               │
│      confidence_score: 0.42,                                     │
│      ferramenta_origem: "perplexity",                            │
│      hash_conteudo: "abc123...xyz789"                            │
│    })                                                            │
│                                                                  │
│ 4. REGISTRAR EM HISTÓRICO (Opcional)                             │
│    inserir_historico_pesquisa({                                  │
│      falha_id: 1,                                                │
│      query: entrada.query,                                       │
│      idioma: "pt",                                               │
│      ferramenta: "perplexity",                                   │
│      status: "concluido",                                        │
│      resultados_encontrados: 5,                                  │
│      tempo_execucao: 2.34 (segundos),                            │
│      executado_em: datetime.now()                                │
│    })                                                            │
│                                                                  │
│ 5. ATUALIZAR STATUS DA FILA                                      │
│    UPDATE fila_pesquisas                                         │
│    SET status = 'concluido'                                      │
│    WHERE id = 1                                                  │
│                                                                  │
└──────────────────────────────┬─────────────────────────────────┘
                               │
                               ▼
         ┌────────────────────────────────────────┐
         │ RESULTADOS_PESQUISA (1,503 registros)  │
         │                                        │
         │ Campos:                                │
         │ • id (PK)                              │
         │ • falha_id (FK)                        │
         │ • titulo, descricao                    │
         │ • fonte_url, fonte_tipo                │
         │ • idioma                               │
         │ • confidence_score ← CALCULADO         │
         │ • ferramenta_origem                    │
         │ • hash_conteudo (UNIQUE)               │
         │ • criado_em, atualizado_em             │
         └────────────────────────────────────────┘
```

---

## 3. FLUXO DE ATUALIZAÇÃO DE SCORES (Opcional)

```
┌────────────────────────────────────────────────────────┐
│ REFINAMENTO PÓS-PROCESSAMENTO                          │
│ (Pode ser executado posteriormente)                    │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│ BUSCAR RESULTADO PARA REAVALIAR                        │
│                                                        │
│ SELECT * FROM resultados_pesquisa WHERE id = 2088     │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│ REAVALIAR COM CONTEXTO RAG (Se habilitado)            │
│                                                        │
│ 1. Buscar resultados similares históricos              │
│    vector_store.search_resultados(                     │
│      query=resultado.titulo + resultado.descricao,     │
│      n_results=3                                       │
│    )                                                   │
│                                                        │
│ 2. Ajustar score baseado em similares                  │
│    score_base = 0.42                                   │
│    Se similar de alta qualidade: +0.1                  │
│    Se similar de baixa qualidade: -0.15                │
│    ajuste = clamped entre -0.3 e +0.2                  │
│    score_final = 0.42 + ajuste                         │
│                                                        │
│ 3. Atualizar no banco                                  │
│    UPDATE resultados_pesquisa                          │
│    SET confidence_score = score_final,                 │
│        atualizado_em = CURRENT_TIMESTAMP               │
│    WHERE id = 2088                                     │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
         ┌────────────────────────────────────┐
         │ RESULTADO ATUALIZADO (2088)        │
         │                                    │
         │ confidence_score: 0.42 → 0.52      │
         │ (incrementado de +0.1 por RAG)     │
         │ atualizado_em: 2025-10-23 02:30:15 │
         └────────────────────────────────────┘
```

---

## 4. FLUXO DE FILTROS E QUERIES API

```
┌──────────────────────────────────────────────────────────┐
│ GET /resultados?                                         │
│   skip=0&                                                │
│   limit=50&                                              │
│   falha_id=1&                                            │
│   min_score=0.0&                                         │
│   max_score=1.0&                                         │
│   idioma=pt                                              │
└─────────────────────────────┬──────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────┐
│ QUERY SQL CONSTRUÍDA DINAMICAMENTE:                      │
│                                                          │
│ SELECT                                                   │
│   r.id, r.falha_id, r.titulo, r.descricao,              │
│   r.fonte_url, r.fonte_tipo, r.pais_origem,             │
│   r.idioma, r.confidence_score, r.num_ocorrencias,      │
│   r.ferramenta_origem, r.criado_em, r.atualizado_em,    │
│   f.titulo as falha_titulo,                              │
│   f.pilar                                                │
│ FROM resultados_pesquisa r                               │
│ JOIN falhas_mercado f ON r.falha_id = f.id              │
│ WHERE 1=1                                                │
│   AND r.falha_id = 1           ← Se falha_id fornecido  │
│   AND r.confidence_score BETWEEN 0.0 AND 1.0            │
│   AND r.idioma = 'pt'          ← Se idioma fornecido    │
│ ORDER BY r.confidence_score DESC                         │
│ LIMIT 50 OFFSET 0                                        │
└─────────────────────────────┬──────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────┐
│ ÍNDICES USADOS:                                          │
│ • idx_resultados_falha ON resultados_pesquisa(falha_id) │
│   ↑ Acelera WHERE r.falha_id = 1                         │
│                                                          │
│ • idx_resultados_score ON resultados_pesquisa(          │
│     confidence_score DESC)                               │
│   ↑ Acelera ORDER BY confidence_score DESC +             │
│     BETWEEN min_score AND max_score                      │
│                                                          │
│ • Índice implícito de PK: id                             │
│   ↑ Accelera JOIN com falhas_mercado                     │
└─────────────────────────────┬──────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────┐
│ RESPOSTA JSON (50 resultados com 14 campos cada)        │
│                                                          │
│ [                                                        │
│   {                                                      │
│     "id": 1234,                                          │
│     "falha_id": 1,                                       │
│     "titulo": "Inovação em startups...",                 │
│     "descricao": "Como as startups inovam...",           │
│     "fonte_url": "https://...",                          │
│     "fonte_tipo": "web",                                 │
│     "pais_origem": null,                                 │
│     "idioma": "pt",                                      │
│     "confidence_score": 0.42,                            │
│     "num_ocorrencias": 1,                                │
│     "ferramenta_origem": "perplexity",                   │
│     "criado_em": "2025-10-23T02:20:26",                  │
│     "atualizado_em": "2025-10-23T02:20:26",              │
│     "falha_titulo": "Acesso à educação em...",           │
│     "pilar": "1. Talento"                                │
│   },                                                     │
│   {...},                                                 │
│   ...                                                    │
│ ]                                                        │
└──────────────────────────────────────────────────────────┘
```

---

## 5. MATRIZ DE PROCESSAMENTO TOTAL

```
ENTRADA:
├─ 50 Falhas de Mercado
└─ 8 Idiomas

PROCESSAMENTO:

┌─────────────────────────────────────────┐
│ 1. GERAÇÃO DE QUERIES                   │
│ 50 falhas × 6 queries/falha             │
│ = 300 queries                           │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ 2. ROTAÇÃO DE FERRAMENTAS               │
│ 300 queries × 4 ferramentas × 8 idiomas │
│ = 9,600 entradas na fila                │
│ (Nota: observados 10,800 - incluem      │
│  tentativas/duplicatas de query)        │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ 3. EXECUÇÃO PARALELA                    │
│ 9,600 entradas × 1-5 resultados/entrada │
│ ≈ 15,000 chamadas de API                │
│ Com 4 ferramentas = 60,000 ops totais   │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ 4. DEDUPLICAÇÃO VIA HASH                │
│ 15,000 resultados → hash                │
│ Remover duplicatas (UNIQUE constraint)  │
│ Resultado: 1,503 registros únicos       │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ 5. CÁLCULO DE CONFIANÇA                 │
│ 1,503 resultados × Avaliador            │
│ Score: 0.11 - 0.477 (média 0.193)       │
└─────────────────────────────────────────┘
              │
              ▼
         BANCO DE DADOS
    ┌────────────────────┐
    │ 1,503 resultados   │
    │ 10,800 fila items  │
    │ 0 histórico (vazio)│
    └────────────────────┘
```

---

## 6. EXEMPLO COMPLETO: Falha #1 (Talento)

```
FALHA #1:
├─ ID: 1
├─ Pilar: "1. Talento"
├─ Título: "Deficiência em profissionais especializados"
├─ Dica_busca: "cursos, capacitação, treinamento"
└─ Resultados Esperados: 529 (observado)

QUERIES GERADAS (8 idiomas):
├─ PT: "profissionais especializados Brasil deficiência"
├─ EN: "specialized professionals Brazil skills gap"
├─ ES: "profesionales especializados Brasil déficit"
├─ IT: "professionisti specializzati Brasile carenza"
├─ FR: "professionnels spécialisés Brésil pénurie"
├─ DE: "spezialisierte Fachleute Brasilien Mangel"
├─ AR: "متخصصون محترفون البرازيل نقص"
└─ KO: "전문가 브라질 부족"

FILA (50 entradas):
├─ Query PT × 4 ferramentas = 4 entradas
├─ Query EN × 4 ferramentas = 4 entradas
├─ ...
└─ Total: 8 queries × 4 ferramentas = 32 entradas só para falha #1

RESULTADOS COLETADOS:
├─ Perplexity: ~150 resultados (avg score: 0.170)
├─ Serper: ~120 resultados (avg score: 0.202)
├─ Tavily: ~110 resultados (avg score: 0.220)
└─ Total bruto: ~380 → 529 após duplicatas (pois tem repeticoes)

SCORE MÉDIO DA FALHA #1:
├─ Calculado: 0.205
├─ Fator crítico: Relevância baixa em queries genéricas
├─ Hipótese: Descrições vazias (NULL) reduzem score
└─ Recomendação: Enriquecer com descrições de API antes de avaliar
```

