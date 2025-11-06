# Sistema Inteligente de Gerenciamento de Modelos LLM

**Atualizado em:** 2025-11-06

## 📋 Visão Geral

Sistema completo de gerenciamento de modelos LLM da OpenRouter com:
- ✅ Atualização automática diária dos modelos e preços
- ✅ Sistema de scoring para escolha do melhor modelo por tarefa
- ✅ Fallback inteligente em caso de falha
- ✅ Cálculo preciso de custos e estimativas
- ✅ 338 modelos disponíveis (45 gratuitos)

## 🏗️ Arquitetura

### Componentes Principais

```
app/llm/
├── modelos_openrouter.json          # Base de dados de modelos (auto-atualizada)
├── processar_modelos_openrouter.py  # Script de atualização dos modelos
├── gerenciador_modelos.py           # Gerenciador centralizado
├── chamador_llm_inteligente.py      # Sistema de fallback inteligente
└── README.md                         # Esta documentação

app/integracao/
└── openrouter_api_v2.py             # Cliente OpenRouter melhorado
```

## 📊 Estrutura de Dados

### Arquivo `modelos_openrouter.json`

```json
{
  "metadata": {
    "ultima_atualizacao": "2025-11-06T13:26:28",
    "total_modelos": 338
  },
  "categorias": {
    "free": [...],           // 45 modelos gratuitos
    "ultra_economico": [...], // 290 modelos (<$0.0001/1K)
    "economico": [...],       // 2 modelos (<$0.0005/1K)
    "balanceado": [...]       // 1 modelo (<$0.002/1K)
  },
  "top_models": {
    "traducao": [...],        // Top 10 para tradução
    "analise": [...],         // Top 10 para análise
    "velocidade": [...],      // Top 10 mais rápidos
    "custo_beneficio": [...]  // Top 10 custo-benefício
  },
  "todos_modelos": [...]      // Lista completa
}
```

### Metadados de Cada Modelo

```json
{
  "id": "meta-llama/llama-3.1-70b-instruct:free",
  "name": "Meta: Llama 3.1 70B Instruct (free)",
  "description": "...",
  "context_length": 131072,
  "max_completion_tokens": 65536,
  "pricing": {
    "prompt": 0.0,
    "completion": 0.0,
    "total_per_1k": 0.0,
    "categoria": "free"
  },
  "scores": {
    "traducao": 10.0,         // 0.0-10.0
    "analise": 8.5,           // 0.0-10.0
    "velocidade": 5.0,        // 0.0-10.0
    "custo_beneficio": 10.0   // 0.0-10.0
  },
  "architecture": {...},
  "fallback_similar": [...]    // Modelos similares para fallback
}
```

## 🎯 Sistema de Scoring

### Score de Tradução (0.0-10.0)
Critérios:
- Modelos conhecidos por qualidade multilíngue (+2.0)
- Context window grande (+1.5)
- Modelos 70B+ (+0.7)
- Palavra "instruct" no nome (+0.5)

**Top 5 Gratuitos:**
1. Mistral Small 3.1 24B - 10.0/10
2. Llama 3.3 70B Instruct - 10.0/10
3. Llama 3.2 3B Instruct - 10.0/10
4. Qwen2.5 72B Instruct - 10.0/10
5. Hermes 3 405B Instruct - 10.0/10

### Score de Análise (0.0-10.0)
Critérios:
- Modelos premium de raciocínio (+3.0)
- Termos "reasoning", "analysis" (+1.5)
- Context window >200K (+2.0)
- Modelos 405B+ (+1.5)

**Top 5 Custo-Benefício:**
1. Amazon Nova Premier - 10.0/10 ($0.000015/1K)
2. Perplexity Sonar Pro - 10.0/10 ($0.000018/1K)
3. Mistral Voxtral Small - 10.0/10 (gratuito)
4. GPT-OSS Safeguard - 10.0/10 (gratuito)
5. Nemotron Nano 12B - 10.0/10 (gratuito)

### Score de Velocidade (0.0-10.0)
Critérios:
- Palavras "fast", "turbo", "flash" (+3.0)
- Modelos 7B-8B (+2.0)
- Providers rápidos (Gemini Flash, GPT-4o-mini) (+2.0)

### Score de Custo-Benefício (0.0-10.0)
Fórmula: `(qualidade_média / preço_normalizado) * 10`
- Modelos gratuitos de qualidade têm score máximo
- Modelos pagos são avaliados por qualidade/preço

## 🚀 Uso

### 1. Gerenciador de Modelos

```python
from app.llm.gerenciador_modelos import obter_gerenciador

# Obter instância
gerenciador = obter_gerenciador()

# Buscar modelo específico
modelo = gerenciador.obter_modelo_por_id("meta-llama/llama-3.1-70b-instruct:free")

# Obter melhores para tradução (gratuitos)
melhores = gerenciador.obter_melhores_para_tarefa(
    tarefa="traducao",
    limite=5,
    categoria_preco="free"
)

# Obter modelos por faixa de preço
baratos = gerenciador.obter_modelos_por_faixa_preco(
    preco_max=0.0001,
    tarefa="analise",
    limite=10
)

# Obter fallbacks para um modelo
fallbacks = gerenciador.obter_fallback_para_modelo(
    model_id="anthropic/claude-3-sonnet",
    max_diferenca_preco=0.002,
    limite=5
)

# Forçar atualização dos modelos
gerenciador.forcar_atualizacao()
```

### 2. Chamador LLM Inteligente

```python
from app.llm.chamador_llm_inteligente import ChamadorLLMInteligente

# Criar chamador com fallback automático
async def meu_chamador_base(model_id: str, prompt: str, **kwargs):
    # Sua implementação de chamada ao LLM
    pass

chamador = ChamadorLLMInteligente(
    chamador_base=meu_chamador_base,
    max_tentativas=3,  # Modelo principal + 2 fallbacks
    timeout_por_tentativa=30.0
)

# Chamar com fallback automático
resultado = await chamador.chamar_com_fallback(
    model_id="meta-llama/llama-3.1-70b-instruct:free",
    prompt="Traduza para português: Hello World",
    categoria_preco_max="free"
)

if resultado["sucesso"]:
    print(f"Resposta: {resultado['resposta']}")
    print(f"Modelo usado: {resultado['modelo_usado']}")
    print(f"Tentativas: {resultado['tentativas']}")
    print(f"Custo: ${resultado['custo_estimado']:.6f}")
else:
    print(f"Erro: {resultado['erro']}")

# Ou usar seleção automática do melhor modelo
resultado = await chamador.chamar_modelo_ideal(
    prompt="Analise este documento...",
    tarefa="analise",
    categoria_preco="balanceado"
)

# Obter métricas
metricas = chamador.obter_metricas()
print(f"Taxa de sucesso: {metricas['taxa_sucesso']*100:.1f}%")
print(f"Custo total: ${metricas['custo_total_estimado_usd']:.6f}")
```

### 3. Cliente OpenRouter V2

```python
from app.integracao.openrouter_api_v2 import OpenRouterClientV2

async with OpenRouterClientV2() as client:
    # Tradução com fallback automático
    traducao = await client.traduzir_texto(
        texto="Innovation policy frameworks",
        idioma_destino="pt",
        categoria_preco="free"
    )

    # Detectar idioma
    idioma = await client.detectar_idioma("Este é um texto em português")

    # Analisar fonte
    analise = await client.analisar_fonte(
        titulo="Policy Framework for Innovation",
        descricao="...",
        url="https://...",
        modo="balanceado"  # gratuito, balanceado, premium
    )

    # Estimativa de custos
    estimativa = client.obter_custos_estimados(
        num_traducoes=100,
        categoria_preco="free"
    )
    print(f"Custo estimado: R$ {estimativa['custo_brl']:.4f}")
    print(f"Tempo estimado: {estimativa['tempo_estimado_minutos']} min")

    # Estatísticas de uso
    stats = client.obter_estatisticas()
```

## 🔄 Atualização Automática

O sistema detecta automaticamente quando os dados estão desatualizados (>24h) e atualiza via API:

```python
# Atualização automática no próximo carregamento
gerenciador = obter_gerenciador()  # Verifica e atualiza se necessário

# Ou forçar atualização imediata
gerenciador.forcar_atualizacao()
```

### Processo de Atualização

1. **Busca API OpenRouter** → `/api/v1/models`
2. **Processa modelos** → Adiciona scores e metadados
3. **Salva JSON** → `modelos_openrouter.json`
4. **Atualiza cache** → Cache em memória por 1h

## 💰 Categorias de Preço

| Categoria | Faixa de Preço | Quantidade | Uso Recomendado |
|-----------|----------------|------------|-----------------|
| **free** | $0.00 | 45 | Traduções em massa |
| **ultra_economico** | <$0.0001/1K | 290 | Análises simples |
| **economico** | <$0.0005/1K | 2 | Análises médias |
| **balanceado** | <$0.002/1K | 1 | Análises complexas |
| **premium** | <$0.01/1K | 0 | Não disponível |
| **ultra_premium** | >$0.01/1K | 0 | Não disponível |

## 🎓 Exemplos de Uso Real

### Exemplo 1: Tradução em Lote

```python
from app.integracao.openrouter_api_v2 import OpenRouterClientV2

async def traduzir_lote(textos: list[str]):
    async with OpenRouterClientV2() as client:
        # Estimar custo primeiro
        estimativa = client.obter_custos_estimados(
            num_traducoes=len(textos),
            categoria_preco="free"
        )

        print(f"Custo: R$ {estimativa['custo_brl']:.4f}")
        print(f"Tempo: ~{estimativa['tempo_estimado_minutos']} min")

        # Confirmar e executar
        traducoes = []
        for texto in textos:
            traducao = await client.traduzir_texto(
                texto,
                categoria_preco="free"
            )
            traducoes.append(traducao)

        return traducoes
```

### Exemplo 2: Análise com Fallback Inteligente

```python
from app.llm.chamador_llm_inteligente import ChamadorLLMInteligente
from app.integracao.openrouter_api_v2 import OpenRouterClientV2

async def analisar_com_fallback(documentos: list[dict]):
    client = OpenRouterClientV2()
    chamador = ChamadorLLMInteligente(
        chamador_base=client._chamar_modelo_base,
        max_tentativas=3
    )

    resultados = []
    for doc in documentos:
        prompt = f"Analise: {doc['texto']}"

        resultado = await chamador.chamar_modelo_ideal(
            prompt=prompt,
            tarefa="analise",
            categoria_preco="economico"
        )

        if resultado["sucesso"]:
            resultados.append({
                "documento_id": doc["id"],
                "analise": resultado["resposta"],
                "modelo": resultado["modelo_usado"],
                "custo": resultado["custo_estimado"]
            })

    # Métricas finais
    metricas = chamador.obter_metricas()
    print(f"Análises: {metricas['total_sucesso']}/{metricas['total_chamadas']}")
    print(f"Fallbacks: {metricas['total_fallbacks']}")
    print(f"Custo total: R$ {metricas['custo_total_estimado_brl']:.2f}")

    return resultados
```

## 🔧 Manutenção

### Atualização Manual

```bash
cd "app/llm"

# 1. Buscar modelos da API
curl -X GET "https://openrouter.ai/api/v1/models" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -o /tmp/openrouter_models_raw.json

# 2. Formatar JSON
python3 -m json.tool /tmp/openrouter_models_raw.json > /tmp/openrouter_models.json

# 3. Processar com metadados
python3 processar_modelos_openrouter.py \
  /tmp/openrouter_models.json \
  modelos_openrouter.json
```

### Verificar Status

```python
from app.llm.gerenciador_modelos import obter_gerenciador

gerenciador = obter_gerenciador()
stats = gerenciador.obter_estatisticas()

print(f"Total de modelos: {stats['total_modelos']}")
print(f"Última atualização: {stats['ultima_atualizacao']}")
print(f"Distribuição por categoria: {stats['por_categoria']}")
print("\nTop 5 Custo-Benefício:")
for modelo in stats['top_custo_beneficio']:
    print(f"  - {modelo['name']}: {modelo['score']}/10")
```

## 📈 Benefícios

### Antes (Sistema Antigo)
- ❌ Modelos hardcoded no código
- ❌ Preços desatualizados
- ❌ Fallback manual e limitado
- ❌ Difícil adicionar novos modelos
- ❌ Sem métricas de uso

### Agora (Sistema Novo)
- ✅ 338 modelos disponíveis automaticamente
- ✅ Preços sempre atualizados (diariamente)
- ✅ Fallback inteligente automático
- ✅ Scoring para escolha otimizada
- ✅ Métricas detalhadas de custo/uso
- ✅ Fácil migração gradual

## 🔐 Segurança

- API keys armazenadas em `.env` (não versionado)
- Cache local do JSON (não versionado)
- Sem dados sensíveis no repositório
- Timeouts configuráveis para evitar custos excessivos

## 📝 Notas Importantes

1. **Compatibilidade**: O sistema mantém compatibilidade com o código antigo. Migração pode ser gradual.

2. **Atualização automática**: Ocorre automaticamente no primeiro uso após 24h da última atualização.

3. **Fallback**: Sistema tenta até 3 modelos automaticamente, respeitando faixa de preço.

4. **Scores**: Baseados em heurísticas e benchmarks conhecidos. Podem ser ajustados em `processar_modelos_openrouter.py`.

5. **Cache**: Gerenciador mantém cache em memória por 1h para performance.

## 🐛 Troubleshooting

### Erro: "Arquivo de modelos não encontrado"
```bash
python3 app/llm/processar_modelos_openrouter.py
```

### Erro: "OPENROUTER_API_KEY não encontrada"
Verifique arquivo `.env`:
```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

### Modelos retornando erro 429 (Rate Limit)
Use modelos pagos ou aguarde reset do rate limit.

### Atualização automática não funcionando
Forçar manualmente:
```python
gerenciador.forcar_atualizacao()
```

## 📚 Referências

- [OpenRouter API](https://openrouter.ai/docs)
- [Documentação de Modelos](https://openrouter.ai/models)
- [Preços Atualizados](https://openrouter.ai/models?pricing=true)

---

**Última atualização:** 2025-11-06
**Versão:** 1.0
**Autor:** Sistema Sebrae Nacional
