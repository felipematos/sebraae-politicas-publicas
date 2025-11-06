"""
Gerenciador Inteligente de Modelos LLM da OpenRouter.
Atualizado em: 2025-11-06

Funcionalidades:
- Carregamento automático de modelos do repositório JSON
- Atualização automática quando dados estão desatualizados (>24h)
- Busca de modelos por categoria, score, tarefa
- Sistema de fallback inteligente baseado em preço e características
- Cache em memória para performance
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import asyncio


class GerenciadorModelos:
    """
    Gerenciador centralizado de modelos LLM da OpenRouter.
    """

    def __init__(self, arquivo_modelos: str = None, auto_atualizar: bool = True):
        """
        Inicializa o gerenciador de modelos.

        Args:
            arquivo_modelos: Caminho para o arquivo JSON de modelos
            auto_atualizar: Se True, atualiza automaticamente quando necessário
        """
        if arquivo_modelos is None:
            # Caminho padrão relativo ao diretório do script
            base_dir = Path(__file__).parent
            self.arquivo_modelos = base_dir / "modelos_openrouter.json"
        else:
            self.arquivo_modelos = Path(arquivo_modelos)

        self.auto_atualizar = auto_atualizar
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._atualizacao_em_progresso = False

        # Carregar modelos na inicialização
        self._carregar_modelos()

    def _carregar_modelos(self, forcar: bool = False) -> Dict[str, Any]:
        """
        Carrega os modelos do arquivo JSON.

        Args:
            forcar: Se True, recarrega mesmo se já estiver em cache

        Returns:
            Dicionário com os dados dos modelos
        """
        # Usar cache se disponível e não forçar recarga
        if not forcar and self._cache is not None:
            # Cache válido por 1 hora
            if datetime.now() - self._cache_timestamp < timedelta(hours=1):
                return self._cache

        # Verificar se arquivo existe
        if not self.arquivo_modelos.exists():
            raise FileNotFoundError(
                f"Arquivo de modelos não encontrado: {self.arquivo_modelos}\n"
                f"Execute o script processar_modelos_openrouter.py primeiro."
            )

        # Carregar arquivo
        with open(self.arquivo_modelos, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        # Verificar se está desatualizado e atualizar se necessário
        if self.auto_atualizar and self._esta_desatualizado(dados):
            print("⚠️  Modelos desatualizados. Atualizando automaticamente...")
            self._atualizar_modelos()
            # Recarregar após atualização
            with open(self.arquivo_modelos, 'r', encoding='utf-8') as f:
                dados = json.load(f)

        # Atualizar cache
        self._cache = dados
        self._cache_timestamp = datetime.now()

        return dados

    def _esta_desatualizado(self, dados: Dict[str, Any]) -> bool:
        """
        Verifica se os dados dos modelos estão desatualizados (>24h).

        Args:
            dados: Dicionário com os dados dos modelos

        Returns:
            True se estiver desatualizado
        """
        try:
            ultima_atualizacao = datetime.fromisoformat(
                dados["metadata"]["ultima_atualizacao"]
            )
            idade = datetime.now() - ultima_atualizacao
            return idade > timedelta(days=1)
        except (KeyError, ValueError):
            # Se não conseguir determinar, considerar desatualizado
            return True

    def _atualizar_modelos(self):
        """
        Atualiza os modelos buscando da API da OpenRouter.
        """
        if self._atualizacao_em_progresso:
            print("⏳ Atualização já em progresso...")
            return

        try:
            self._atualizacao_em_progresso = True
            base_dir = Path(__file__).parent

            # 1. Buscar modelos da API
            print("📡 Buscando modelos da OpenRouter...")
            subprocess.run(
                [
                    "curl", "-X", "GET",
                    "https://openrouter.ai/api/v1/models",
                    "-H", f"Authorization: Bearer {self._get_api_key()}",
                    "-H", "Content-Type: application/json",
                    "-o", "/tmp/openrouter_models_raw.json"
                ],
                check=True,
                capture_output=True
            )

            # 2. Formatar JSON
            subprocess.run(
                ["python3", "-m", "json.tool",
                 "/tmp/openrouter_models_raw.json",
                 "/tmp/openrouter_models.json"],
                check=True,
                capture_output=True
            )

            # 3. Processar modelos
            print("⚙️  Processando modelos com metadados...")
            script_processar = base_dir / "processar_modelos_openrouter.py"
            subprocess.run(
                ["python3", str(script_processar),
                 "/tmp/openrouter_models.json",
                 str(self.arquivo_modelos)],
                check=True
            )

            print("✅ Modelos atualizados com sucesso!")

        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao atualizar modelos: {e}")
        finally:
            self._atualizacao_em_progresso = False

    def _get_api_key(self) -> str:
        """
        Obtém a chave da API da OpenRouter do arquivo .env.

        Returns:
            Chave da API
        """
        env_file = Path(__file__).parent.parent.parent / ".env"

        if not env_file.exists():
            raise ValueError("Arquivo .env não encontrado")

        with open(env_file, 'r') as f:
            for linha in f:
                if linha.startswith("OPENROUTER_API_KEY="):
                    return linha.split("=", 1)[1].strip()

        raise ValueError("OPENROUTER_API_KEY não encontrada no .env")

    def obter_modelo_por_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca um modelo específico por ID.

        Args:
            model_id: ID do modelo (ex: "anthropic/claude-3-sonnet")

        Returns:
            Dicionário com dados do modelo ou None se não encontrado
        """
        dados = self._carregar_modelos()

        for modelo in dados["todos_modelos"]:
            if modelo["id"] == model_id:
                return modelo

        return None

    def obter_modelos_por_categoria(self, categoria: str) -> List[Dict[str, Any]]:
        """
        Busca modelos por categoria de preço.

        Args:
            categoria: "free", "ultra_economico", "economico", "balanceado", "premium", "ultra_premium"

        Returns:
            Lista de modelos da categoria
        """
        dados = self._carregar_modelos()
        return dados["categorias"].get(categoria, [])

    def obter_melhores_para_tarefa(
        self,
        tarefa: str,
        limite: int = 10,
        categoria_preco: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca os melhores modelos para uma tarefa específica.

        Args:
            tarefa: "traducao", "analise", "velocidade", "custo_beneficio"
            limite: Número máximo de modelos a retornar
            categoria_preco: Filtrar por categoria de preço (opcional)

        Returns:
            Lista de modelos ordenados por score da tarefa
        """
        dados = self._carregar_modelos()

        # Se a tarefa está nos top_models, usar esse cache
        if tarefa in dados["top_models"] and categoria_preco is None:
            return dados["top_models"][tarefa][:limite]

        # Caso contrário, filtrar e ordenar manualmente
        modelos = dados["todos_modelos"]

        if categoria_preco:
            modelos = [m for m in modelos if m["pricing"]["categoria"] == categoria_preco]

        # Ordenar por score da tarefa
        if tarefa in ["traducao", "analise", "velocidade", "custo_beneficio"]:
            modelos = sorted(
                modelos,
                key=lambda x: x["scores"].get(tarefa, 0),
                reverse=True
            )

        return modelos[:limite]

    def obter_modelos_por_faixa_preco(
        self,
        preco_max: float,
        tarefa: Optional[str] = None,
        limite: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Busca modelos dentro de uma faixa de preço.

        Args:
            preco_max: Preço máximo por 1K tokens (prompt + completion)
            tarefa: Se especificado, ordena por score da tarefa
            limite: Número máximo de modelos a retornar

        Returns:
            Lista de modelos dentro da faixa de preço
        """
        dados = self._carregar_modelos()
        modelos = dados["todos_modelos"]

        # Filtrar por preço
        modelos_filtrados = [
            m for m in modelos
            if m["pricing"]["total_per_1k"] <= preco_max
        ]

        # Ordenar por tarefa se especificado
        if tarefa and tarefa in ["traducao", "analise", "velocidade", "custo_beneficio"]:
            modelos_filtrados = sorted(
                modelos_filtrados,
                key=lambda x: x["scores"].get(tarefa, 0),
                reverse=True
            )
        else:
            # Ordenar por custo-benefício por padrão
            modelos_filtrados = sorted(
                modelos_filtrados,
                key=lambda x: x["scores"]["custo_beneficio"],
                reverse=True
            )

        return modelos_filtrados[:limite]

    def obter_fallback_para_modelo(
        self,
        model_id: str,
        max_diferenca_preco: float = 0.002,
        limite: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Obtém modelos de fallback para um modelo específico.

        Args:
            model_id: ID do modelo original
            max_diferenca_preco: Diferença máxima de preço aceitável
            limite: Número máximo de modelos de fallback

        Returns:
            Lista de modelos similares ordenados por similaridade
        """
        modelo_original = self.obter_modelo_por_id(model_id)

        if not modelo_original:
            return []

        # Primeiro tentar usar os modelos similares pré-calculados
        fallbacks = []
        for similar_id in modelo_original.get("fallback_similar", [])[:limite]:
            modelo = self.obter_modelo_por_id(similar_id)
            if modelo:
                # Verificar diferença de preço
                diff_preco = abs(
                    modelo["pricing"]["total_per_1k"] -
                    modelo_original["pricing"]["total_per_1k"]
                )
                if diff_preco <= max_diferenca_preco:
                    fallbacks.append(modelo)

        # Se não tiver fallbacks suficientes, buscar por preço similar
        if len(fallbacks) < limite:
            preco_original = modelo_original["pricing"]["total_per_1k"]
            preco_min = preco_original
            preco_max = preco_original + max_diferenca_preco

            modelos_similares = self.obter_modelos_por_faixa_preco(
                preco_max=preco_max,
                limite=limite * 2
            )

            # Filtrar modelos que já estão nos fallbacks e o próprio modelo original
            ids_existentes = {f["id"] for f in fallbacks} | {model_id}

            for modelo in modelos_similares:
                if modelo["id"] not in ids_existentes:
                    if modelo["pricing"]["total_per_1k"] >= preco_min:
                        fallbacks.append(modelo)

                        if len(fallbacks) >= limite:
                            break

        return fallbacks[:limite]

    def obter_modelo_economico_equivalente(
        self,
        model_id: str,
        categoria_alvo: str = "economico"
    ) -> Optional[Dict[str, Any]]:
        """
        Encontra um modelo mais econômico com características similares.

        Args:
            model_id: ID do modelo original
            categoria_alvo: Categoria de preço desejada

        Returns:
            Modelo econômico equivalente ou None
        """
        modelo_original = self.obter_modelo_por_id(model_id)

        if not modelo_original:
            return None

        # Buscar modelos na categoria alvo
        candidatos = self.obter_modelos_por_categoria(categoria_alvo)

        if not candidatos:
            return None

        # Calcular similaridade baseada nos scores
        def calcular_similaridade(modelo: Dict[str, Any]) -> float:
            """Calcula similaridade de scores (0.0-1.0)"""
            diff_traducao = abs(
                modelo["scores"]["traducao"] -
                modelo_original["scores"]["traducao"]
            )
            diff_analise = abs(
                modelo["scores"]["analise"] -
                modelo_original["scores"]["analise"]
            )
            diff_velocidade = abs(
                modelo["scores"]["velocidade"] -
                modelo_original["scores"]["velocidade"]
            )

            # Média das diferenças (menor = mais similar)
            media_diff = (diff_traducao + diff_analise + diff_velocidade) / 3

            # Converter para score de similaridade (0-1)
            return max(0.0, 1.0 - (media_diff / 10.0))

        # Ordenar por similaridade
        candidatos_com_score = [
            (modelo, calcular_similaridade(modelo))
            for modelo in candidatos
        ]
        candidatos_com_score.sort(key=lambda x: x[1], reverse=True)

        # Retornar o mais similar
        if candidatos_com_score:
            return candidatos_com_score[0][0]

        return None

    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Retorna estatísticas sobre os modelos disponíveis.

        Returns:
            Dicionário com estatísticas
        """
        dados = self._carregar_modelos()

        return {
            "total_modelos": dados["metadata"]["total_modelos"],
            "ultima_atualizacao": dados["metadata"]["data_atualizacao_legivel"],
            "por_categoria": {
                categoria: len(modelos)
                for categoria, modelos in dados["categorias"].items()
            },
            "top_custo_beneficio": [
                {
                    "id": m["id"],
                    "name": m["name"],
                    "score": m["scores"]["custo_beneficio"],
                    "preco": m["pricing"]["total_per_1k"]
                }
                for m in dados["top_models"]["custo_beneficio"][:5]
            ]
        }

    def forcar_atualizacao(self):
        """
        Força uma atualização dos modelos imediatamente.
        """
        print("🔄 Forçando atualização dos modelos...")
        self._atualizar_modelos()
        self._carregar_modelos(forcar=True)


# Singleton global para fácil acesso
_gerenciador_global: Optional[GerenciadorModelos] = None


def obter_gerenciador() -> GerenciadorModelos:
    """
    Obtém a instância global do gerenciador de modelos.

    Returns:
        Instância do GerenciadorModelos
    """
    global _gerenciador_global

    if _gerenciador_global is None:
        _gerenciador_global = GerenciadorModelos()

    return _gerenciador_global


# Funções de conveniência para uso direto
def obter_modelo(model_id: str) -> Optional[Dict[str, Any]]:
    """Busca um modelo por ID"""
    return obter_gerenciador().obter_modelo_por_id(model_id)


def obter_melhores_traducao(limite: int = 10) -> List[Dict[str, Any]]:
    """Retorna os melhores modelos para tradução"""
    return obter_gerenciador().obter_melhores_para_tarefa("traducao", limite)


def obter_melhores_analise(limite: int = 10) -> List[Dict[str, Any]]:
    """Retorna os melhores modelos para análise"""
    return obter_gerenciador().obter_melhores_para_tarefa("analise", limite)


def obter_mais_rapidos(limite: int = 10) -> List[Dict[str, Any]]:
    """Retorna os modelos mais rápidos"""
    return obter_gerenciador().obter_melhores_para_tarefa("velocidade", limite)


def obter_melhor_custo_beneficio(limite: int = 10) -> List[Dict[str, Any]]:
    """Retorna os modelos com melhor custo-benefício"""
    return obter_gerenciador().obter_melhores_para_tarefa("custo_beneficio", limite)


def obter_modelos_gratuitos() -> List[Dict[str, Any]]:
    """Retorna todos os modelos gratuitos"""
    return obter_gerenciador().obter_modelos_por_categoria("free")


def obter_fallback(model_id: str, limite: int = 5) -> List[Dict[str, Any]]:
    """Obtém modelos de fallback para um modelo específico"""
    return obter_gerenciador().obter_fallback_para_modelo(model_id, limite=limite)


if __name__ == "__main__":
    # Teste do gerenciador
    print("🧪 Testando Gerenciador de Modelos\n")

    gerenciador = obter_gerenciador()

    # Estatísticas
    print("📊 Estatísticas:")
    stats = gerenciador.obter_estatisticas()
    print(f"   Total de modelos: {stats['total_modelos']}")
    print(f"   Última atualização: {stats['ultima_atualizacao']}")
    print(f"   Por categoria: {stats['por_categoria']}")
    print()

    # Top 5 custo-benefício
    print("🏆 Top 5 Custo-Benefício:")
    for i, modelo in enumerate(stats["top_custo_beneficio"], 1):
        print(f"   {i}. {modelo['name']}")
        print(f"      Score: {modelo['score']}/10 | Preço: ${modelo['preco']:.6f}/1K")
    print()

    # Melhores para tradução (gratuitos)
    print("🌍 Melhores para Tradução (gratuitos):")
    traducao_free = gerenciador.obter_melhores_para_tarefa(
        "traducao", limite=5, categoria_preco="free"
    )
    for i, modelo in enumerate(traducao_free, 1):
        print(f"   {i}. {modelo['name']}")
        print(f"      Score Tradução: {modelo['scores']['traducao']}/10")
    print()

    # Teste de fallback
    print("🔄 Teste de Fallback:")
    modelo_teste = "anthropic/claude-3-sonnet"
    fallbacks = gerenciador.obter_fallback_para_modelo(modelo_teste, limite=3)
    print(f"   Fallbacks para {modelo_teste}:")
    for i, fb in enumerate(fallbacks, 1):
        print(f"   {i}. {fb['name']} (${fb['pricing']['total_per_1k']:.6f}/1K)")
