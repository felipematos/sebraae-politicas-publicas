# Configuração OpenRouter - Tradução com LLM Gratuito

## 🎯 Objetivo

Usar modelos LLM gratuitos da OpenRouter para traduzir queries de pesquisa com alto custo-benefício e fallback automático entre modelos.

## 📋 Idiomas Suportados (10)

| Código | Idioma | Status |
|--------|--------|--------|
| pt | Português (Brasil) | ✅ Nativo |
| en | Inglês | ✅ Nativo |
| es | Espanhol | ✅ Suportado |
| fr | Francês | ✅ Suportado |
| de | Alemão | ✅ Suportado |
| it | Italiano | ✅ Suportado |
| ar | Árabe | ✅ Suportado |
| **ja** | **Japonês** | ✅ **NOVO** |
| ko | Coreano | ✅ Suportado |
| he | Hebraico | ✅ Suportado |

## 🔧 Configuração

### 1. Obter Chave OpenRouter Gratuita

1. Acesse https://openrouter.io
2. Crie uma conta (grátis)
3. Vá para "Chaves de API" → "Criar chave"
4. Copie a chave

### 2. Adicionar ao .env

```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxx
```

### 3. Reiniciar Aplicação

```bash
# A aplicação carregará a nova chave
source venv/bin/activate
python main.py
```

## 🤖 Modelos Gratuitos Utilizados

A biblioteca faz fallback automático entre os seguintes modelos gratuitos, na ordem:

### 1. **Mistral 7B Instruct** (Preferido)
- Modelo: `mistralai/mistral-7b-instruct`
- Velocidade: ⚡ Muito rápido
- Qualidade: ⭐⭐⭐⭐
- Rate limit: Generoso
- Melhor para: Tradução geral, idiomas principais

### 2. **Phi 3 Mini** (Rápido)
- Modelo: `microsoft/phi-3-mini`
- Velocidade: ⚡⚡ Extremamente rápido
- Qualidade: ⭐⭐⭐
- Rate limit: Muito generoso
- Melhor para: Queries curtas, fallback rápido

### 3. **OpenChat 3.5** (Simples)
- Modelo: `openchat/openchat-3.5`
- Velocidade: ⚡ Rápido
- Qualidade: ⭐⭐⭐
- Rate limit: Bom
- Melhor para: Tarefas simples, idiomas principais

### 4. **GPT-3.5-turbo** (Confiável)
- Modelo: `gpt-3.5-turbo` (via OpenRouter)
- Velocidade: ⚡⚡ Rápido
- Qualidade: ⭐⭐⭐⭐⭐
- Rate limit: Generoso na OpenRouter
- Melhor para: Fallback final, traduções críticas

## 📊 Como Funciona

```
Query em Português
        ↓
[Tentar OpenRouter com Mistral 7B]
        ↓ (sucesso)
Resultado traduzido
        ↓ (falha/timeout)
[Tentar OpenRouter com Phi 3 Mini]
        ↓ (sucesso)
Resultado traduzido
        ↓ (falha/timeout)
[Tentar OpenRouter com OpenChat 3.5]
        ↓ (sucesso)
Resultado traduzido
        ↓ (falha/timeout/rate limit)
[Tentar GPT-3.5-turbo]
        ↓ (sucesso)
Resultado traduzido
        ↓ (todas as tentativas falharam)
[Usar Fallback: Mapeamento Estático]
Resultado com termos mapeados
```

## 💰 Custos

### OpenRouter (Modelos Gratuitos)
- Grátis para todos os modelos listados acima
- Rate limits generosos:
  - Mistral 7B: ~1000 req/min
  - Phi 3 Mini: ~500 req/min
  - OpenChat: ~500 req/min
  - GPT-3.5-turbo: ~3000 req/min (via OpenRouter)

### Estimativa de Uso
- **50 falhas × 6 queries × 10 idiomas = 3.000 queries/rodada**
- Cada query ocupa ~50-100 tokens
- **Totalmente gratuito** com OpenRouter

## 🚀 Monitoramento

### Logs de Tradução

Quando a tradução é executada, você verá logs como:

```
[TRADUÇÃO] ✓ Modelo: mistralai/mistral-7b-instruct
[TRADUÇÃO] ✗ Tentativa 1/4 com mistralai/mistral-7b-instruct: Rate limit atingido (429)
[TRADUÇÃO] ✓ Modelo: microsoft/phi-3-mini
```

### Estatísticas por Sessão

O sistema rastreia:
- Quantas traduções foram bem-sucedidas por modelo
- Quais modelos mais usados
- Rate limits atingidos

## ⚙️ Ajustes Avançados

### Modificar Temperatura
Editar `app/integracao/openrouter_api.py`, linha 102:

```python
"temperature": 0.3,  # 0.0 = consistente, 1.0 = criativo
```

### Adicionar Novo Modelo
Editar `app/integracao/openrouter_api.py`, linha 16:

```python
MODELOS_GRATUITOS = [
    "seu-novo-modelo-aqui",
    "mistralai/mistral-7b-instruct",
    # ...
]
```

### Desabilitar OpenRouter Temporariamente
Na função `traduzir_query()`, use `usar_llm=False`:

```python
resultado = await traduzir_query(query, "ja", "pt", usar_llm=False)
```

## 🐛 Troubleshooting

### "OPENROUTER_API_KEY não configurada"
- Verifique se `.env` tem a chave
- Reinicie a aplicação após adicionar

### "Todas as tentativas falharam"
- Verifique conexão de internet
- Confirme que a chave tem créditos (mesmo grátis, precisa verificação de conta)
- Tente chamar diretamente: https://api.openrouter.ai/

### Rate Limit (429)
- Sistema faz fallback automático
- Aguarda 1s entre tentativas
- Revise logs para ver qual modelo conseguiu

## 📝 Exemplo de Uso

```python
from app.utils.idiomas import traduzir_query

# Traduzir para Japonês
resultado = await traduzir_query(
    "falta de acesso a credito para startups",
    idioma_origem="pt",
    idioma_alvo="ja",
    usar_llm=True  # Usa OpenRouter
)

print(resultado)
# スタートアップのための信用アクセスの欠如
```

## 📚 Referências

- OpenRouter: https://openrouter.io
- Modelos Gratuitos: https://openrouter.io/docs/models
- API Docs: https://openrouter.io/docs/api/chat

---

**Status**: ✅ Configurado com suporte a 10 idiomas + Japonês
**Última atualização**: 2025-10-23
