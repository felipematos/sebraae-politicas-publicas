# Instruções para Implementação do Frontend - Fase II de Boas Práticas

## ✅ Backend Implementado

### Banco de Dados
- ✅ Campo `confidence_score` (0-100) adicionado à tabela `boas_praticas`

### API Endpoints
- ✅ `GET /api/boas-praticas/fase2/modelos-disponiveis` - Lista modelos LLM disponíveis
- ✅ `GET /api/boas-praticas/fase2/estimar-custo/{falha_id}?modelo=` - Estima custo/tempo para uma falha
- ✅ `POST /api/boas-praticas/fase2/analisar/{falha_id}?modelo=&reprocessar=` - Analisa falha (já existia, atualizado)
- ✅ `POST /api/boas-praticas/fase2/analisar-tudo?modelo=&reprocessar=` - Analisa todas as falhas
- ✅ `GET /api/boas-praticas/fase2/estimar-custo-tudo?modelo=` - Estima custo/tempo total

### Modelos Suportados
**Gratuitos (Recomendados):**
- `google/gemini-2.0-flash-exp:free` - **PADRÃO** - Rápido, grande contexto, grátis
- `meta-llama/llama-3.3-70b-instruct:free` - Excelente raciocínio, grátis
- `google/gemma-2-27b-it:free` - Compacto e eficiente, grátis

**Pagos (Premium):**
- `google/gemini-pro-1.5` - 2M tokens de contexto ($0.00125/1K)
- `anthropic/claude-3.5-sonnet` - Melhor raciocínio ($0.003/1K)
- `openai/gpt-4o` - Excelente análise ($0.005/1K)

---

## 🎨 Mudanças Necessárias no Frontend (static/index.html)

### 1. Adicionar Variáveis Alpine.js (Seção `data()`)

Localize a seção `data() {` do Alpine.js e adicione:

```javascript
// Fase II - Boas Práticas - Configuração de Modelo
modelo_llm_fase2: {
    id: 'google/gemini-2.0-flash-exp:free',
    nome: 'Google Gemini 2.0 Flash (Grátis)',
    custo_por_1k: 0.0,
    categoria: 'free'
},
modelos_disponiveis_fase2: [],
modal_config_modelo_aberto: false,
modal_confirmacao_analise_aberto: false,
modal_confirmacao_tudo_aberto: false,
estimativa_custo_atual: null,
estimativa_custo_tudo: null,
processando_tudo: false,
```

### 2. Modificar Cabeçalho da Fase II

Localize `<!-- Fase II: Análise com IA -->` (~linha 3201) e substitua o bloco de controles por:

```html
<!-- Fase II: Análise com IA -->
<div x-show="boas_praticas_subfase === 2" class="space-y-4">
    <!-- Controles -->
    <div class="bg-white rounded-lg shadow p-6">
        <div class="flex justify-between items-start mb-4">
            <div>
                <h3 class="text-xl font-bold mb-2">Fase II - Detecção de Boas Práticas</h3>
                <p class="text-sm text-gray-600">Clique em "Analisar" para executar a detecção de boas práticas com IA para cada falha.</p>
                <!-- Modelo atual -->
                <div class="mt-2 text-xs text-gray-500">
                    <span class="font-medium">Modelo configurado:</span>
                    <span x-text="modelo_llm_fase2.nome"></span>
                    <span x-show="modelo_llm_fase2.custo_por_1k === 0.0" class="ml-2 bg-green-100 text-green-800 px-2 py-0.5 rounded">GRÁTIS</span>
                </div>
            </div>
            <div class="flex gap-3">
                <button @click="abrir_modal_config_modelo()"
                        class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                    </svg>
                    Configurar Modelo
                </button>
                <button @click="confirmar_analisar_tudo()"
                        :disabled="falhas_fase2.length === 0 || processando_tudo"
                        class="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:from-gray-400 disabled:to-gray-500 text-white px-6 py-2 rounded-lg font-medium transition-all shadow-lg hover:shadow-xl flex items-center gap-2">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                    </svg>
                    <span x-show="!processando_tudo">Analisar Tudo</span>
                    <span x-show="processando_tudo">Processando...</span>
                </button>
            </div>
        </div>

        <!-- Status -->
        <div x-show="fase2_status" class="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p class="text-sm text-blue-800" x-text="fase2_status"></p>
        </div>
    </div>
```

### 3. Adicionar Modal de Configuração de Modelo

Adicione antes do fechamento do `body` (próximo aos outros modais):

```html
<!-- Modal: Configurar Modelo LLM Fase II -->
<div x-show="modal_config_modelo_aberto"
     x-cloak
     class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
     @click.self="modal_config_modelo_aberto = false">
    <div class="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <!-- Header -->
        <div class="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-6 py-4 rounded-t-lg">
            <h2 class="text-2xl font-bold">⚙️ Configurar Modelo LLM - Fase II</h2>
            <p class="text-sm mt-1 text-indigo-100">Escolha o modelo para detecção de boas práticas</p>
        </div>

        <!-- Body -->
        <div class="p-6 space-y-6">
            <!-- Modelos Gratuitos -->
            <div>
                <h3 class="text-lg font-bold mb-3 text-green-700">🆓 Modelos Gratuitos (Recomendados)</h3>
                <div class="space-y-3">
                    <template x-for="modelo in modelos_disponiveis_fase2.filter(m => m.categoria === 'free')" :key="modelo.id">
                        <div @click="selecionar_modelo_fase2(modelo)"
                             :class="modelo_llm_fase2.id === modelo.id ? 'ring-2 ring-green-500 bg-green-50' : 'hover:bg-gray-50'"
                             class="border rounded-lg p-4 cursor-pointer transition-all">
                            <div class="flex items-start justify-between">
                                <div class="flex-1">
                                    <div class="flex items-center gap-2">
                                        <h4 class="font-bold" x-text="modelo.nome"></h4>
                                        <span x-show="modelo.recomendado" class="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded">⭐ RECOMENDADO</span>
                                    </div>
                                    <p class="text-sm text-gray-600 mt-1" x-text="modelo.descricao"></p>
                                    <div class="flex gap-4 mt-2 text-xs text-gray-500">
                                        <span class="bg-green-100 text-green-800 px-2 py-1 rounded font-bold">GRÁTIS</span>
                                    </div>
                                </div>
                                <div x-show="modelo_llm_fase2.id === modelo.id">
                                    <svg class="w-6 h-6 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                                    </svg>
                                </div>
                            </div>
                        </div>
                    </template>
                </div>
            </div>

            <!-- Modelos Premium -->
            <div>
                <h3 class="text-lg font-bold mb-3 text-purple-700">💎 Modelos Premium</h3>
                <div class="space-y-3">
                    <template x-for="modelo in modelos_disponiveis_fase2.filter(m => m.categoria === 'premium')" :key="modelo.id">
                        <div @click="selecionar_modelo_fase2(modelo)"
                             :class="modelo_llm_fase2.id === modelo.id ? 'ring-2 ring-purple-500 bg-purple-50' : 'hover:bg-gray-50'"
                             class="border rounded-lg p-4 cursor-pointer transition-all">
                            <div class="flex items-start justify-between">
                                <div class="flex-1">
                                    <div class="flex items-center gap-2">
                                        <h4 class="font-bold" x-text="modelo.nome"></h4>
                                        <span x-show="modelo.recomendado" class="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded">⭐ RECOMENDADO</span>
                                    </div>
                                    <p class="text-sm text-gray-600 mt-1" x-text="modelo.descricao"></p>
                                    <div class="flex gap-4 mt-2 text-xs text-gray-500">
                                        <span class="bg-purple-100 text-purple-800 px-2 py-1 rounded">
                                            $<span x-text="modelo.custo_por_1k.toFixed(4)"></span>/1K tokens
                                        </span>
                                    </div>
                                </div>
                                <div x-show="modelo_llm_fase2.id === modelo.id">
                                    <svg class="w-6 h-6 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                                    </svg>
                                </div>
                            </div>
                        </div>
                    </template>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="bg-gray-50 px-6 py-4 rounded-b-lg flex justify-end gap-3">
            <button @click="modal_config_modelo_aberto = false"
                    class="px-6 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg font-medium transition-colors">
                Fechar
            </button>
        </div>
    </div>
</div>
```

### 4. Adicionar Modal de Confirmação "Analisar Tudo"

```html
<!-- Modal: Confirmação Analisar Tudo -->
<div x-show="modal_confirmacao_tudo_aberto"
     x-cloak
     class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
     @click.self="modal_confirmacao_tudo_aberto = false">
    <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full">
        <!-- Header -->
        <div class="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-6 py-4 rounded-t-lg">
            <h2 class="text-2xl font-bold">⚡ Analisar Todas as Falhas</h2>
        </div>

        <!-- Body -->
        <div class="p-6 space-y-4">
            <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p class="text-yellow-800 font-medium">⚠️ Atenção: Esta ação irá processar todas as falhas priorizadas.</p>
            </div>

            <!-- Estimativas -->
            <div x-show="estimativa_custo_tudo" class="space-y-3">
                <div class="grid grid-cols-2 gap-4">
                    <div class="bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200 rounded-lg p-4">
                        <div class="text-sm text-gray-600">Total de Falhas</div>
                        <div class="text-2xl font-bold text-purple-700" x-text="estimativa_custo_tudo?.total_falhas || 0"></div>
                    </div>
                    <div class="bg-gradient-to-br from-blue-50 to-cyan-50 border border-blue-200 rounded-lg p-4">
                        <div class="text-sm text-gray-600">Tempo Estimado</div>
                        <div class="text-2xl font-bold text-blue-700" x-text="estimativa_custo_tudo?.tempo_total_formatado || '~0s'"></div>
                    </div>
                </div>

                <div class="bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-lg p-4">
                    <div class="flex justify-between items-center">
                        <div>
                            <div class="text-sm text-gray-600">Custo Estimado</div>
                            <div class="text-3xl font-bold text-green-700" x-text="estimativa_custo_tudo?.custo_total_formatado || 'GRÁTIS'"></div>
                        </div>
                        <div x-show="estimativa_custo_tudo?.is_gratuito" class="bg-green-600 text-white px-4 py-2 rounded-lg font-bold text-lg">
                            🎉 GRÁTIS
                        </div>
                    </div>
                </div>

                <div class="bg-gray-50 border border-gray-200 rounded-lg p-3">
                    <div class="text-xs text-gray-600">Modelo:</div>
                    <div class="font-medium text-gray-800" x-text="modelo_llm_fase2.nome"></div>
                </div>
            </div>

            <div x-show="!estimativa_custo_tudo" class="text-center py-4">
                <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
                <p class="text-sm text-gray-600 mt-2">Calculando estimativas...</p>
            </div>
        </div>

        <!-- Footer -->
        <div class="bg-gray-50 px-6 py-4 rounded-b-lg flex justify-end gap-3">
            <button @click="modal_confirmacao_tudo_aberto = false"
                    class="px-6 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg font-medium transition-colors">
                Cancelar
            </button>
            <button @click="executar_analisar_tudo()"
                    :disabled="!estimativa_custo_tudo"
                    class="px-6 py-2 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:from-gray-400 disabled:to-gray-500 text-white rounded-lg font-medium transition-all shadow-lg">
                Confirmar e Analisar
            </button>
        </div>
    </div>
</div>
```

### 5. Adicionar Funções JavaScript

Adicione na seção de métodos do Alpine.js:

```javascript
// ===== FASE II - CONFIGURAÇÃO DE MODELO =====

async abrir_modal_config_modelo() {
    try {
        // Carregar modelos disponíveis
        const res = await fetch('/api/boas-praticas/fase2/modelos-disponiveis');
        const data = await res.json();
        this.modelos_disponiveis_fase2 = data.modelos;

        // Abrir modal
        this.modal_config_modelo_aberto = true;
    } catch (error) {
        console.error('Erro ao carregar modelos:', error);
        alert('Erro ao carregar lista de modelos');
    }
},

selecionar_modelo_fase2(modelo) {
    this.modelo_llm_fase2 = modelo;
    console.log('Modelo selecionado:', modelo.nome);
},

async confirmar_analisar_tudo() {
    try {
        // Buscar estimativa de custo
        this.modal_confirmacao_tudo_aberto = true;
        this.estimativa_custo_tudo = null;

        const res = await fetch(`/api/boas-praticas/fase2/estimar-custo-tudo?modelo=${encodeURIComponent(this.modelo_llm_fase2.id)}`);
        const data = await res.json();
        this.estimativa_custo_tudo = data;
    } catch (error) {
        console.error('Erro ao estimar custo:', error);
        this.modal_confirmacao_tudo_aberto = false;
        alert('Erro ao estimar custo da análise');
    }
},

async executar_analisar_tudo() {
    try {
        this.modal_confirmacao_tudo_aberto = false;
        this.processando_tudo = true;
        this.fase2_status = `Processando ${this.estimativa_custo_tudo.total_falhas} falhas com ${this.modelo_llm_fase2.nome}...`;

        const res = await fetch(`/api/boas-praticas/fase2/analisar-tudo?modelo=${encodeURIComponent(this.modelo_llm_fase2.id)}`, {
            method: 'POST'
        });

        const resultado = await res.json();

        if (resultado.processadas > 0) {
            this.fase2_status = `✅ ${resultado.mensagem} (${resultado.processadas} processadas, ${resultado.com_erro} erros)`;

            // Recarregar lista
            await this.carregar_falhas_fase2();
        } else {
            this.fase2_status = '❌ Nenhuma falha processada';
        }
    } catch (error) {
        console.error('Erro ao processar em lote:', error);
        this.fase2_status = '❌ Erro ao processar falhas em lote';
    } finally {
        this.processando_tudo = false;
    }
},
```

### 6. Modificar Função de Análise Individual

Localize a função `analisar_falha_fase2()` e modifique para incluir o modelo:

```javascript
async analisar_falha_fase2(falha_id, reprocessar = false) {
    try {
        // Buscar estimativa primeiro
        const estimativa_res = await fetch(`/api/boas-praticas/fase2/estimar-custo/${falha_id}?modelo=${encodeURIComponent(this.modelo_llm_fase2.id)}`);
        const estimativa = await estimativa_res.json();

        // Confirmar com usuário
        const custo_msg = estimativa.is_gratuito ? 'GRÁTIS' : estimativa.custo_estimado_formatado;
        const confirmar = confirm(
            `Analisar Falha #${falha_id}\n\n` +
            `Modelo: ${this.modelo_llm_fase2.nome}\n` +
            `Fontes: ${estimativa.num_fontes}\n` +
            `Tempo estimado: ${estimativa.tempo_estimado_formatado}\n` +
            `Custo estimado: ${custo_msg}\n\n` +
            `Deseja continuar?`
        );

        if (!confirmar) return;

        this.fase2_status = `Analisando falha #${falha_id} com ${this.modelo_llm_fase2.nome}...`;

        const res = await fetch(`/api/boas-praticas/fase2/analisar/${falha_id}?reprocessar=${reprocessar}&modelo=${encodeURIComponent(this.modelo_llm_fase2.id)}`, {
            method: 'POST'
        });

        const resultado = await res.json();

        if (resultado.total_praticas > 0) {
            this.fase2_status = `✅ ${resultado.total_praticas} boas práticas identificadas para falha #${falha_id}`;
            await this.carregar_falhas_fase2();
        } else {
            this.fase2_status = `ℹ️ Nenhuma boa prática identificada para falha #${falha_id}`;
        }
    } catch (error) {
        console.error('Erro ao analisar:', error);
        this.fase2_status = `❌ Erro ao analisar falha #${falha_id}`;
    }
},
```

---

## 📊 Como Funciona

### Score de Confiança (0-100)

Cada boa prática recebe um score baseado em:
- **40%** - Evidências de implementação real
- **30%** - Métricas/resultados quantificáveis
- **20%** - Relevância para a falha específica
- **10%** - Qualidade e credibilidade da fonte

### Interpretação dos Scores:
- **90-100**: Prática comprovada com métricas claras e casos de sucesso
- **70-89**: Prática implementada com resultados positivos
- **50-69**: Prática mencionada com evidências parciais
- **30-49**: Prática citada sem evidências robustas
- **0-29**: Prática teórica ou com implementação duvidosa

---

## 🧪 Como Testar

1. **Iniciar o servidor:**
   ```bash
   python3 -m uvicorn app.main:app --reload
   ```

2. **Acessar a interface:**
   - Ir para Fase 4: Boas Práticas
   - Clicar na aba "Fase II - Detecção de Boas Práticas"

3. **Testar configuração de modelo:**
   - Clicar em "Configurar Modelo"
   - Selecionar um modelo diferente
   - Verificar que o nome aparece no cabeçalho

4. **Testar análise individual:**
   - Clicar em "Analisar" em uma falha
   - Verificar que o diálogo mostra estimativa de custo/tempo
   - Confirmar e aguardar processamento

5. **Testar "Analisar Tudo":**
   - Clicar em "Analisar Tudo"
   - Verificar estimativa total
   - Confirmar e acompanhar progresso

6. **Verificar scores:**
   - Após análise, verificar que cada boa prática tem um `confidence_score`
   - Verificar que scores estão entre 0-100

---

## 📝 Próximos Passos

Após implementar o frontend:

1. **Exibir confidence_score** na interface de visualização de boas práticas
2. **Adicionar filtro por score** (ex: "Apenas práticas com score > 70")
3. **Adicionar indicador visual** (ex: estrelas, cores) baseado no score
4. **Gráficos de distribuição** de scores por pillar

---

## 🐛 Troubleshooting

### Modelo não encontrado
- Verificar que o ID do modelo está correto
- Usar endpoint `/api/boas-praticas/fase2/modelos-disponiveis` para listar modelos válidos

### Erro 500 ao analisar
- Verificar logs do servidor (`server.log`)
- Verificar que Jina API e OpenRouter API estão configuradas
- Verificar que há fontes disponíveis para a falha

### Confidence_score sempre 0
- Verificar que o modelo está retornando o campo `confidence_score` no JSON
- Verificar logs do AnalisadorBoasPraticas
- Testar prompt manualmente com modelo escolhido

---

**Autor:** Claude Code
**Data:** 2025-11-08
**Versão:** 1.0.0
