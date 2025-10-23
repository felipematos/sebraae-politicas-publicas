/**
 * Dashboard Alpine.js
 * Aplicacao interativa para visualizar dados de pesquisa
 */

function dashboardApp() {
    return {
        // Estado
        aba_ativa: 'falhas',
        ativo: true,
        falhas: [],
        resultados: [],
        stats: {
            total_falhas: 50,
            fila_pendente: 0,
            processadas: 0,
            total_resultados: 0,
            total_pendentes: 0,
            total_processando: 0,
            total_concluidas: 0,
            total_erros: 0
        },
        percentual_processamento: 0,
        status_pesquisa: {
            ativo: false,
            porcentagem: 0.0,
            mensagem: "Nenhuma pesquisa em progresso"
        },
        pesquisa_iniciando: false,
        pesquisa_pausada: false,
        modal_falha_aberta: false,
        falha_selecionada: null,
        resultados_falha_selecionada: [],
        modal_resultado_aberta: false,
        resultado_selecionado: null,
        filtro_score_min: 0.5,
        health_check_executando: false,
        health_check_resultado: null,
        search_channels: {},
        canais_ativos: 0,
        total_canais: 0,
        ferramentas_config: {
            perplexity: true,
            jina: true,
            tavily: true,
            serper: true,
            deep_research: true
        },
        salvando_config: false,

        // Inicializacao
        async init() {
            await this.carregar_falhas();
            await this.carregar_resultados();
            await this.carregar_canais();
            await this.carregar_ferramentas_config();
            await this.atualizar_stats();
            // Atualizar stats a cada 3 segundos quando pesquisa ativa, 10 segundos se inativa
            setInterval(() => this.atualizar_stats(), 3000);
        },

        // Carregar dados da API
        async carregar_falhas() {
            try {
                const response = await fetch('/api/falhas');
                if (response.ok) {
                    const dados = await response.json();
                    this.falhas = dados;
                } else {
                    console.error('Erro carregando falhas:', response.status);
                }
            } catch (erro) {
                console.error('Erro na requisicao:', erro);
            }
        },

        async carregar_resultados() {
            try {
                const response = await fetch('/api/resultados');
                if (response.ok) {
                    const dados = await response.json();
                    this.resultados = dados;
                } else {
                    console.error('Erro carregando resultados:', response.status);
                }
            } catch (erro) {
                console.error('Erro na requisicao:', erro);
            }
        },

        async atualizar_stats() {
            try {
                // Atualizar status de pesquisas em tempo real
                const res_status = await fetch('/api/pesquisas/status');
                if (res_status.ok) {
                    const status = await res_status.json();
                    this.status_pesquisa = status;
                    this.stats.total_pendentes = status.total_pendentes;
                    this.stats.total_processando = status.total_processando;
                    this.stats.total_concluidas = status.total_concluidas;
                    this.stats.total_erros = status.total_erros;
                    this.percentual_processamento = status.porcentagem;
                }

                // Atualizar falhas E somar total de resultados (não usar endpoint paginado)
                const res_falhas = await fetch('/api/falhas?limit=100');
                if (res_falhas.ok) {
                    const falhas = await res_falhas.json();
                    this.stats.total_falhas = falhas.length;
                    // Somar total_resultados de todas as falhas para sincronizar com a barra de progresso
                    this.stats.total_resultados = falhas.reduce((sum, falha) => sum + (falha.total_resultados || 0), 0);
                }

            } catch (erro) {
                console.error('Erro atualizando stats:', erro);
            }
        },

        // Iniciar pesquisas
        async iniciar_pesquisas(falhas_ids = null, idiomas = null, ferramentas = null) {
            if (this.pesquisa_iniciando) {
                alert('Pesquisa já em andamento ou iniciando...');
                return;
            }

            if (!confirm('Iniciar pesquisa em todas as falhas? Isto pode levar várias horas.')) {
                return;
            }

            this.pesquisa_iniciando = true;
            this.pesquisa_pausada = false;

            try {
                const payload = {
                    falhas_ids: falhas_ids,
                    idiomas: idiomas,
                    ferramentas: ferramentas,
                    prioridade: 0
                };

                const response = await fetch('/api/pesquisas/iniciar', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                if (response.ok) {
                    const resultado = await response.json();
                    alert(`Pesquisa iniciada!\n\nQueries criadas: ${resultado.queries_criadas}\nTempo estimado: ${resultado.tempo_estimado_minutos} minutos`);

                    // Atualizar stats imediatamente
                    await this.atualizar_stats();

                } else {
                    const erro = await response.json();
                    alert(`Erro ao iniciar pesquisa: ${erro.detail || 'Erro desconhecido'}`);
                }
            } catch (erro) {
                console.error('Erro ao iniciar pesquisa:', erro);
                alert(`Erro: ${erro.message}`);
            } finally {
                this.pesquisa_iniciando = false;
            }
        },

        // Pausar pesquisas
        async pausar_pesquisas() {
            if (!confirm('Pausar pesquisas em andamento?')) {
                return;
            }

            try {
                const response = await fetch('/api/pesquisas/pausar', {
                    method: 'POST'
                });

                if (response.ok) {
                    const resultado = await response.json();
                    alert(resultado.mensagem);
                    this.pesquisa_pausada = true;
                    await this.atualizar_stats();
                } else {
                    const erro = await response.json();
                    alert(`Erro: ${erro.detail || 'Erro desconhecido'}`);
                }
            } catch (erro) {
                console.error('Erro ao pausar pesquisas:', erro);
                alert(`Erro: ${erro.message}`);
            }
        },

        // Retomar pesquisas
        async retomar_pesquisas() {
            try {
                const response = await fetch('/api/pesquisas/retomar', {
                    method: 'POST'
                });

                if (response.ok) {
                    const resultado = await response.json();
                    alert(resultado.mensagem);
                    this.pesquisa_pausada = false;
                    await this.atualizar_stats();
                } else {
                    const erro = await response.json();
                    alert(`Erro: ${erro.detail || 'Erro desconhecido'}`);
                }
            } catch (erro) {
                console.error('Erro ao retomar pesquisas:', erro);
                alert(`Erro: ${erro.message}`);
            }
        },

        // Alternar pausa/retoma
        async alternar_pausa_retoma() {
            if (this.pesquisa_pausada) {
                await this.retomar_pesquisas();
            } else {
                await this.pausar_pesquisas();
            }
        },

        // Reiniciar pesquisas
        async reiniciar_pesquisas() {
            if (!confirm('ATENÇÃO: Isto vai limpar TODA a fila e todos os resultados encontrados até agora!\n\nTem certeza?')) {
                return;
            }

            try {
                const response = await fetch('/api/pesquisas/reiniciar', {
                    method: 'POST'
                });

                if (response.ok) {
                    const resultado = await response.json();
                    alert(resultado.mensagem);
                    await this.atualizar_stats();
                } else {
                    const erro = await response.json();
                    alert(`Erro: ${erro.detail || 'Erro desconhecido'}`);
                }
            } catch (erro) {
                console.error('Erro ao reiniciar pesquisas:', erro);
                alert(`Erro: ${erro.message}`);
            }
        },

        // Health Check
        async executar_health_check() {
            if (this.health_check_executando) {
                return;
            }

            this.health_check_executando = true;
            this.health_check_resultado = null;

            try {
                const response = await fetch('/api/health/check', {
                    method: 'POST'
                });

                if (response.ok) {
                    const resultado = await response.json();
                    this.health_check_resultado = resultado;

                    // Mostrar resumo no console
                    console.log('Health Check Resultado:', resultado);

                } else {
                    alert('Erro ao executar health check');
                }
            } catch (erro) {
                console.error('Erro ao executar health check:', erro);
                alert(`Erro: ${erro.message}`);
            } finally {
                this.health_check_executando = false;
            }
        },

        // Operacoes de CRUD
        async deletar_resultado(id) {
            if (!confirm('Tem certeza que deseja deletar este resultado?')) {
                return;
            }

            try {
                const response = await fetch(`/api/resultados/${id}`, {
                    method: 'DELETE'
                });

                if (response.ok || response.status === 204) {
                    // Remover da lista local
                    this.resultados = this.resultados.filter(r => r.id !== id);
                    console.log('Resultado deletado com sucesso');
                } else {
                    alert('Erro ao deletar resultado');
                }
            } catch (erro) {
                console.error('Erro na requisicao:', erro);
            }
        },

        async ver_detalhes_falha(falha_id) {
            try {
                const response = await fetch(`/api/falhas/${falha_id}/resultados`);
                if (response.ok) {
                    const dados = await response.json();
                    this.falha_selecionada = dados.falha;
                    this.resultados_falha_selecionada = dados.resultados;
                    this.modal_falha_aberta = true;
                } else {
                    console.error('Erro carregando detalhes:', response.status);
                }
            } catch (erro) {
                console.error('Erro na requisicao:', erro);
            }
        },

        abrir_detalhes_resultado(resultado) {
            this.resultado_selecionado = resultado;
            this.modal_resultado_aberta = true;
        },

        fechar_detalhes_resultado() {
            this.modal_resultado_aberta = false;
            this.resultado_selecionado = null;
        },

        // Filtros
        async filtrar_resultados() {
            try {
                const response = await fetch(`/api/resultados?score_min=${this.filtro_score_min}`);
                if (response.ok) {
                    const dados = await response.json();
                    this.resultados = dados;
                } else {
                    console.error('Erro filtrando:', response.status);
                }
            } catch (erro) {
                console.error('Erro na requisicao:', erro);
            }
        },

        // Gerenciamento de canais de pesquisa
        async carregar_canais() {
            try {
                const response = await fetch('/api/config/channels');
                if (response.ok) {
                    const dados = await response.json();
                    this.search_channels = dados.channels;
                    this.canais_ativos = dados.canais_ativos;
                    this.total_canais = dados.total_canais;
                } else {
                    console.error('Erro carregando canais:', response.status);
                }
            } catch (erro) {
                console.error('Erro na requisicao:', erro);
            }
        },

        async alternar_canal(canal) {
            try {
                const novo_estado = !this.search_channels[canal];
                const response = await fetch(`/api/config/channels/${canal}?enabled=${novo_estado}`, {
                    method: 'POST'
                });

                if (response.ok) {
                    await this.carregar_canais();
                    console.log(`Canal ${canal} alterado para ${novo_estado}`);
                } else {
                    const erro = await response.json();
                    alert(`Erro ao alternar canal: ${erro.detail || 'Erro desconhecido'}`);
                }
            } catch (erro) {
                console.error('Erro ao alternar canal:', erro);
                alert(`Erro: ${erro.message}`);
            }
        },

        async resetar_canais() {
            if (!confirm('Tem certeza que deseja reabilitar TODOS os canais?')) {
                return;
            }

            try {
                const response = await fetch('/api/config/channels/reset', {
                    method: 'POST'
                });

                if (response.ok) {
                    await this.carregar_canais();
                    alert('Todos os canais foram reabilitados');
                } else {
                    const erro = await response.json();
                    alert(`Erro: ${erro.detail || 'Erro desconhecido'}`);
                }
            } catch (erro) {
                console.error('Erro ao resetar canais:', erro);
                alert(`Erro: ${erro.message}`);
            }
        },

        // Gerenciar Ferramentas de Pesquisa
        async carregar_ferramentas_config() {
            try {
                const response = await fetch('/api/config/search-channels');
                if (response.ok) {
                    const config = await response.json();
                    this.ferramentas_config = {
                        perplexity: config.search_channels_enabled?.perplexity ?? true,
                        jina: config.search_channels_enabled?.jina ?? true,
                        tavily: config.search_channels_enabled?.tavily ?? true,
                        serper: config.search_channels_enabled?.serper ?? true,
                        deep_research: config.search_channels_enabled?.deep_research ?? true
                    };
                }
            } catch (erro) {
                console.warn('Nao foi possivel carregar configuracao das ferramentas:', erro);
                // Manter configuracao padrao
            }
        },

        async salvar_ferramentas_config() {
            this.salvando_config = true;
            try {
                const response = await fetch('/api/config/search-channels', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        search_channels_enabled: this.ferramentas_config
                    })
                });

                if (response.ok) {
                    alert('✓ Configuração das ferramentas salva com sucesso!');
                } else {
                    throw new Error(`Erro ${response.status}: Nao foi possivel salvar configuracao`);
                }
            } catch (erro) {
                console.error('Erro ao salvar configuracao:', erro);
                alert(`✗ Erro ao salvar: ${erro.message}`);
            } finally {
                this.salvando_config = false;
            }
        },

        // Helpers
        formatarScore(score) {
            return (score * 100).toFixed(0) + '%';
        },

        formatarData(data_string) {
            if (!data_string) return '-';
            const data = new Date(data_string);
            return data.toLocaleDateString('pt-BR');
        },

        // Retorna cor baseada no score (traffic light)
        obterCorScore(score) {
            const s = score || 0;
            if (s >= 0.75) return 'text-green-700 bg-green-50';  // Bom
            if (s >= 0.5) return 'text-yellow-700 bg-yellow-50'; // Médio
            return 'text-red-700 bg-red-50';                     // Ruim
        },

        // Retorna classe de barra baseada no score (verde > 0.75, amarelo 0.5-0.75, azul < 0.5)
        obterCorBarra(score) {
            const s = score || 0;
            if (s >= 0.75) return 'bg-green-600';
            if (s >= 0.5) return 'bg-yellow-500';
            return 'bg-blue-600';  // Azul para scores baixos ao invés de vermelho
        },

        // Retorna status descritivo
        obterStatusScore(score) {
            const s = score || 0;
            if (s >= 0.75) return '✓ Excelente';
            if (s >= 0.5) return '⚠ Bom';
            if (s > 0) return '✗ Fraco';
            return '-';
        }
    };
}

// Inicializar quando DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    const app = document.querySelector('[x-data]');
    if (app && app.__x) {
        app.__x.init();
    }
});
