# Progresso da Implementacao - Sistema de Pesquisa Automatizada

**Data:** 2025-10-22
**Fase Atual:** Fase 1 (Base) - 60% concluida

---

## ✅ Implementado (Commit: 1e213fe)

### 1. Estrutura do Projeto
- ✅ Diretorios criados: `app/`, `app/api/`, `app/agente/`, `app/integracao/`, `app/utils/`, `static/`
- ✅ Arquivos base criados (vazios ou inicializados)
- ✅ Ambiente virtual Python configurado (`venv/`)
- ✅ Dependencias instaladas via `requirements.txt`

### 2. Configuracao e Banco de Dados
- ✅ **app/config.py**: Configuracoes com pydantic-settings, variaveis de ambiente
- ✅ **app/database.py**: Conexao SQLite assincron

a com aiosqlite
- ✅ **Tabelas criadas no SQLite:**
  - `resultados_pesquisa` (id, falha_id, titulo, descricao, fonte_url, fonte_tipo, pais_origem, idioma, confidence_score, num_ocorrencias, ferramenta_origem, hash_conteudo, timestamps)
  - `historico_pesquisas` (id, falha_id, query, idioma, ferramenta, status, resultados_encontrados, erro_mensagem, tempo_execucao, executado_em)
  - `fila_pesquisas` (id, falha_id, query, idioma, ferramenta, prioridade, tentativas, max_tentativas, status, criado_em)
  - Indices para performance criados
- ✅ Funcoes auxiliares: `get_falhas_mercado()`, `get_falha_by_id()`, `insert_resultado()`, `update_resultado_score()`, `delete_resultado()`, `get_estatisticas_gerais()`, `get_estatisticas_falha()`

### 3. Models e Schemas Pydantic
- ✅ **app/models.py**:
  - `FalhaMercado`
  - `ResultadoPesquisa`
  - `HistoricoPesquisa`
  - `FilaPesquisa`
  - `Estatisticas`
  - `EstatisticasFalha`
- ✅ **app/schemas.py**:
  - Request schemas: `ResultadoCreate`, `ResultadoUpdate`, `PesquisaIniciar`, `PesquisaCustom`
  - Response schemas: `FalhaResponse`, `ResultadoResponse`, `FalhaComResultados`, `StatusPesquisa`, `JobResponse`, `EstatisticasResponse`, `EstatisticasFalhaResponse`

### 4. Aplicacao FastAPI
- ✅ **app/main.py**: Ponto de entrada da aplicacao com lifecycle hooks
- ✅ Configuracao de rotas e static files
- ✅ Health check endpoint (`/health`)

---

## 🔄 Em Progresso

### 5. Endpoints da API (Parcial)
- ⏳ **app/api/falhas.py**: PENDENTE - Implementar rotas
  - `GET /api/falhas` - Listar todas as falhas
  - `GET /api/falhas/{id}` - Detalhe de uma falha
  - `GET /api/falhas/{id}/resultados` - Resultados de uma falha
- ⏳ **app/api/resultados.py**: PENDENTE - Implementar rotas
  - `GET /api/resultados` - Listar resultados com filtros
  - `GET /api/resultados/{id}` - Detalhe de um resultado
  - `PUT /api/resultados/{id}` - Editar resultado
  - `DELETE /api/resultados/{id}` - Deletar resultado
  - `POST /api/resultados` - Adicionar manualmente
- ⏳ **app/api/pesquisas.py**: PENDENTE - Implementar rotas
  - `POST /api/pesquisas/iniciar` - Iniciar pesquisa geral
  - `POST /api/pesquisas/custom` - Pesquisa customizada
  - `GET /api/pesquisas/status` - Status do processamento
  - `GET /api/pesquisas/historico` - Historico
- ⏳ **app/api/estatisticas.py**: PENDENTE - Criar arquivo
  - `GET /api/estatisticas` - Stats gerais
  - `GET /api/estatisticas/{falha_id}` - Stats de uma falha

---

## ⏳ Proximas Tarefas (Prioridade Alta)

### Fase 1 (Continuacao - Base): 40% restante
1. **Implementar todos os endpoints da API** (app/api/*.py)
2. **Testar endpoints manualmente** com curl ou Postman

### Fase 2: Integracao com APIs Externas
3. **app/integracao/perplexity_api.py**
   - Cliente HTTP para Perplexity AI
   - Metodo `pesquisar(query, idioma)` -> List[dict]
4. **app/integracao/jina_api.py**
   - Cliente para Jina AI (usando MCP)
   - Metodos `search_web()` e `read_url()`
5. **app/integracao/deep_research_mcp.py**
   - Cliente para MCP Deep Research
   - Metodo `pesquisar(query, sources="both")`

### Fase 3: Agente Pesquisador IA
6. **app/utils/idiomas.py**
   - Funcao `traduzir_query(query_pt, idioma_alvo)` usando LLM
   - Funcao `gerar_queries_variadas(falha, idioma, num_queries=5)`
   - Constante `IDIOMAS` com 8 idiomas
7. **app/utils/hash_utils.py**
   - Funcao `gerar_hash_conteudo(titulo, descricao, fonte)` -> str
8. **app/agente/avaliador.py**
   - Funcao `calcular_confidence_score()` com 4 fatores ponderados
   - Funcao `avaliar_relevancia_llm(resultado, falha)` usando Claude
9. **app/agente/deduplicador.py**
   - Funcao `verificar_duplicata()` com hash + similaridade
   - Funcao `atualizar_duplicata()` incrementando score/ocorrencias
10. **app/agente/pesquisador.py**
    - Classe `AgentePesquisador`
    - Metodo `executar_pesquisa_completa(falha_id)`
    - Metodo `gerar_queries(falha, idioma)`
    - Metodo `avaliar_relevancia(resultado, falha)`
    - Funcao CLI `popular_fila()` para criar todas as pesquisas na fila

### Fase 4: Worker Assincrono
11. **app/agente/processador.py**
    - Classe `ProcessadorPesquisas`
    - Metodo `processar_fila()` loop infinito consumindo fila
    - Metodo `executar_pesquisa(pesquisa)` chamando API correta
    - Metodo `processar_resultado()` com dedup + score + insert
    - Retry logic e error handling
    - Script CLI para rodar worker em background

### Fase 5: Dashboard Frontend
12. **static/index.html**
    - HTML completo com Tailwind CSS CDN
    - Alpine.js para reatividade
    - Estrutura: Header, Controls, Tabela de Falhas, Modal Detalhes, Modal Pesquisa Custom, Progress Bar
13. **static/js/dashboard.js**
    - Funcao `dashboardApp()` para Alpine.js
    - Metodos: `carregarFalhas()`, `verDetalhes()`, `atualizarScore()`, `deletar()`, `iniciarPesquisaGeral()`, `pesquisarCustom()`, `iniciarPoolingStatus()`
14. **static/css/styles.css**
    - Estilos customizados adicionais (alem do Tailwind)

### Fase 6: Testes e Refinamento
15. **Testar fluxo completo** com 1-2 falhas de amostra
16. **Ajustar thresholds** de confidence score
17. **Otimizar rate limiting** e delays
18. **Documentacao final** (README, INSTALL, USAGE)

---

## 📊 Estatisticas Atuais

- **Tabelas criadas:** 3 (resultados_pesquisa, historico_pesquisas, fila_pesquisas)
- **Falhas de mercado no banco:** 50
- **Resultados encontrados:** 0 (ainda nao iniciou pesquisa)
- **Pesquisas pendentes:** 0 (fila vazia)
- **Confidence medio:** 0.0

---

## 🚀 Como Continuar

### Passo 1: Implementar Endpoints da API
```bash
# Editar arquivos:
# - app/api/falhas.py
# - app/api/resultados.py
# - app/api/pesquisas.py

# Testar servidor:
source venv/bin/activate
python3 app/main.py
# OU
uvicorn app.main:app --reload --port 8000

# Testar endpoints:
curl http://localhost:8000/health
curl http://localhost:8000/api/falhas
```

### Passo 2: Implementar Clientes de APIs
```bash
# Editar arquivos:
# - app/integracao/perplexity_api.py
# - app/integracao/jina_api.py
# - app/integracao/deep_research_mcp.py

# Testar clientes individualmente (criar script de teste)
```

### Passo 3: Implementar Agente Pesquisador
```bash
# Editar arquivos na ordem:
# 1. app/utils/idiomas.py
# 2. app/utils/hash_utils.py
# 3. app/agente/avaliador.py
# 4. app/agente/deduplicador.py
# 5. app/agente/pesquisador.py

# Popular fila (primeira vez):
python3 -m app.agente.pesquisador popular_fila
```

### Passo 4: Iniciar Worker Assincrono
```bash
# Editar:
# - app/agente/processador.py

# Rodar worker (em terminal separado):
python3 -m app.agente.processador
```

### Passo 5: Criar Dashboard
```bash
# Editar:
# - static/index.html
# - static/js/dashboard.js
# - static/css/styles.css

# Acessar: http://localhost:8000/
```

---

## 📝 Notas Importantes

1. **Encoding:** Todos os arquivos Python devem ter `# -*- coding: utf-8 -*-` no topo
2. **Acentos:** Evitar acentos em docstrings/comentarios (problemas de encoding no macOS)
3. **Python Version:** Python 3.14 (verificado)
4. **Idiomas configurados:** 8 idiomas (pt, en, es, fr, de, it, ar, ko, he)
5. **Queries por falha:** 5+ queries × 3 ferramentas = 15+ por falha
6. **Total estimado de pesquisas:** 50 falhas × 15+ queries × 8 idiomas = **6.000+ pesquisas**
7. **Tempo estimado de execucao:** 20-40 horas com rate limiting
8. **APIs necessarias:**
   - JINA_API_KEY: ✅ Configurada
   - PERPLEXITY_API_KEY: ✅ Configurada
   - ANTHROPIC_API_KEY: ⚠️ Opcional (ainda nao configurada)

---

## 🛠️ Comandos Uteis

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Inicializar/verificar tabelas
python3 -m app.database

# Rodar servidor FastAPI
python3 app/main.py
# OU com reload automatico:
uvicorn app.main:app --reload --port 8000

# Verificar banco de dados
sqlite3 falhas_mercado_v1.db "SELECT COUNT(*) FROM falhas_mercado;"
sqlite3 falhas_mercado_v1.db "SELECT * FROM resultados_pesquisa LIMIT 10;"

# Commits
git add .
git commit -m "feat: Implementar [funcionalidade]"
git push origin main
```

---

## 🎯 Objetivo Final

Sistema completo com:
- ✅ 50 falhas de mercado mapeadas
- 🎯 500-2.000 politicas publicas internacionais encontradas
- 🎯 Dashboard interativo para visualizacao e edicao
- 🎯 Confidence score >= 0.7 para resultados de alta qualidade
- 🎯 Distribuicao por pais, idioma e pilar
- 🎯 Exportacao para CSV/PDF para relatorios

**Status:** 30% concluido | **Proximo commit:** Implementar endpoints da API
