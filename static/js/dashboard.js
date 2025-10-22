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
            total_resultados: 0
        },
        percentual_processamento: 0,
        modal_falha_aberta: false,
        falha_selecionada: null,
        resultados_falha_selecionada: [],
        filtro_score_min: 0.5,

        // Inicializacao
        async init() {
            await this.carregar_falhas();
            await this.carregar_resultados();
            await this.atualizar_stats();
            // Atualizar stats a cada 5 segundos
            setInterval(() => this.atualizar_stats(), 5000);
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
                // Atualizar falhas
                const res_falhas = await fetch('/api/falhas');
                if (res_falhas.ok) {
                    const falhas = await res_falhas.json();
                    this.stats.total_falhas = falhas.length;
                }

                // Atualizar resultados
                const res_resultados = await fetch('/api/resultados');
                if (res_resultados.ok) {
                    const resultados = await res_resultados.json();
                    this.stats.total_resultados = resultados.length;
                }

                // Mock: fila pendente e processadas
                this.stats.fila_pendente = Math.max(0, Math.random() * 100);
                this.stats.processadas = Math.max(0, 100 - this.stats.fila_pendente);

                // Calcular percentual
                const total_possivel = 6000; // 50 falhas x 8 idiomas x 3 ferramentas x ~5 variacoes
                this.percentual_processamento = (this.stats.processadas / total_possivel) * 100;

            } catch (erro) {
                console.error('Erro atualizando stats:', erro);
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

        // Helpers
        formatarScore(score) {
            return (score * 100).toFixed(0) + '%';
        },

        formatarData(data_string) {
            if (!data_string) return '-';
            const data = new Date(data_string);
            return data.toLocaleDateString('pt-BR');
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
