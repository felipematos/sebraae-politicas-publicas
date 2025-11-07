# Correções da API OpenRouter - 2025-11-06

## Problema Identificado

Durante a reanálise das fontes na Fase 1 de Pesquisa, foram detectados **4.678 erros HTTP 405** causados por modelos LLM inválidos na configuração da OpenRouter API.

### Causa Raiz

Os modelos da família Grok foram **renomeados** pela OpenRouter:
- ❌ Antigo: `xai/grok-4-fast`
- ✅ Novo: `x-ai/grok-4-fast` (com hífen)

O erro ocorreu porque o código estava usando os IDs antigos dos modelos, que não existem mais na API da OpenRouter.

### Impacto

- **4.678 erros** durante reanálise de fontes
- Fallback automático para classificação heurística (menos precisa)
- Logs truncados dificultando diagnóstico
- 8.842 análises em cache usando modelo antigo (mas ainda válidas)

## Correções Implementadas

### 1. Atualização dos Modelos (`app/integracao/openrouter_api.py`)

**Modelos Especializados:**
```python
MODELOS_ESPECIALIZADOS = {
    "avaliacao": "x-ai/grok-4-fast",        # Corrigido
    "traducao": "meta-llama/llama-3.3-70b-instruct:free",  # Atualizado para 3.3
    "deteccao_idioma": "x-ai/grok-4-fast",  # Corrigido
}
```

**Modelos de Avaliação Profunda:**
- `x-ai/grok-4` (preço corrigido: $0.003/1K tokens)
- `x-ai/grok-4-fast` (preço corrigido: $0.0002/1K tokens)

**Todos os fallbacks** também foram atualizados para usar o ID correto.

### 2. Melhoria no Sistema de Logging

**Antes:**
```python
print(f"[ANÁLISE] ✗ Erro ao analisar fonte: {str(e)[:100]}")  # Truncado!
```

**Depois:**
```python
# Log melhorado com contexto completo
erro_msg = str(e)
print(f"[ANÁLISE] ✗ Erro ao analisar fonte: {erro_msg}")
print(f"[ANÁLISE]   → Título: {titulo[:80] if titulo else 'N/A'}")
print(f"[ANÁLISE]   → Modelo usado: {modelo}")
if len(erro_msg) > 200:
    print(f"[ANÁLISE]   → Detalhes completos: {erro_msg}")
```

**Locais corrigidos:**
- Detecção de idioma
- Avaliação de qualidade
- Tradução com detecção
- Tradução simples
- Avaliação profunda
- Consultas gerais

### 3. Testes Realizados

✅ **Detecção de Idioma:** Funcionando
```
Input: "Este é um texto em português para testar."
Output: pt
```

✅ **Análise de Fonte:** Funcionando
```
Input: "Política Nacional de Inovação Brasileira"
Output: {
  "tipo_fonte": "governamental",
  "tem_implementacao": False,
  "tem_metricas": True,
  "confianca": 1.0
}
```

✅ **Tradução:** Funcionando

## Modelos Disponíveis (Verificado em 2025-11-06)

### Família Grok (X.AI)
- `x-ai/grok-4-fast` - $0.0002/1K tokens, 2M contexto
- `x-ai/grok-4` - $0.003/1K tokens, 256K contexto
- `x-ai/grok-3-mini` - $0.0003/1K tokens, 131K contexto
- `x-ai/grok-code-fast-1` - $0.0002/1K tokens, 256K contexto

### Modelos Gratuitos Recomendados
- `google/gemini-2.0-flash-exp:free` - **1M contexto!**
- `meta-llama/llama-3.3-70b-instruct:free` - 131K contexto
- `deepseek/deepseek-chat-v3.1:free` - 163K contexto
- `qwen/qwen3-coder:free` - 262K contexto

## Cache de Análises

**Status Atual:**
- Total: 8.842 análises em cache
- Modelo usado: `xai/grok-4-fast` (antigo)
- Status: **Válidas** (foram criadas quando o modelo ainda funcionava)

**Decisão:** Manter o cache existente, pois as análises são válidas. Novas análises usarão o modelo correto.

## Próximos Passos Recomendados

1. ✅ Modelos corrigidos e testados
2. ✅ Logging melhorado
3. ⏳ Monitorar próximas análises para confirmar que não há mais erros
4. ⏳ Considerar migração gradual do cache (opcional)

## Informações Técnicas

**Arquivo modificado:** `app/integracao/openrouter_api.py`
**Linhas alteradas:** 33-35, 42-63, 150, 161, 227-231, 382, 457, 613-619, 985, 1157, 1274
**Testes executados:** 3/3 passando
**Data:** 2025-11-06
**Responsável:** Claude Code (via Felipe Matos)

## Lições Aprendidas

1. **Sempre verificar mudanças na API externa:** Provedores como OpenRouter podem renomear modelos
2. **Não truncar logs de erro:** Mensagens completas são essenciais para diagnóstico
3. **Implementar testes de integração:** Detectar problemas antes de produção
4. **Manter preços atualizados:** Revisar custos regularmente
