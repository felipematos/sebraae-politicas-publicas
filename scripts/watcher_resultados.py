#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Watcher processo que monitora resultados em tempo real
Detecta problemas de qualidade e pausa pesquisa se necessário
"""
import asyncio
import sys
from datetime import datetime, timedelta
import json

sys.path.insert(0, '/Users/felipematossardinhapinto/Library/CloudStorage/GoogleDrive-Felipe@felipematos.net/My Drive/10K/Projetos/2025/Sebrae Nacional/Code')

from app.database import db
from app.config import settings


class VigiaResultados:
    """Monitora qualidade de resultados em tempo real"""

    def __init__(self):
        self.problemas_detectados = []
        self.ultima_verificacao = None
        self.total_verificados = 0
        self.taxa_erro = 0.0
        self.pesquisa_pausada = False
        self.motivo_pausa = None

    def _registrar_problema(self, tipo: str, descricao: str, severidade: str = "warning"):
        """Registra um problema encontrado"""
        problema = {
            "timestamp": datetime.now().isoformat(),
            "tipo": tipo,
            "descricao": descricao,
            "severidade": severidade  # "warning", "critical"
        }
        self.problemas_detectados.append(problema)
        print(f"   [{severidade.upper()}] {tipo}: {descricao}")

    async def verificar_integridade_fila(self) -> dict:
        """Verifica integridade da fila de pesquisas"""
        print("\n📋 Verificando integridade da fila...")
        problemas_fila = []

        # Verificar entradas sem falha_id
        orfas = await db.fetch_all("""
            SELECT COUNT(*) as total FROM fila_pesquisas
            WHERE falha_id IS NULL OR falha_id = 0
        """)
        if orfas[0]['total'] > 0:
            problema = f"{orfas[0]['total']} entradas com falha_id inválida"
            problemas_fila.append(problema)
            self._registrar_problema("FILA_ORFÃ", problema, "critical")

        # Verificar status inválidos
        status_invalidos = await db.fetch_all("""
            SELECT status, COUNT(*) as total FROM fila_pesquisas
            WHERE status NOT IN ('pendente', 'processando', 'completa', 'erro')
            GROUP BY status
        """)
        for row in status_invalidos:
            problema = f"{row['total']} entradas com status inválido: {row['status']}"
            problemas_fila.append(problema)
            self._registrar_problema("FILA_STATUS_INVÁLIDO", problema, "critical")

        # Verificar processando há muito tempo (>5 minutos sem atualização)
        # NOTA: Esta verificação requer coluna 'atualizado_em' em fila_pesquisas que não existe ainda
        # TODO: Adicionar migração para incluir 'atualizado_em DATETIME' em fila_pesquisas
        # Por enquanto, apenas contamos quantas entradas estão em 'processando'
        processando = await db.fetch_all("""
            SELECT COUNT(*) as total FROM fila_pesquisas
            WHERE status = 'processando'
        """)
        if processando[0]['total'] > 0:
            print(f"   ℹ️  {processando[0]['total']} entradas em 'processando' (sem detecção de timeout por enquanto)")

        return {"problemas": len(problemas_fila), "detalhes": problemas_fila}

    async def verificar_qualidade_resultados(self, ultimas_horas: int = 1) -> dict:
        """Verifica qualidade de resultados recentes"""
        print(f"\n📊 Verificando qualidade dos últimos {ultimas_horas} hora(s)...")

        tempo_limite = datetime.now() - timedelta(hours=ultimas_horas)
        problemas_qualidade = []

        # 1. Verificar resultados com campos vazios
        vazios = await db.fetch_all(f"""
            SELECT COUNT(*) as total FROM resultados_pesquisa
            WHERE criado_em > datetime('{tempo_limite.isoformat()}')
            AND (titulo IS NULL OR titulo = '' OR descricao IS NULL OR descricao = '')
        """)
        if vazios[0]['total'] > 0:
            problema = f"{vazios[0]['total']} resultados com campos vazios"
            problemas_qualidade.append(problema)
            self._registrar_problema("RESULTADO_VAZIO", problema, "critical")

        # 2. Verificar falta de traduções
        sem_traducoes = await db.fetch_all(f"""
            SELECT COUNT(*) as total FROM resultados_pesquisa
            WHERE criado_em > datetime('{tempo_limite.isoformat()}')
            AND idioma NOT IN ('pt', 'en')
            AND (titulo_pt IS NULL OR titulo_pt = '' OR titulo_en IS NULL OR titulo_en = '')
        """)
        if sem_traducoes[0]['total'] > 0:
            problema = f"{sem_traducoes[0]['total']} resultados não-PT/EN sem traduções"
            problemas_qualidade.append(problema)
            self._registrar_problema("FALTA_TRADUCAO", problema, "warning")

        # 3. Verificar confidence_score muito baixo (<0.3)
        baixa_confianca = await db.fetch_all(f"""
            SELECT COUNT(*) as total FROM resultados_pesquisa
            WHERE criado_em > datetime('{tempo_limite.isoformat()}')
            AND confidence_score < 0.3
        """)
        if baixa_confianca[0]['total'] > 0:
            problema = f"{baixa_confianca[0]['total']} resultados com confiança <0.3"
            problemas_qualidade.append(problema)
            self._registrar_problema("BAIXA_CONFIANÇA", problema, "warning")

        # 4. Verificar URLs vazias (sempre esperar ao menos alguns URLs)
        sem_url = await db.fetch_all(f"""
            SELECT COUNT(*) as total FROM resultados_pesquisa
            WHERE criado_em > datetime('{tempo_limite.isoformat()}')
            AND (fonte_url IS NULL OR fonte_url = '')
        """)
        total_recentes = await db.fetch_all(f"""
            SELECT COUNT(*) as total FROM resultados_pesquisa
            WHERE criado_em > datetime('{tempo_limite.isoformat()}')
        """)
        if total_recentes[0]['total'] > 10 and sem_url[0]['total'] > total_recentes[0]['total'] * 0.5:
            problema = f"{sem_url[0]['total']}/{total_recentes[0]['total']} resultados sem URL"
            problemas_qualidade.append(problema)
            self._registrar_problema("FALTA_URL", problema, "warning")

        # 5. Verificar tamanhos de conteúdo muito pequenos
        pequenos = await db.fetch_all(f"""
            SELECT COUNT(*) as total FROM resultados_pesquisa
            WHERE criado_em > datetime('{tempo_limite.isoformat()}')
            AND (
                LENGTH(titulo) < 5 OR
                LENGTH(descricao) < 20
            )
        """)
        if pequenos[0]['total'] > 0:
            problema = f"{pequenos[0]['total']} resultados com conteúdo muito pequeno"
            problemas_qualidade.append(problema)
            self._registrar_problema("CONTEÚDO_PEQUENO", problema, "warning")

        # 6. Verificar hash duplicado (mesmos resultados repetidos)
        duplicados = await db.fetch_all(f"""
            SELECT hash_conteudo, COUNT(*) as freq FROM resultados_pesquisa
            WHERE criado_em > datetime('{tempo_limite.isoformat()}')
            AND hash_conteudo IS NOT NULL AND hash_conteudo != ''
            GROUP BY hash_conteudo
            HAVING freq > 2
            LIMIT 10
        """)
        if duplicados:
            problema = f"{len(duplicados)} hashes de conteúdo com >2 ocorrências"
            problemas_qualidade.append(problema)
            self._registrar_problema("DUPLICAÇÃO_ALTA", problema, "warning")

        return {"problemas": len(problemas_qualidade), "detalhes": problemas_qualidade}

    async def verificar_taxa_erro(self) -> dict:
        """Verifica taxa de erro em processamento recente"""
        print("\n⚠️  Verificando taxa de erro...")

        # Contar últimas 100 entradas processadas (usando criado_em já que atualizado_em não existe em fila_pesquisas)
        stats = await db.fetch_all("""
            SELECT status, COUNT(*) as total FROM fila_pesquisas
            WHERE status IN ('completa', 'erro')
            ORDER BY id DESC
            LIMIT 100
        """)

        total = sum(row['total'] for row in stats)
        erros = next((row['total'] for row in stats if row['status'] == 'erro'), 0)

        if total > 0:
            self.taxa_erro = erros / total

            if self.taxa_erro > 0.5:  # >50% de erro
                problema = f"Taxa de erro crítica: {self.taxa_erro:.1%} (ultimas 100 entradas)"
                self._registrar_problema("TAXA_ERRO_CRÍTICA", problema, "critical")
                return {"problemas": 1, "taxa_erro": self.taxa_erro, "detalhes": [problema]}
            elif self.taxa_erro > 0.2:  # >20% de erro
                print(f"   ⚠️ Taxa de erro elevada: {self.taxa_erro:.1%}")

        return {"problemas": 0, "taxa_erro": self.taxa_erro}

    async def verificar_progressao(self) -> dict:
        """Verifica se a pesquisa está progredindo"""
        print("\n📈 Verificando progressão...")

        # Contar resultados da última hora
        uma_hora_atras = datetime.now() - timedelta(hours=1)
        resultados_hora = await db.fetch_all(f"""
            SELECT COUNT(*) as total FROM resultados_pesquisa
            WHERE criado_em > datetime('{uma_hora_atras.isoformat()}')
        """)

        if resultados_hora[0]['total'] == 0:
            problema = "Nenhum resultado em 1 hora - pesquisa pode estar parada"
            self._registrar_problema("SEM_PROGRESSÃO", problema, "critical")
            return {"problemas": 1, "resultados_ultima_hora": 0}

        return {"problemas": 0, "resultados_ultima_hora": resultados_hora[0]['total']}

    async def verificar_tudo(self) -> dict:
        """Executa todas as verificações"""
        print("=" * 80)
        print(f"🔍 VERIFICAÇÃO DE QUALIDADE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        self.ultima_verificacao = datetime.now()
        self.problemas_detectados = []
        problemas_totais = 0

        # Executar verificações
        fila = await self.verificar_integridade_fila()
        qualidade = await self.verificar_qualidade_resultados()
        taxa_erro = await self.verificar_taxa_erro()
        progressao = await self.verificar_progressao()

        problemas_totais = sum([
            fila.get("problemas", 0),
            qualidade.get("problemas", 0),
            taxa_erro.get("problemas", 0),
            progressao.get("problemas", 0)
        ])

        # Relatório final
        print(f"\n{'='*80}")
        print(f"📊 RESUMO FINAL")
        print(f"{'='*80}")
        print(f"✅ Total de problemas encontrados: {problemas_totais}")
        print(f"📋 Verificações críticas: {len([p for p in self.problemas_detectados if p['severidade'] == 'critical'])}")
        print(f"⚠️  Avisos: {len([p for p in self.problemas_detectados if p['severidade'] == 'warning'])}")

        # Decidir se deve pausar
        problemas_criticos = [p for p in self.problemas_detectados if p['severidade'] == 'critical']

        if problemas_criticos:
            self.pesquisa_pausada = True
            self.motivo_pausa = "Problemas críticos detectados"

            print(f"\n🛑 PESQUISA PAUSADA - Problemas críticos:")
            for problema in problemas_criticos:
                print(f"   ❌ [{problema['tipo']}] {problema['descricao']}")
        else:
            self.pesquisa_pausada = False
            if problemas_totais > 0:
                print(f"\n⚠️  Avisos encontrados - monitorar próximas iterações")
            else:
                print(f"\n✅ Todos os controles de qualidade passaram!")

        print(f"{'='*80}\n")

        return {
            "timestamp": self.ultima_verificacao.isoformat(),
            "total_problemas": problemas_totais,
            "problemas_criticos": len(problemas_criticos),
            "pesquisa_pausada": self.pesquisa_pausada,
            "motivo_pausa": self.motivo_pausa,
            "detalhes": self.problemas_detectados
        }

    async def monitorar_continuo(self, intervalo_minutos: int = 5):
        """Monitora continuamente os resultados"""
        print(f"🕐 Iniciando monitoramento contínuo (a cada {intervalo_minutos} minutos)...\n")

        iteracao = 0
        try:
            while True:
                iteracao += 1
                print(f"\n[ITERAÇÃO {iteracao}] {datetime.now().strftime('%H:%M:%S')}")

                # Executar verificação
                resultado = await self.verificar_tudo()

                # Salvar em arquivo de log
                log_file = "/tmp/watcher_resultados_log.jsonl"
                try:
                    with open(log_file, "a") as f:
                        f.write(json.dumps(resultado) + "\n")
                except:
                    pass

                # Se pausou, aguardar mais tempo antes de verificar novamente
                if self.pesquisa_pausada:
                    print(f"\n⏸️  Sistema pausado. Aguardando intervenção manual...")
                    await asyncio.sleep(60)  # Verifica a cada 1 min enquanto pausado
                else:
                    await asyncio.sleep(intervalo_minutos * 60)

        except KeyboardInterrupt:
            print("\n\n✅ Monitoramento encerrado pelo usuário")


async def main():
    """Executa verificação única ou contínua"""
    import sys

    vigia = VigiaResultados()

    if len(sys.argv) > 1 and sys.argv[1] == "continuo":
        # Monitoramento contínuo
        intervalo = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        await vigia.monitorar_continuo(intervalo_minutos=intervalo)
    else:
        # Verificação única
        await vigia.verificar_tudo()


if __name__ == "__main__":
    asyncio.run(main())
