# -*- coding: utf-8 -*-
"""
Worker assincrono que processa fila de pesquisas
Consome entradas da fila, executa pesquisas e armazena resultados
"""
import asyncio
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.database import (
    listar_fila_pesquisas,
    atualizar_status_fila,
    insert_resultado,
    contar_fila_pesquisas
)
from app.agente.pesquisador import AgentePesquisador
from app.agente.avaliador import Avaliador
from app.agente.deduplicador import Deduplicador
from app.utils.hash_utils import gerar_hash_conteudo


class Processador:
    """Worker que processa fila de pesquisas"""

    def __init__(self, max_workers: int = 5):
        """
        Inicializa processador

        Args:
            max_workers: Numero de workers concorrentes
        """
        self.max_workers = max_workers
        self.ativo = True

        # Modulos de IA
        self.agente_pesquisador = AgentePesquisador()
        self.avaliador = Avaliador()
        self.deduplicador = Deduplicador(threshold=0.8)

        # Rate limiting
        self.rate_limit_delay = 1.0  # segundos entre requests
        self.max_requests_por_minuto = 60
        self.requests_ultimo_minuto = []

        # Retry logic
        self.max_retries = 3

        # Timeout
        self.timeout = 30  # segundos

        # Estatisticas
        self.processadas = 0
        self.erros = 0
        self.tempo_inicio = None

    def configurar_rate_limiting(
        self,
        delay_minimo: float = 1.0,
        max_requests_por_minuto: int = 60
    ):
        """Configura rate limiting"""
        self.rate_limit_delay = delay_minimo
        self.max_requests_por_minuto = max_requests_por_minuto

    def validar_entrada(self, entrada: Dict[str, Any]) -> bool:
        """
        Valida se entrada tem campos obrigatorios

        Args:
            entrada: Entrada da fila

        Returns:
            True se valida
        """
        campos_obrigatorios = ["id", "falha_id", "query", "idioma", "ferramenta"]

        for campo in campos_obrigatorios:
            if campo not in entrada or entrada[campo] is None:
                return False

        return True

    async def aplicar_rate_limiting(self):
        """Aplica rate limiting baseado em tempo"""
        agora = time.time()

        # Remover requests antigos (> 60 segundos)
        self.requests_ultimo_minuto = [
            ts for ts in self.requests_ultimo_minuto
            if agora - ts < 60
        ]

        # Se ja atingiu limite, esperar
        if len(self.requests_ultimo_minuto) >= self.max_requests_por_minuto:
            tempo_espera = 60 - (agora - self.requests_ultimo_minuto[0])
            if tempo_espera > 0:
                await asyncio.sleep(tempo_espera)

        # Adicionar timestamp atual
        self.requests_ultimo_minuto.append(agora)

        # Delay minimo entre requests
        await asyncio.sleep(self.rate_limit_delay)

    async def obter_proxima_entrada_fila(self) -> Optional[Dict[str, Any]]:
        """
        Obtem proxima entrada pendente da fila

        Returns:
            Primeira entrada pendente ou None
        """
        entradas = await listar_fila_pesquisas(status="pendente")

        if entradas:
            return entradas[0]

        return None

    async def marcar_como_processando(self, entrada_id: int) -> bool:
        """Marca entrada como em processamento"""
        try:
            await atualizar_status_fila(entrada_id, "processando")
            return True
        except Exception as e:
            print(f"Erro marcando entrada como processando: {e}")
            return False

    async def marcar_como_processada(self, entrada_id: int) -> bool:
        """Marca entrada como completa"""
        try:
            await atualizar_status_fila(entrada_id, "completa")
            self._incrementar_processadas()
            return True
        except Exception as e:
            print(f"Erro marcando entrada como processada: {e}")
            return False

    async def marcar_como_erro(
        self,
        entrada_id: int,
        erro_msg: str
    ) -> bool:
        """Marca entrada com erro"""
        try:
            await atualizar_status_fila(entrada_id, "erro")
            self._incrementar_erros()
            return True
        except Exception as e:
            print(f"Erro marcando entrada com erro: {e}")
            return False

    def _incrementar_processadas(self):
        """Incrementa contador de processadas"""
        self.processadas += 1

    def _incrementar_erros(self):
        """Incrementa contador de erros"""
        self.erros += 1

    async def processar_entrada(self, entrada: Dict[str, Any]) -> bool:
        """
        Processa uma entrada da fila

        Args:
            entrada: Entrada para processar

        Returns:
            True se processada com sucesso
        """
        # Validar
        if not self.validar_entrada(entrada):
            print(f"Entrada invalida: {entrada}")
            await self.marcar_como_erro(entrada["id"], "Entrada invalida")
            return False

        # Marcar como em processamento (para que apareça no dashboard como "em andamento")
        await self.marcar_como_processando(entrada["id"])

        try:
            # Garantir que a query está no idioma correto
            query = entrada["query"]
            idioma = entrada["idioma"]

            # Se query está em português mas idioma-alvo é outro, traduzir
            if idioma != "pt":
                from app.utils.language_detector import detectar_idioma
                idioma_detectado, confianca = detectar_idioma(query)

                # Se query foi detectada como português com confiança, traduzir
                if idioma_detectado == "pt" and confianca > 0.2:
                    from app.utils.idiomas import traduzir_query
                    query_traduzida = await traduzir_query(
                        query=query,
                        idioma_origem="pt",
                        idioma_alvo=idioma,
                        usar_llm=True
                    )

                    if query_traduzida and query_traduzida != query:
                        print(f"[PROCESSADOR] Query traduzida: '{query}' -> '{query_traduzida}' ({idioma})")
                        query = query_traduzida

            # Executar pesquisa adaptativa (que também funciona com busca tradicional se desativada)
            resposta_pesquisa = await self.agente_pesquisador.executar_pesquisa_adaptativa(
                query=query,
                idioma=idioma,
                ferramentas=[entrada["ferramenta"]]
            )

            # Extrair resultados da resposta
            resultados = resposta_pesquisa.get("resultados", [])

            # Log dos metrics da pesquisa adaptativa
            if resposta_pesquisa.get("modo") == "adaptativo":
                print(f"\n[PROCESSADOR] Entrada {entrada['id']}: {resposta_pesquisa.get('num_buscas', 0)} buscas, "
                      f"qualidade={resposta_pesquisa.get('qualidade', 0):.3f}, "
                      f"confianca={resposta_pesquisa.get('confianca', 0):.3f}, "
                      f"diversidade={resposta_pesquisa.get('diversidade', 0):.3f}")
                print(f"[PROCESSADOR] Motivo da parada: {resposta_pesquisa.get('motivo_parada', 'desconhecido')}")

            # Avaliar e processar resultados
            resultados_processados = []

            for resultado in resultados:
                # Adicionar metadados
                resultado["falha_id"] = entrada["falha_id"]
                resultado["idioma"] = entrada["idioma"]
                resultado["ferramenta_origem"] = entrada["ferramenta"]

                # Avaliar
                score = await self.avaliador.avaliar(resultado, entrada["query"])
                resultado["confidence_score"] = score

                # Deduplicar (retorna resultado possivelmente com score aumentado)
                resultado_dedup = self.deduplicador.processar(resultado)

                resultados_processados.append(resultado_dedup)

            # Salvar resultados
            for resultado in resultados_processados:
                await self.salvar_resultado(resultado)

            # Marcar entrada como completa
            await self.marcar_como_processada(entrada["id"])
            return True

        except Exception as e:
            print(f"Erro processando entrada {entrada['id']}: {e}")
            await self.marcar_como_erro(entrada["id"], str(e))
            return False

    async def salvar_resultado(self, resultado: Dict[str, Any]) -> bool:
        """
        Salva resultado no banco de dados

        Args:
            resultado: Resultado para salvar

        Returns:
            True se salvo com sucesso
        """
        try:
            # Validar idioma antes de salvar
            idioma_esperado = resultado.get('idioma', 'pt')
            if idioma_esperado != 'pt':
                from app.utils.language_detector import validar_idioma_resultado

                titulo = resultado.get('titulo', '')
                descricao = resultado.get('descricao', '')

                eh_valido, idioma_detectado, confianca = validar_idioma_resultado(
                    titulo, descricao, idioma_esperado, threshold_confianca=0.15
                )

                # Se resultado não está no idioma correto, não salvar
                if idioma_detectado == 'pt' and idioma_esperado != 'pt' and confianca > 0.15:
                    print(f"[PROCESSADOR] ⚠️ Resultado descartado: português detectado mas esperado {idioma_esperado}")
                    return False

            # Calcular hash
            hash_conteudo = gerar_hash_conteudo(
                titulo=resultado.get('titulo', ''),
                descricao=resultado.get('descricao', ''),
                fonte=resultado.get('url', '')
            )

            # Preparar para inserir
            dados = {
                "falha_id": resultado.get("falha_id"),
                "titulo": resultado.get("titulo", ""),
                "descricao": resultado.get("descricao", ""),
                "fonte_url": resultado.get("url", ""),
                "fonte_tipo": resultado.get("fonte", "web"),
                "idioma": resultado.get("idioma", "pt"),
                "confidence_score": resultado.get("confidence_score", 0.5),
                "ferramenta_origem": resultado.get("ferramenta_origem", "unknown"),
                "hash_conteudo": hash_conteudo,
                "criado_em": datetime.now().isoformat()
            }

            # Adicionar tradução automática para português se não for PT
            idioma = dados.get("idioma", "pt")
            if idioma != "pt" and idioma:
                try:
                    from app.integracao.openrouter_api import traduzir_com_openrouter

                    # Traduzir título
                    if dados.get("titulo"):
                        titulo_pt = await traduzir_com_openrouter(
                            dados["titulo"],
                            idioma_alvo="pt",
                            idioma_origem=idioma
                        )
                        if titulo_pt and titulo_pt != dados["titulo"]:
                            dados["titulo_pt"] = titulo_pt

                    # Traduzir descrição
                    if dados.get("descricao"):
                        descricao_pt = await traduzir_com_openrouter(
                            dados["descricao"],
                            idioma_alvo="pt",
                            idioma_origem=idioma
                        )
                        if descricao_pt and descricao_pt != dados["descricao"]:
                            dados["descricao_pt"] = descricao_pt

                    print(f"[TRADUÇÃO] Resultado traduzido automaticamente para português (idioma: {idioma})")

                except Exception as e:
                    print(f"[TRADUÇÃO] Aviso: Falha ao traduzir resultado: {str(e)[:100]}")
                    # Continuar mesmo se a tradução falhar

            # Salvar no banco
            await insert_resultado(dados)
            return True

        except Exception as e:
            print(f"Erro salvando resultado: {e}")
            return False

    async def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Obtem estatisticas de processamento

        Returns:
            Dicionario com stats
        """
        tempo_decorrido = 0.0

        if self.tempo_inicio:
            tempo_decorrido = time.time() - self.tempo_inicio

        fila_pendente = await contar_fila_pesquisas(status="pendente")
        fila_total = await contar_fila_pesquisas()

        return {
            "processadas": self.processadas,
            "erros": self.erros,
            "tempo_total": tempo_decorrido,
            "fila_pendente": fila_pendente,
            "fila_total": fila_total,
            "taxa_sucesso": (
                self.processadas / (self.processadas + self.erros)
                if (self.processadas + self.erros) > 0 else 0
            ),
            "ativo": self.ativo
        }

    def resetar_stats(self):
        """Reseta estatisticas"""
        self.processadas = 0
        self.erros = 0
        self.tempo_inicio = None

    async def processar_lote(self, max_por_lote: int = 10) -> int:
        """
        Processa um lote de entradas da fila

        Args:
            max_por_lote: Maximo de entradas a processar

        Returns:
            Total de entradas processadas neste lote
        """
        self.tempo_inicio = time.time()

        entradas = await listar_fila_pesquisas(status="pendente")
        entradas = entradas[:max_por_lote]

        total = 0

        for entrada in entradas:
            if not self.ativo:
                break

            # Aplicar rate limiting
            await self.aplicar_rate_limiting()

            # Processar
            sucesso = await self.processar_entrada(entrada)

            if sucesso:
                total += 1

        return total

    async def processar_em_paralelo(self, max_por_lote: int = 10) -> int:
        """
        Processa entradas em paralelo usando workers

        Args:
            max_por_lote: Maximo de entradas por lote

        Returns:
            Total de entradas processadas
        """
        self.tempo_inicio = time.time()

        entradas = await listar_fila_pesquisas(status="pendente")
        entradas = entradas[:max_por_lote]

        # Agrupar em chunks para processar com workers
        chunks = [
            entradas[i:i + self.max_workers]
            for i in range(0, len(entradas), self.max_workers)
        ]

        total = 0

        for chunk in chunks:
            if not self.ativo:
                break

            # Processar chunk em paralelo
            tarefas = [self.processar_entrada(e) for e in chunk]
            resultados = await asyncio.gather(*tarefas, return_exceptions=True)

            # Contar sucessos
            for resultado in resultados:
                if isinstance(resultado, bool) and resultado:
                    total += 1

            # Rate limiting entre chunks
            await self.aplicar_rate_limiting()

        return total

    async def loop_processador(self, intervalo_minutos: int = 5):
        """
        Loop infinito que processa fila periodicamente

        Args:
            intervalo_minutos: Intervalo entre processamentos
        """
        print(f"Iniciando loop do processador (intervalo: {intervalo_minutos} min)...")
        self.tempo_inicio = time.time()

        intervalo_segundos = intervalo_minutos * 60

        try:
            while self.ativo:
                # Processar lote
                total = await self.processar_em_paralelo(max_por_lote=20)

                if total > 0:
                    stats = await self.obter_estatisticas()
                    print(f"Lote processado: {total} entradas. Stats: {stats}")

                # Esperar antes do proximo ciclo
                await asyncio.sleep(intervalo_segundos)

        except KeyboardInterrupt:
            print("Processador interrompido pelo usuario")
        except Exception as e:
            print(f"Erro no loop do processador: {e}")
        finally:
            self.ativo = False
            stats = await self.obter_estatisticas()
            print(f"Processador finalizado. Stats finais: {stats}")

    async def processar_tudo(self, intervalo_verificacao: int = 10):
        """
        Processa TODA a fila ate esvaziar

        Args:
            intervalo_verificacao: Segundos entre verificacoes
        """
        print("Iniciando processamento de toda a fila...")
        self.tempo_inicio = time.time()

        try:
            while self.ativo:
                fila_pendente = await contar_fila_pesquisas(status="pendente")

                if fila_pendente == 0:
                    print("Fila vazia! Processamento concluido.")
                    break

                # Processar lote
                total = await self.processar_em_paralelo(max_por_lote=20)

                if total == 0:
                    # Se nao processou nada, esperar um pouco
                    await asyncio.sleep(intervalo_verificacao)
                else:
                    stats = await self.obter_estatisticas()
                    print(
                        f"Processadas {total} entradas. "
                        f"Pendentes: {fila_pendente}. "
                        f"Taxa: {stats['taxa_sucesso']:.1%}"
                    )

        except KeyboardInterrupt:
            print("Processamento interrompido pelo usuario")
        except Exception as e:
            print(f"Erro processando tudo: {e}")
        finally:
            self.ativo = False
            stats = await self.obter_estatisticas()
            print(f"Processamento finalizado. Stats: {stats}")


async def main_processar_lote():
    """
    CLI: Processar um lote de entradas
    Uso: python -m app.agente.processador processar_lote
    """
    processador = Processador(max_workers=5)
    processador.configurar_rate_limiting(delay_minimo=0.5, max_requests_por_minuto=120)

    print("Processando lote...")
    total = await processador.processar_lote(max_por_lote=10)
    print(f"Total processado: {total}")

    stats = await processador.obter_estatisticas()
    print(f"Estatisticas: {stats}")


async def main_processar_paralelo():
    """
    CLI: Processar em paralelo
    Uso: python -m app.agente.processador processar_paralelo
    """
    processador = Processador(max_workers=5)
    processador.configurar_rate_limiting(delay_minimo=0.5, max_requests_por_minuto=120)

    print("Processando em paralelo...")
    total = await processador.processar_em_paralelo(max_por_lote=20)
    print(f"Total processado: {total}")

    stats = await processador.obter_estatisticas()
    print(f"Estatisticas: {stats}")


async def main_loop():
    """
    CLI: Rodar loop infinito
    Uso: python -m app.agente.processador loop
    """
    processador = Processador(max_workers=5)
    processador.configurar_rate_limiting(delay_minimo=1.0, max_requests_por_minuto=60)

    await processador.loop_processador(intervalo_minutos=5)


async def main_processar_tudo():
    """
    CLI: Processar toda a fila
    Uso: python -m app.agente.processador processar_tudo
    """
    processador = Processador(max_workers=5)
    processador.configurar_rate_limiting(delay_minimo=0.5, max_requests_por_minuto=120)

    await processador.processar_tudo(intervalo_verificacao=10)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        comando = sys.argv[1]

        if comando == "processar_lote":
            asyncio.run(main_processar_lote())
        elif comando == "processar_paralelo":
            asyncio.run(main_processar_paralelo())
        elif comando == "loop":
            asyncio.run(main_loop())
        elif comando == "processar_tudo":
            asyncio.run(main_processar_tudo())
        else:
            print(f"Comando desconhecido: {comando}")
            print("Comandos disponibles:")
            print("  processar_lote - Processar um lote")
            print("  processar_paralelo - Processar em paralelo")
            print("  loop - Rodar loop infinito")
            print("  processar_tudo - Processar toda a fila")
    else:
        print("Worker Processador - Sebrae Nacional")
        print("\nUso: python -m app.agente.processador <comando>")
        print("\nComandos:")
        print("  processar_lote - Processar 10 entradas")
        print("  processar_paralelo - Processar 20 entradas em paralelo")
        print("  loop - Rodar loop infinito a cada 5 minutos")
        print("  processar_tudo - Processar toda a fila ate esvaziar")
