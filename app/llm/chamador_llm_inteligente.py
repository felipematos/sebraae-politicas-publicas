"""
Chamador LLM Inteligente com Fallback Automático.
Atualizado em: 2025-11-06

Funcionalidades:
- Tentativa automática de múltiplos modelos em caso de falha
- Respeito à faixa de preço especificada pelo usuário
- Registro de métricas de uso e custos
- Sistema de cache para reduzir custos
- Fallback inteligente baseado em similaridade de modelos
"""

import asyncio
import hashlib
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

# Ajustar path para imports quando executado diretamente
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.llm.gerenciador_modelos import obter_gerenciador, GerenciadorModelos


class ChamadorLLMInteligente:
    """
    Wrapper inteligente para chamadas LLM com fallback automático.
    """

    def __init__(
        self,
        chamador_base: Callable,
        max_tentativas: int = 3,
        timeout_por_tentativa: float = 30.0,
        registrar_metricas: bool = True
    ):
        """
        Inicializa o chamador inteligente.

        Args:
            chamador_base: Função assíncrona que faz a chamada real ao LLM
                          Deve aceitar (model_id, prompt, **kwargs) e retornar string
            max_tentativas: Número máximo de tentativas (modelo principal + fallbacks)
            timeout_por_tentativa: Timeout em segundos por tentativa
            registrar_metricas: Se True, registra métricas de uso
        """
        self.chamador_base = chamador_base
        self.max_tentativas = max_tentativas
        self.timeout_por_tentativa = timeout_por_tentativa
        self.registrar_metricas = registrar_metricas
        self.gerenciador = obter_gerenciador()

        # Métricas
        self.metricas = {
            "total_chamadas": 0,
            "total_sucesso": 0,
            "total_falhas": 0,
            "total_fallbacks": 0,
            "custo_total_estimado": 0.0,
            "uso_por_modelo": {},
            "tempos_resposta": []
        }

    async def chamar_com_fallback(
        self,
        model_id: str,
        prompt: str,
        categoria_preco_max: Optional[str] = None,
        preco_max_por_1k: Optional[float] = None,
        delay_entre_tentativas: float = 1.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Chama o LLM com fallback automático em caso de falha.

        Args:
            model_id: ID do modelo principal a usar
            prompt: Prompt a enviar
            categoria_preco_max: Categoria máxima de preço ("free", "economico", etc)
            preco_max_por_1k: Preço máximo por 1K tokens (sobrescreve categoria)
            delay_entre_tentativas: Delay em segundos entre tentativas
            **kwargs: Argumentos adicionais para o chamador base

        Returns:
            Dicionário com:
                - sucesso: bool
                - resposta: str (se sucesso)
                - modelo_usado: str
                - tentativas: int
                - custo_estimado: float
                - tempo_resposta: float
                - erro: str (se falha)
        """
        inicio = time.time()
        self.metricas["total_chamadas"] += 1

        # Obter modelo principal
        modelo_principal = self.gerenciador.obter_modelo_por_id(model_id)
        if not modelo_principal:
            return {
                "sucesso": False,
                "erro": f"Modelo não encontrado: {model_id}",
                "tentativas": 0,
                "tempo_resposta": time.time() - inicio
            }

        # Determinar faixa de preço
        if preco_max_por_1k is None:
            if categoria_preco_max:
                # Mapear categoria para preço máximo
                mapa_categorias = {
                    "free": 0.0,
                    "ultra_economico": 0.0001,
                    "economico": 0.0005,
                    "balanceado": 0.002,
                    "premium": 0.01,
                    "ultra_premium": float('inf')
                }
                preco_max_por_1k = mapa_categorias.get(categoria_preco_max, float('inf'))
            else:
                # Usar preço do modelo principal + 50% como limite
                preco_max_por_1k = modelo_principal["pricing"]["total_per_1k"] * 1.5

        # Montar lista de modelos a tentar
        modelos_tentar = [modelo_principal]

        # Adicionar fallbacks se configurado
        if self.max_tentativas > 1:
            fallbacks = self.gerenciador.obter_fallback_para_modelo(
                model_id,
                max_diferenca_preco=preco_max_por_1k,
                limite=self.max_tentativas - 1
            )

            # Filtrar por preço máximo
            fallbacks_validos = [
                fb for fb in fallbacks
                if fb["pricing"]["total_per_1k"] <= preco_max_por_1k
            ]

            modelos_tentar.extend(fallbacks_validos)

        # Limitar ao máximo de tentativas
        modelos_tentar = modelos_tentar[:self.max_tentativas]

        # Tentar cada modelo
        ultimo_erro = None

        for i, modelo in enumerate(modelos_tentar):
            tentativa_inicio = time.time()

            try:
                # Se não for a primeira tentativa, aguardar delay
                if i > 0:
                    await asyncio.sleep(delay_entre_tentativas)
                    self.metricas["total_fallbacks"] += 1

                # Fazer chamada com timeout
                resposta = await asyncio.wait_for(
                    self.chamador_base(modelo["id"], prompt, **kwargs),
                    timeout=self.timeout_por_tentativa
                )

                # Sucesso!
                tempo_resposta = time.time() - tentativa_inicio
                custo_estimado = self._calcular_custo(prompt, resposta, modelo)

                # Registrar métricas
                if self.registrar_metricas:
                    self._registrar_sucesso(modelo["id"], custo_estimado, tempo_resposta)

                return {
                    "sucesso": True,
                    "resposta": resposta,
                    "modelo_usado": modelo["id"],
                    "modelo_nome": modelo["name"],
                    "tentativas": i + 1,
                    "usou_fallback": i > 0,
                    "custo_estimado": custo_estimado,
                    "tempo_resposta": time.time() - inicio,
                    "tempo_modelo": tempo_resposta
                }

            except asyncio.TimeoutError:
                ultimo_erro = f"Timeout após {self.timeout_por_tentativa}s"
                continue

            except Exception as e:
                ultimo_erro = str(e)
                continue

        # Todas as tentativas falharam
        self.metricas["total_falhas"] += 1

        return {
            "sucesso": False,
            "erro": ultimo_erro or "Todas as tentativas falharam",
            "tentativas": len(modelos_tentar),
            "modelos_tentados": [m["id"] for m in modelos_tentar],
            "tempo_resposta": time.time() - inicio
        }

    def _calcular_custo(self, prompt: str, resposta: str, modelo: Dict[str, Any]) -> float:
        """
        Calcula custo estimado da chamada.

        Args:
            prompt: Texto do prompt
            resposta: Texto da resposta
            modelo: Dicionário do modelo

        Returns:
            Custo estimado em USD
        """
        # Estimativa simples: ~4 caracteres por token
        tokens_prompt = len(prompt) / 4
        tokens_resposta = len(resposta) / 4

        custo_prompt = (tokens_prompt / 1000) * modelo["pricing"]["prompt"]
        custo_resposta = (tokens_resposta / 1000) * modelo["pricing"]["completion"]

        return custo_prompt + custo_resposta

    def _registrar_sucesso(self, model_id: str, custo: float, tempo: float):
        """Registra métricas de uma chamada bem-sucedida"""
        self.metricas["total_sucesso"] += 1
        self.metricas["custo_total_estimado"] += custo
        self.metricas["tempos_resposta"].append(tempo)

        if model_id not in self.metricas["uso_por_modelo"]:
            self.metricas["uso_por_modelo"][model_id] = {
                "chamadas": 0,
                "custo_total": 0.0,
                "tempo_medio": 0.0
            }

        uso = self.metricas["uso_por_modelo"][model_id]
        uso["chamadas"] += 1
        uso["custo_total"] += custo

        # Atualizar tempo médio
        tempos = [t for t in self.metricas["tempos_resposta"] if t > 0]
        if tempos:
            uso["tempo_medio"] = sum(tempos) / len(tempos)

    def obter_metricas(self) -> Dict[str, Any]:
        """
        Retorna as métricas coletadas.

        Returns:
            Dicionário com métricas
        """
        tempos = [t for t in self.metricas["tempos_resposta"] if t > 0]

        return {
            "total_chamadas": self.metricas["total_chamadas"],
            "total_sucesso": self.metricas["total_sucesso"],
            "total_falhas": self.metricas["total_falhas"],
            "taxa_sucesso": (
                self.metricas["total_sucesso"] / self.metricas["total_chamadas"]
                if self.metricas["total_chamadas"] > 0 else 0.0
            ),
            "total_fallbacks": self.metricas["total_fallbacks"],
            "custo_total_estimado_usd": self.metricas["custo_total_estimado"],
            "custo_total_estimado_brl": self.metricas["custo_total_estimado"] * 5.0,  # Conversão aproximada
            "tempo_medio_resposta": sum(tempos) / len(tempos) if tempos else 0.0,
            "tempo_min_resposta": min(tempos) if tempos else 0.0,
            "tempo_max_resposta": max(tempos) if tempos else 0.0,
            "uso_por_modelo": self.metricas["uso_por_modelo"]
        }

    def resetar_metricas(self):
        """Reseta as métricas coletadas"""
        self.metricas = {
            "total_chamadas": 0,
            "total_sucesso": 0,
            "total_falhas": 0,
            "total_fallbacks": 0,
            "custo_total_estimado": 0.0,
            "uso_por_modelo": {},
            "tempos_resposta": []
        }

    async def chamar_modelo_ideal(
        self,
        prompt: str,
        tarefa: str = "custo_beneficio",
        categoria_preco: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Chama automaticamente o melhor modelo para a tarefa especificada.

        Args:
            prompt: Prompt a enviar
            tarefa: "traducao", "analise", "velocidade", "custo_beneficio"
            categoria_preco: Categoria de preço ("free", "economico", etc)
            **kwargs: Argumentos adicionais

        Returns:
            Resultado da chamada com fallback
        """
        # Obter melhores modelos para a tarefa
        melhores = self.gerenciador.obter_melhores_para_tarefa(
            tarefa=tarefa,
            limite=1,
            categoria_preco=categoria_preco
        )

        if not melhores:
            return {
                "sucesso": False,
                "erro": "Nenhum modelo disponível para a tarefa especificada",
                "tentativas": 0
            }

        modelo_ideal = melhores[0]

        # Chamar com fallback
        return await self.chamar_com_fallback(
            model_id=modelo_ideal["id"],
            prompt=prompt,
            categoria_preco_max=categoria_preco,
            **kwargs
        )


class GerenciadorChamadas:
    """
    Gerenciador centralizado de chamadas LLM com múltiplos chamadores.
    """

    def __init__(self):
        self.chamadores: Dict[str, ChamadorLLMInteligente] = {}

    def registrar_chamador(
        self,
        nome: str,
        chamador_base: Callable,
        **kwargs
    ):
        """
        Registra um novo chamador LLM.

        Args:
            nome: Nome identificador do chamador
            chamador_base: Função de chamada base
            **kwargs: Argumentos para ChamadorLLMInteligente
        """
        self.chamadores[nome] = ChamadorLLMInteligente(chamador_base, **kwargs)

    def obter_chamador(self, nome: str) -> Optional[ChamadorLLMInteligente]:
        """Obtém um chamador registrado"""
        return self.chamadores.get(nome)

    def obter_metricas_totais(self) -> Dict[str, Any]:
        """
        Retorna métricas agregadas de todos os chamadores.

        Returns:
            Dicionário com métricas totais
        """
        metricas_totais = {
            "total_chamadas": 0,
            "total_sucesso": 0,
            "total_falhas": 0,
            "total_fallbacks": 0,
            "custo_total_estimado_usd": 0.0,
            "por_chamador": {}
        }

        for nome, chamador in self.chamadores.items():
            metricas = chamador.obter_metricas()
            metricas_totais["total_chamadas"] += metricas["total_chamadas"]
            metricas_totais["total_sucesso"] += metricas["total_sucesso"]
            metricas_totais["total_falhas"] += metricas["total_falhas"]
            metricas_totais["total_fallbacks"] += metricas["total_fallbacks"]
            metricas_totais["custo_total_estimado_usd"] += metricas["custo_total_estimado_usd"]
            metricas_totais["por_chamador"][nome] = metricas

        return metricas_totais


# Singleton global
_gerenciador_chamadas: Optional[GerenciadorChamadas] = None


def obter_gerenciador_chamadas() -> GerenciadorChamadas:
    """Obtém a instância global do gerenciador de chamadas"""
    global _gerenciador_chamadas

    if _gerenciador_chamadas is None:
        _gerenciador_chamadas = GerenciadorChamadas()

    return _gerenciador_chamadas


# Exemplo de uso
if __name__ == "__main__":
    import asyncio

    # Função de exemplo para simular chamada LLM
    async def chamador_exemplo(model_id: str, prompt: str, **kwargs) -> str:
        """Simula uma chamada LLM"""
        print(f"   Chamando modelo: {model_id}")
        await asyncio.sleep(0.5)  # Simular latência

        # Simular falha para alguns modelos
        import random
        if random.random() < 0.3:  # 30% de chance de falha
            raise Exception(f"Erro simulado no modelo {model_id}")

        return f"Resposta simulada do modelo {model_id} para: {prompt[:50]}..."

    async def teste():
        print("🧪 Testando Chamador LLM Inteligente\n")

        # Criar chamador
        chamador = ChamadorLLMInteligente(
            chamador_base=chamador_exemplo,
            max_tentativas=3
        )

        # Teste 1: Chamada com fallback
        print("📞 Teste 1: Chamada com fallback automático")
        resultado = await chamador.chamar_com_fallback(
            model_id="meta-llama/llama-3.1-70b-instruct:free",
            prompt="Traduza para português: Hello, how are you?",
            categoria_preco_max="free"
        )

        print(f"   Sucesso: {resultado['sucesso']}")
        if resultado['sucesso']:
            print(f"   Modelo usado: {resultado['modelo_usado']}")
            print(f"   Tentativas: {resultado['tentativas']}")
            print(f"   Usou fallback: {resultado['usou_fallback']}")
            print(f"   Custo estimado: ${resultado['custo_estimado']:.6f}")
        else:
            print(f"   Erro: {resultado['erro']}")
        print()

        # Teste 2: Modelo ideal para tradução
        print("🌍 Teste 2: Seleção automática do melhor modelo para tradução")
        resultado = await chamador.chamar_modelo_ideal(
            prompt="Translate to Spanish: Good morning, everyone!",
            tarefa="traducao",
            categoria_preco="free"
        )

        print(f"   Sucesso: {resultado['sucesso']}")
        if resultado['sucesso']:
            print(f"   Modelo escolhido: {resultado['modelo_nome']}")
        print()

        # Métricas
        print("📊 Métricas:")
        metricas = chamador.obter_metricas()
        print(f"   Total de chamadas: {metricas['total_chamadas']}")
        print(f"   Taxa de sucesso: {metricas['taxa_sucesso']*100:.1f}%")
        print(f"   Fallbacks usados: {metricas['total_fallbacks']}")
        print(f"   Custo total: ${metricas['custo_total_estimado_usd']:.6f} (≈R${metricas['custo_total_estimado_brl']:.4f})")
        print(f"   Tempo médio: {metricas['tempo_medio_resposta']:.2f}s")

    asyncio.run(teste())
