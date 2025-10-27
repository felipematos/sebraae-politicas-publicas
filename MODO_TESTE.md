# 🧪 Modo Teste - Pesquisa Multilíngue

## Visão Geral

O **Modo Teste** permite processar uma amostra pequena de queries traduzidas antes de rodar o processamento completo dos 10,800+ resultados.

### Estado Atual da Fila
- **Total de entradas**: 12,000
  - 1,200 em português (status: `completa`)
  - 10,800 em 9 idiomas (status: `pendente`)

### Arquitetura de Tradução
Cada resultado é armazenado em **3 idiomas**:
- `titulo` / `descricao` - Idioma original da pesquisa
- `titulo_pt` / `descricao_pt` - Tradução para português
- `titulo_en` / `descricao_en` - Tradução para inglês

---

## 🚀 Como Usar o Modo Teste

### 1. Ativar o Modo Teste

```bash
curl -X POST "http://localhost:8000/api/config/test-mode/true"
```

**Resposta esperada:**
```json
{
  "mensagem": "Modo teste ATIVADO",
  "test_mode_enabled": true,
  "test_mode_limit": 10,
  "timestamp": "2024-10-27T..."
}
```

### 2. (Opcional) Ajustar o Limite de Queries

Por padrão, processa as primeiras **10 queries**. Para alterar:

```bash
# Para processar 20 queries
curl -X POST "http://localhost:8000/api/config/test-mode/limit/20"

# Para processar 50 queries
curl -X POST "http://localhost:8000/api/config/test-mode/limit/50"
```

### 3. Iniciar a Pesquisa em Modo Teste

```bash
# Inicia pesquisa com limite de 10 queries
curl -X POST "http://localhost:8000/api/pesquisas/iniciar"
```

**O que acontece:**
- Sistema processa apenas as primeiras **10 queries pendentes**
- Cada resultado é traduzido para português e inglês
- Traduções armazenadas em colunas separadas do banco
- Após 10 queries, o processamento para automaticamente

### 4. Verificar Resultados em Modo Teste

```bash
# Ver quantas queries foram processadas
curl "http://localhost:8000/api/pesquisas/status"

# Ver um resultado específico com suas traduções
sqlite3 falhas_mercado_v1.db << 'EOF'
SELECT
  id,
  titulo,           -- Idioma original
  titulo_pt,        -- Tradução português
  titulo_en,        -- Tradução inglês
  idioma,
  ferramenta_origem
FROM resultados_pesquisa
WHERE id > 13703  -- Resultados novos após teste
LIMIT 5;
EOF
```

### 5. Desativar o Modo Teste

```bash
curl -X POST "http://localhost:8000/api/config/test-mode/false"
```

**Resposta esperada:**
```json
{
  "mensagem": "Modo teste DESATIVADO",
  "test_mode_enabled": false,
  "test_mode_limit": 10,
  "timestamp": "2024-10-27T..."
}
```

### 6. Processar Todas as Queries

Após validar os resultados do teste, processe o restante:

```bash
# Garante que modo teste está desativado
curl -X POST "http://localhost:8000/api/config/test-mode/false"

# Inicia pesquisa em escala completa (10,790 queries restantes)
curl -X POST "http://localhost:8000/api/pesquisas/iniciar"
```

---

## 📊 Verificar Status do Modo Teste

```bash
curl "http://localhost:8000/api/config/test-mode"
```

**Resposta:**
```json
{
  "test_mode_enabled": false,
  "test_mode_limit": 10,
  "descricao": "Quando ativado, processa apenas as primeiras N queries para testes"
}
```

---

## 💾 Estrutura de Dados - Resultados

### Colunas da Tabela `resultados_pesquisa`

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `titulo` | TEXT | Título no idioma original da pesquisa |
| `descricao` | TEXT | Descrição no idioma original |
| `titulo_pt` | TEXT | **Novo** - Título traduzido para português |
| `descricao_pt` | TEXT | **Novo** - Descrição traduzida para português |
| `titulo_en` | TEXT | **Novo** - Título traduzido para inglês |
| `descricao_en` | TEXT | **Novo** - Descrição traduzida para inglês |
| `idioma` | TEXT | Idioma original (en, es, fr, de, it, ar, ja, ko, he) |
| `ferramenta_origem` | TEXT | Ferramenta que gerou o resultado (perplexity, jina, etc) |
| `confidence_score` | REAL | Score de confiança (0-1) |
| `query` | TEXT | Query que gerou este resultado |

### Exemplo de Resultado com Todas as Traduções

```sql
SELECT
  titulo,
  titulo_pt,
  titulo_en,
  idioma
FROM resultados_pesquisa
WHERE idioma = 'es'
LIMIT 1;
```

Resultado esperado:
```
titulo (Español): "Políticas Públicas para Innovación en Startups"
titulo_pt: "Políticas Públicas para Inovação em Startups"
titulo_en: "Public Policies for Innovation in Startups"
idioma: "es"
```

---

## ⚙️ Configuração (app/config.py)

```python
# Modo Teste - Limita pesquisa a um pequeno número de queries para testes
TEST_MODE: bool = False
TEST_MODE_LIMIT: int = 10  # Número de queries a processar em modo teste
```

---

## 🔧 Endpoints da API

### 1. GET `/api/config/test-mode`
Retorna status atual do modo teste.

**Resposta:**
```json
{
  "test_mode_enabled": false,
  "test_mode_limit": 10,
  "descricao": "Quando ativado, processa apenas as primeiras N queries para testes"
}
```

### 2. POST `/api/config/test-mode/{enabled}`
Ativa ou desativa o modo teste.

**Parâmetro:** `enabled` (true ou false)

**Exemplos:**
```bash
curl -X POST "http://localhost:8000/api/config/test-mode/true"
curl -X POST "http://localhost:8000/api/config/test-mode/false"
```

### 3. POST `/api/config/test-mode/limit/{limit}`
Define quantas queries processar em modo teste.

**Parâmetro:** `limit` (1-1000)

**Exemplos:**
```bash
curl -X POST "http://localhost:8000/api/config/test-mode/limit/10"
curl -X POST "http://localhost:8000/api/config/test-mode/limit/50"
```

---

## 📈 Fluxo Recomendado de Teste

### Fase 1: Teste Inicial (10 queries)
```bash
# 1. Ativar modo teste com limite padrão (10)
curl -X POST "http://localhost:8000/api/config/test-mode/true"

# 2. Iniciar pesquisa
curl -X POST "http://localhost:8000/api/pesquisas/iniciar"

# 3. Aguardar conclusão (monitor em /api/pesquisas/status)
# 4. Validar resultados com:
sqlite3 falhas_mercado_v1.db "SELECT titulo, titulo_pt, titulo_en FROM resultados_pesquisa WHERE id > 13703 LIMIT 3;"
```

### Fase 2: Teste Expandido (50 queries)
```bash
# 1. Ajustar limite para 50
curl -X POST "http://localhost:8000/api/config/test-mode/limit/50"

# 2. Reset do contador interno (reiniciar app ou API pode ser necessário)

# 3. Iniciar pesquisa expandida
curl -X POST "http://localhost:8000/api/pesquisas/iniciar"

# 4. Validar qualidade das traduções
sqlite3 falhas_mercado_v1.db "SELECT COUNT(*) FROM resultados_pesquisa WHERE titulo_en IS NOT NULL;"
```

### Fase 3: Processamento Completo
```bash
# 1. Desativar modo teste
curl -X POST "http://localhost:8000/api/config/test-mode/false"

# 2. Iniciar processamento completo (10,790 queries restantes)
curl -X POST "http://localhost:8000/api/pesquisas/iniciar"

# 3. Monitorar progresso
watch -n 5 'curl -s http://localhost:8000/api/pesquisas/status | jq'
```

---

## 🐛 Troubleshooting

### Problema: Modo teste não para após 10 queries
**Solução:** Reiniciar a aplicação para resetar o contador `processadas`.

```bash
# Reiniciar o serviço
systemctl restart pesquisas  # ou equivalente para seu setup
```

### Problema: Traduções vazias (NULL)
**Causa provável:** Rate limiting da API Claude.
**Solução:** Aguardar alguns minutos e reprocessar, ou aumentar o delay entre requests em `app/config.py`:

```python
RATE_LIMIT_DELAY: float = 2.0  # Aumentar de 1.0 para 2.0
```

### Problema: Coluna `titulo_en` não encontrada
**Solução:** Executar script para adicionar colunas:

```python
import sqlite3

conn = sqlite3.connect('falhas_mercado_v1.db')
cursor = conn.cursor()

cursor.execute("ALTER TABLE resultados_pesquisa ADD COLUMN titulo_en TEXT")
cursor.execute("ALTER TABLE resultados_pesquisa ADD COLUMN descricao_en TEXT")

conn.commit()
conn.close()
```

---

## 📝 Notas Importantes

1. **Modo Teste respeita status da fila:** Processa apenas queries com status `pendente`
2. **Traduções são incrementais:** Se reprocessar com modo teste ativado novamente, cria novos registros
3. **Limite máximo:** 1000 queries (para evitar timeout acidental)
4. **Rate limiting:** Claude API pode ter delays, considere aumentar `RATE_LIMIT_DELAY`
5. **Multi-idioma:** Cada resultado é armazenado em 3 idiomas para máxima flexibilidade

---

## 🎯 Próximos Passos

1. ✅ Validar 10 primeiras queries em modo teste
2. ✅ Verificar qualidade das traduções (português e inglês)
3. ✅ Expandir para 50-100 queries
4. ✅ Desativar modo teste
5. ✅ Processar 10,790 queries restantes
6. 📊 Analisar resultados finais (12,000 total com traduções)
