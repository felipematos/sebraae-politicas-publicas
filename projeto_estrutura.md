# Estrutura do Projeto Sebrae Nacional - Análise Completa

## 1. ARQUITETURA GERAL

### Stack Tecnológico
- **Backend**: FastAPI (Python 3.x) com asyncio
- **Database**: SQLite 3.x (falhas_mercado_v1.db)
- **APIs Externas**: Perplexity AI, Jina, Tavily, Serper, Exa, Deep Research (MCP)
- **Processamento**: Agente de pesquisa orquestrador com 6 ferramentas paralelas

---

## 2. BANCO DE DADOS - SCHEMA SQL

### Tabelas Criadas

#### A. `falhas_mercado` (Original - 50 registros)
```sql
CREATE TABLE falhas_mercado (
    id INTEGER PRIMARY KEY,
    titulo TEXT NOT NULL,
    pilar TEXT NOT NULL,              -- Ex: "1. Talento", "6. Regulação"
    descricao TEXT NOT NULL,
    dica_busca TEXT NOT NULL          -- Guia para pesquisa
);
```

#### B. `resultados_pesquisa` (Nova - 1,503 registros)
```sql
CREATE TABLE resultados_pesquisa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    falha_id INTEGER NOT NULL,
    titulo TEXT NOT NULL,
    descricao TEXT,
    fonte_url TEXT NOT NULL,
    fonte_tipo TEXT,                  -- Ex: "web", "artigo", "lei", "programa"
    pais_origem TEXT,                 -- País de origem da pesquisa
    idioma TEXT,                       -- Ex: "pt", "en", "es", "ar", "it", "fr", "de", "ko"
    confidence_score REAL DEFAULT 0.5, -- Score de confiança (0.0-1.0)
    num_ocorrencias INTEGER DEFAULT 1, -- Quantas vezes apareceu
    ferramenta_origem TEXT,            -- Ex: "perplexity", "jina", "tavily", "serper"
    hash_conteudo TEXT UNIQUE,         -- Hash SHA256 para deduplicação
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (falha_id) REFERENCES falhas_mercado(id)
);

-- Índices de Performance
CREATE INDEX idx_resultados_falha ON resultados_pesquisa(falha_id);
CREATE INDEX idx_resultados_score ON resultados_pesquisa(confidence_score DESC);
```

#### C. `historico_pesquisas` (Nova - 0 registros, pronto para uso)
```sql
CREATE TABLE historico_pesquisas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    falha_id INTEGER NOT NULL,
    query TEXT NOT NULL,
    idioma TEXT NOT NULL,
    ferramenta TEXT NOT NULL,
    status TEXT DEFAULT 'pendente',    -- 'pendente', 'processando', 'concluido', 'erro'
    resultados_encontrados INTEGER DEFAULT 0,
    erro_mensagem TEXT,
    tempo_execucao REAL,               -- Tempo em segundos
    executado_em DATETIME,
    FOREIGN KEY (falha_id) REFERENCES falhas_mercado(id)
);

CREATE INDEX idx_historico_falha ON historico_pesquisas(falha_id);
```

#### D. `fila_pesquisas` (Nova - 10,800 registros)
```sql
CREATE TABLE fila_pesquisas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    falha_id INTEGER NOT NULL,
    query TEXT NOT NULL,
    idioma TEXT NOT NULL,
    ferramenta TEXT NOT NULL,         -- Ex: "perplexity", "jina", "tavily"
    prioridade INTEGER DEFAULT 0,     -- 0=normal, maior=mais prioritário
    tentativas INTEGER DEFAULT 0,     -- Tentativas realizadas
    max_tentativas INTEGER DEFAULT 3, -- Limite de tentativas
    status TEXT DEFAULT 'pendente',   -- 'pendente', 'processando', 'concluido', 'erro'
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (falha_id) REFERENCES falhas_mercado(id)
);

CREATE INDEX idx_fila_status ON fila_pesquisas(status, prioridade DESC);
```

---

## 3. ESTATÍSTICAS DE DADOS ATUAIS

### Registros Presentes
| Tabela | Total | Status |
|--------|-------|--------|
| falhas_mercado | 50 | Original |
| resultados_pesquisa | 1,503 | Pesquisas completadas |
| fila_pesquisas | 10,800 | Em processamento |
| historico_pesquisas | 0 | Não iniciado |

### Distribuição de Resultados por Ferramenta
| Ferramenta | Total | Avg Score |
|------------|-------|-----------|
| perplexity | 646 | 0.170 |
| serper | 425 | 0.202 |
| tavily | 420 | 0.220 |

### Distribuição de Resultados por Idioma
| Idioma | Total | Avg Score |
|--------|-------|-----------|
| pt (Português) | 222 | 0.213 |
| he (Hebraico) | 105 | 0.212 |
| en (Inglês) | 208 | 0.178 |
| ar (Árabe) | 179 | 0.195 |
| it (Italiano) | 170 | 0.191 |
| es (Espanhol) | 170 | 0.195 |
| de (Alemão) | 148 | 0.183 |
| fr (Francês) | 154 | 0.180 |
| ko (Coreano) | 147 | 0.193 |

### Distribuição por Falha (Top 5)
| Falha ID | Total Resultados | Avg Score |
|----------|------------------|-----------|
| 1 | 529 | 0.205 |
| 2 | 505 | 0.214 |
| 3 | 367 | 0.155 |
| 4 | 61 | 0.153 |
| 5 | 25 | 0.206 |

### Análise de Confidence Score
- **Min**: 0.11
- **Max**: 0.477
- **Média**: 0.193
- **% acima de 0.5**: 0%
- **% acima de 0.7**: 0%
- **Observação**: Todos os scores estão entre 0.11 e 0.477 (bem abaixo de 1.0)

### Outros Dados
- **Fonte Tipo**: Todas as 1,503 registros têm `fonte_tipo = "web"`
- **País Origem**: Não preenchido (NULL) para todos os registros
- **Total de Pesquisas na Fila**: 10,800 (50 falhas × 6 idiomas × 36 queries por falha)

---

## 4. LÓGICA DE CÁLCULO DE CONFIDENCE SCORE

### Arquivo: `app/agente/avaliador.py`

#### Função Principal: `calcular_score_ponderado()`
Combina 4 fatores com pesos:

```python
score = (
    score_relevancia * 0.40 +           # 40% - Quanto relevante para a query
    valor_ocorrencias * 0.30 +          # 30% - Quantas vezes apareceu
    confiabilidade_fonte * 0.20 +       # 20% - Confiabilidade da fonte
    valor_titulo_match * 0.10           # 10% - Se título contém palavras-chave
)
```

#### 1. Score de Relevância (40%)
- **Função**: `calcular_score_relevancia(resultado, query)`
- **Algoritmo**:
  - Extrai palavras-chave da query (remove stop words em PT)
  - Conta quantas palavras-chave aparecem no resultado
  - Score base: `(matches / total_palavras) * 0.7`
  - Bonus de phrase: +0.2 se query completa aparece (ou +0.05 se todas as palavras presentes)
  - Range: 0.0 a 1.0

#### 2. Score de Ocorrências (30%)
- **Cálculo**: `min(1.0, num_ocorrencias / 10.0)`
- **Lógica**: Normaliza ocorrências assumindo máximo de 10 como 100%
- **Range**: 0.0 a 1.0

#### 3. Confiabilidade da Fonte (20%)
- **Tabela de Scores**:
  | Fonte | Score |
  |-------|-------|
  | perplexity | 0.95 |
  | jina | 0.90 |
  | deep_research | 0.85 |
  | google | 0.80 |
  | wikipedia | 0.75 |
  | blog | 0.50 |
  | social_media | 0.30 |
  | unknown | 0.40 (default) |

#### 4. Match no Título (10%)
- **Cálculo**: Proporcão de palavras-chave que aparecem no título
- **Range**: 0.0 a 1.0

### Score Final
- **Range**: 0.0 a 1.0 (clipped com `min(1.0, max(0.0, score))`)
- **Score Atual Médio**: 0.193 (muito baixo)

---

## 5. INSERÇÃO E ATUALIZAÇÃO DE RESULTADOS

### Arquivo: `app/database.py`

#### Função: `insert_resultado(resultado: Dict[str, Any]) -> int`
```python
async def insert_resultado(resultado: Dict[str, Any]) -> int:
    query = """
    INSERT INTO resultados_pesquisa (
        falha_id, titulo, descricao, fonte_url, fonte_tipo,
        pais_origem, idioma, confidence_score, ferramenta_origem,
        hash_conteudo
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    # Retorna o ID do resultado inserido
    return cursor.lastrowid
```

#### Função: `update_resultado_score(resultado_id: int, novo_score: float) -> None`
```python
async def update_resultado_score(resultado_id: int, novo_score: float):
    await db.execute("""
        UPDATE resultados_pesquisa
        SET confidence_score = ?,
            atualizado_em = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (novo_score, resultado_id))
```

#### Função: `delete_resultado(resultado_id: int) -> None`
Deleta um resultado específico.

### Deduplicação
- **Campo**: `hash_conteudo TEXT UNIQUE`
- **Geração**: SHA256 hash de `(titulo + descricao + fonte_url)`
- **Localização**: `app/utils/hash_utils.py` - função `gerar_hash_conteudo()`
- **Impacto**: Impede duplicatas com constraint UNIQUE no banco

---

## 6. ARQUIVOS PYTHON RELEVANTES

### Core Database
- **`app/database.py`** (356 linhas)
  - Gerenciador de conexões SQLite assincronas
  - CRUD para resultados, histórico, fila
  - Funções de estatísticas

- **`app/models.py`** (92 linhas)
  - Modelos Pydantic para dados
  - Classes: FalhaMercado, ResultadoPesquisa, HistoricoPesquisa, FilaPesquisa
  - Validação de tipos com field constraints

### Schemas API
- **`app/schemas.py`** (122 linhas)
  - Schemas de request/response
  - Classes para criação, atualização, listagem

### APIs
- **`app/api/resultados.py`** (189 linhas)
  - GET/POST/PUT/DELETE para resultados
  - Listagem com filtros (score, idioma, falha_id)
  - Criação manual de resultados

- **`app/api/pesquisas.py`** (150+ linhas)
  - POST `/pesquisas/iniciar` - Inicia pesquisa automatizada
  - POST `/pesquisas/custom` - Pesquisa customizada
  - GET `/pesquisas/progresso` - Status da pesquisa em tempo real

- **`app/api/falhas.py`**
  - Endpoints para gerenciar falhas de mercado

### Agente de Pesquisa
- **`app/agente/pesquisador.py`** (601 linhas)
  - Classe `AgentePesquisador` - Orquestrador principal
  - Métodos principais:
    - `gerar_queries()` - Cria queries multilingues
    - `popular_fila()` - Popula fila com 1 query × N ferramentas
    - `executar_pesquisa()` - Executa com todas as ferramentas
    - `executar_pesquisa_adaptativa()` - Para quando qualidade é suficiente
    - `obter_progresso()` - Status atual
    - `sincronizar_com_banco()` - Sync com DB

- **`app/agente/avaliador.py`** (544 linhas)
  - Classe `Avaliador` - Calcula confidence scores
  - Métodos principais:
    - `calcular_score_relevancia()` - Score de relevância
    - `calcular_score_ponderado()` - Score final (4 fatores)
    - `avaliar()` - Avalia resultado individual
    - `avaliar_batch()` - Paralelo para múltiplos
    - `avaliar_qualidade_conjunto()` - Heurística para continuar/parar
  - Suporte a RAG (Retrieval-Augmented Generation)
  - Cache de avaliações

### APIs de Terceiros
- **`app/integracao/perplexity_api.py`** - Cliente Perplexity
- **`app/integracao/jina_api.py`** - Cliente Jina
- **`app/integracao/tavily_api.py`** - Cliente Tavily
- **`app/integracao/serper_api.py`** - Cliente Serper
- **`app/integracao/exa_api.py`** - Cliente Exa
- **`app/integracao/deep_research_mcp.py`** - Cliente Deep Research (MCP)

---

## 7. FLUXO DE SALVAMENTO E ATUALIZAÇÃO

### Fase 1: Geração de Queries
```
1. AgentePesquisador.popular_fila()
   ├─ Para cada falha
   ├─ Gera queries multilingues via gerar_queries()
   └─ Para CADA query, insere N entradas na fila (1 por ferramenta)
      └─ Tabela: fila_pesquisas (status='pendente')
         
Resultado: 10,800 entradas na fila
(50 falhas × ~6 queries × ~36 idiomas/ferramentas)
```

### Fase 2: Execução de Pesquisas
```
2. Worker processa fila_pesquisas
   ├─ Pega entrada (status='pendente')
   ├─ Atualiza status → 'processando'
   ├─ Chama API (perplexity, jina, tavily, etc.)
   ├─ Recebe lista de resultados
   └─ Para CADA resultado:
      ├─ Gera hash_conteudo
      ├─ Calcula confidence_score via Avaliador
      ├─ Insere em resultados_pesquisa
      └─ Registra em historico_pesquisas

Resultado: resultados_pesquisa e historico_pesquisas populados
```

### Fase 3: Atualização de Scores
```
3. Refinamento (opcional)
   ├─ Buscar resultado por ID
   ├─ Avaliar novamente com contexto RAG
   ├─ UPDATE confidence_score + atualizado_em
   └─ Log no histórico

Função: update_resultado_score(resultado_id, novo_score)
```

---

## 8. EXEMPLO DE REGISTRO ARMAZENADO

```json
{
  "id": 2088,
  "falha_id": 17,
  "titulo": "Políticas públicas no desenvolvimento do empreendedorismo",
  "descricao": null,
  "fonte_url": "https://startups.com.br/artigo/politicas-...",
  "fonte_tipo": "web",
  "pais_origem": null,
  "idioma": "it",
  "confidence_score": 0.222,
  "num_ocorrencias": 1,
  "ferramenta_origem": "perplexity",
  "hash_conteudo": "fb49b564269448fe611e17b79b7d51e770cf1a9518...",
  "criado_em": "2025-10-23 02:20:26",
  "atualizado_em": "2025-10-23 02:20:26"
}
```

---

## 9. FUNCIONALIDADES PRINCIPAIS

### Pesquisa Adaptativa
- **Função**: `executar_pesquisa_adaptativa()`
- **Lógica**:
  1. Executa mínimo de buscas (configurável)
  2. Após mínimo, avalia qualidade do conjunto
  3. Se qualidade >= threshold: PARA
  4. Se qualidade marginal: pode continuar
  5. Respeita máximo de buscas

### Rotação de Ferramentas
- **Implementação**: `popular_fila()` em pesquisador.py (linhas 200-224)
- **Lógica**: Cada query recebe as ferramentas em ordem rotacionada
  - Query 1: [perplexity, jina, tavily, serper]
  - Query 2: [jina, tavily, serper, perplexity]
  - Query 3: [tavily, serper, perplexity, jina]
  - etc.
- **Objetivo**: Enriquecer resultados com diversidade de fontes

### RAG (Retrieval-Augmented Generation)
- **Arquivo**: `app/vector/vector_store.py`
- **Função**: Busca resultados similares históricos
- **Impacto no Score**:
  - Boost de +0.1 se similar de alta qualidade (>0.75)
  - Redução de -0.15 se similar de baixa qualidade (<0.5)
  - Max ajuste: ±0.3

---

## 10. CONFIGURAÇÃO E SETTINGS

### Arquivo: `app/config.py`
```python
# Idiomas suportados
IDIOMAS = ["pt", "en", "es", "fr", "de", "it", "ar", "ko"]

# Ferramentas ativadas
SEARCH_CHANNELS_ENABLED = {
    "perplexity": True,
    "jina": True,
    "tavily": True,
    "serper": True,
    "exa": False,
    "deep_research": False
}

# Busca Adaptativa
USAR_BUSCA_ADAPTATIVA = True
MIN_BUSCAS_POR_FALHA = 2
MAX_BUSCAS_POR_FALHA = 4
QUALIDADE_MINIMA_PARA_PARAR = 0.75

# RAG
RAG_ENABLED = False (por padrão)
RAG_SIMILARITY_THRESHOLD = 0.8
```

---

## 11. PROBLEMA IDENTIFICADO: Scores Muito Baixos

### Questão Principal
Por que os scores estão todos abaixo de 0.5 (média 0.193)?

### Possíveis Causas
1. **Relevância baixa**: Palavras-chave da query não aparecem nos resultados
2. **Dados incorretos**: Resultados podem ter sido parseados mal pelas APIs
3. **Query genérica**: Queries podem ser muito amplas
4. **Fonte desconhecida**: Default score de fonte é 0.40, não 0.95

### Análise
- Perplexity (0.95 score de fonte) tem média 0.170 nos dados
- Isso sugere que o fator maior é relevância ou ocorrências baixas
- Nenhum resultado tem >0.477, então há cap ou problema na avaliação

---

## 12. RESUMO DA ARQUITETURA

```
┌─────────────────────────────────────────────────────────────┐
│                    SEBRAE NACIONAL                          │
│               Sistema de Pesquisa de Políticas              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    ENTRADA                                  │
│  50 Falhas de Mercado (DB original)                         │
│  8 Idiomas × N Queries = ~10,800 entradas na fila           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               PROCESSAMENTO PARALELO                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 6 Ferramentas de Pesquisa (APIs Externas):          │   │
│  │ • Perplexity AI (0.95 score de confiança)           │   │
│  │ • Jina (0.90)                                        │   │
│  │ • Tavily (0.85)                                      │   │
│  │ • Serper (0.80)                                      │   │
│  │ • Exa (0.85)                                         │   │
│  │ • Deep Research via MCP (0.85)                       │   │
│  └──────────────────────────────────────────────────────┘   │
│               ↓ Rotação de Ferramentas ↓                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        Avaliação de Confiança (Avaliador)           │   │
│  │  Score = 0.40×relevância + 0.30×ocorrências +       │   │
│  │          0.20×fonte + 0.10×titulo_match             │   │
│  └──────────────────────────────────────────────────────┘   │
│               ↓ Com suporte a RAG (opcional) ↓               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    BANCO DE DADOS                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ fila_pesquisas: 10,800 entradas (processamento)     │    │
│  │ resultados_pesquisa: 1,503 registros com scores     │    │
│  │ historico_pesquisas: Log de execuções               │    │
│  │ falhas_mercado: 50 falhas de mercado                │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Índices de Performance:                                    │
│  • idx_resultados_falha (busca por falha)                  │
│  • idx_resultados_score (ordenação por score)              │
│  • idx_fila_status (processamento eficiente)               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API REST (FastAPI)                       │
│  GET /resultados - Lista com filtros                        │
│  POST /resultados - Criar resultado manual                  │
│  PUT /resultados/{id} - Atualizar score                     │
│  POST /pesquisas/iniciar - Inicia pesquisa                  │
│  POST /pesquisas/custom - Pesquisa customizada              │
│  GET /pesquisas/progresso - Status em tempo real            │
│  GET /estatisticas - Dashboard                              │
└─────────────────────────────────────────────────────────────┘
```

---

## CONCLUSÃO

O sistema está **bem estruturado** com:
- ✅ Schema normalizado com 4 tabelas especializadas
- ✅ Índices de performance adequados
- ✅ Cálculo robusto de confidence scores (4 fatores ponderados)
- ✅ Suporte a 8 idiomas e 6 ferramentas de pesquisa
- ✅ Deduplicação via hash único
- ✅ API REST completa com CRUD
- ✅ Agente orquestrador com busca adaptativa
- ✅ Suporte a RAG para contexto histórico

**Preocupações Atuais**:
- ❌ Scores muito baixos (média 0.193, máx 0.477)
- ⚠️ Nenhum resultado acima de 0.5
- ⚠️ Histórico de pesquisas vazio (0 registros)
- ⚠️ País de origem não preenchido

