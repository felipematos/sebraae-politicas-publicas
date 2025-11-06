# -*- coding: utf-8 -*-
"""
Cliente OpenRouter V2 - Versão melhorada com gerenciamento inteligente de modelos.
Atualizado em: 2025-11-06

Esta versão estende o OpenRouterClient original com:
- Integração com gerenciador de modelos
- Atualização automática de preços e disponibilidade
- Sistema de fallback inteligente baseado em características do modelo
- Métricas detalhadas de uso e custo
"""

import asyncio
import aiohttp
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ajustar path para imports quando executado diretamente
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import settings
from app.llm.gerenciador_modelos import obter_gerenciador
from app.llm.chamador_llm_inteligente import ChamadorLLMInteligente


class OpenRouterClientV2:
    """
    Cliente OpenRouter V2 com gerenciamento inteligente de modelos.
    Mantém compatibilidade com v1 mas usa gerenciador de modelos para:
    - Seleção automática do melhor modelo
    - Fallback inteligente
    - Preços sempre atualizados
    """

    BASE_URL = "https://openrouter.io/api/v1"

    def __init__(self, api_key: Optional[str] = None, usar_fallback: bool = True):
        """
        Inicializa cliente OpenRouter V2

        Args:
            api_key: Chave da API (usa settings.OPENROUTER_API_KEY se não fornecido)
            usar_fallback: Se True, usa sistema de fallback automático
        """
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        self.gerenciador = obter_gerenciador()
        self.usar_fallback = usar_fallback

        # Inicializar chamador inteligente
        if usar_fallback:
            self.chamador_inteligente = ChamadorLLMInteligente(
                chamador_base=self._chamar_modelo_base,
                max_tentativas=3
            )
        else:
            self.chamador_inteligente = None

    async def __aenter__(self):
        """Context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()

    def obter_melhores_modelos_traducao(
        self,
        categoria_preco: str = "free",
        limite: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Obtém os melhores modelos para tradução.

        Args:
            categoria_preco: Categoria de preço desejada
            limite: Número máximo de modelos

        Returns:
            Lista de modelos recomendados
        """
        return self.gerenciador.obter_melhores_para_tarefa(
            tarefa="traducao",
            limite=limite,
            categoria_preco=categoria_preco
        )

    def obter_melhores_modelos_analise(
        self,
        categoria_preco: str = "balanceado",
        limite: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Obtém os melhores modelos para análise.

        Args:
            categoria_preco: Categoria de preço desejada
            limite: Número máximo de modelos

        Returns:
            Lista de modelos recomendados
        """
        return self.gerenciador.obter_melhores_para_tarefa(
            tarefa="analise",
            limite=limite,
            categoria_preco=categoria_preco
        )

    def obter_modelo_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações detalhadas sobre um modelo.

        Args:
            model_id: ID do modelo

        Returns:
            Dicionário com informações do modelo
        """
        return self.gerenciador.obter_modelo_por_id(model_id)

    async def _chamar_modelo_base(
        self,
        model_id: str,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 500,
        **kwargs
    ) -> str:
        """
        Chamada base ao modelo (sem fallback).

        Args:
            model_id: ID do modelo
            prompt: Prompt a enviar
            temperature: Temperatura (0.0-1.0)
            max_tokens: Número máximo de tokens
            **kwargs: Argumentos adicionais

        Returns:
            Resposta do modelo

        Raises:
            Exception: Se houver erro na chamada
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://sebrae-politicas.app",
            "X-Title": "Sebrae Research Agent V2",
            "Content-Type": "application/json",
        }

        data = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": kwargs.get("timeout", 30),
        }

        async with self.session.post(
            f"{self.BASE_URL}/chat/completions",
            headers=headers,
            json=data
        ) as resp:
            if resp.status != 200:
                texto_erro = await resp.text()
                raise Exception(
                    f"Erro OpenRouter (status {resp.status}): {texto_erro[:200]}"
                )

            resultado = await resp.json()

            if "choices" not in resultado or not resultado["choices"]:
                raise Exception("Resposta inválida da OpenRouter (sem choices)")

            return resultado["choices"][0]["message"]["content"]

    async def traduzir_texto(
        self,
        texto: str,
        idioma_destino: str = "pt",
        categoria_preco: str = "free"
    ) -> Optional[str]:
        """
        Traduz texto usando o melhor modelo disponível com fallback automático.

        Args:
            texto: Texto a traduzir
            idioma_destino: Idioma de destino (padrão: pt)
            categoria_preco: Categoria de preço máxima

        Returns:
            Texto traduzido ou None se falhar
        """
        if not texto or len(texto.strip()) < 3:
            return texto

        prompt = f"""Translate the following text to {idioma_destino}.
Return ONLY the translation, without explanations or notes.

Text to translate:
{texto}"""

        if self.usar_fallback and self.chamador_inteligente:
            # Usar chamador inteligente com fallback
            resultado = await self.chamador_inteligente.chamar_modelo_ideal(
                prompt=prompt,
                tarefa="traducao",
                categoria_preco=categoria_preco
            )

            if resultado["sucesso"]:
                return resultado["resposta"].strip()
            else:
                print(f"[WARN] Tradução falhou após {resultado['tentativas']} tentativas")
                return None
        else:
            # Modo sem fallback - usar melhor modelo disponível
            modelos = self.obter_melhores_modelos_traducao(categoria_preco, limite=1)

            if not modelos:
                return None

            try:
                resposta = await self._chamar_modelo_base(modelos[0]["id"], prompt)
                return resposta.strip()
            except Exception as e:
                print(f"[WARN] Tradução falhou: {str(e)[:100]}")
                return None

    async def detectar_idioma(self, texto: str) -> str:
        """
        Detecta o idioma do texto usando o melhor modelo disponível.

        Args:
            texto: Texto para detectar idioma

        Returns:
            Código do idioma (pt, en, es, etc) ou 'unknown'
        """
        if not texto or len(texto.strip()) < 10:
            return "unknown"

        prompt = f"""Detect the language of the following text and return ONLY the ISO 639-1 language code (like 'pt', 'en', 'es', 'it', 'fr', 'de', 'ar', 'ja', 'ko', 'he', etc).

Text to analyze:
{texto[:500]}"""

        # Usar modelo rápido para detecção de idioma
        modelos_rapidos = self.gerenciador.obter_melhores_para_tarefa(
            tarefa="velocidade",
            limite=3,
            categoria_preco="ultra_economico"
        )

        for modelo in modelos_rapidos:
            try:
                resultado = await self._chamar_modelo_base(
                    modelo["id"],
                    prompt,
                    temperature=0.1,
                    max_tokens=10
                )
                # Extrair código de idioma (geralmente 2 letras)
                codigo = resultado.strip().lower()[:2]
                if codigo in [
                    "pt", "en", "es", "fr", "de", "it", "ar", "ja", "ko", "he"
                ]:
                    return codigo
            except Exception:
                continue

        return "unknown"

    async def analisar_fonte(
        self,
        titulo: str,
        descricao: str,
        url: str,
        modo: str = "balanceado"
    ) -> Dict[str, Any]:
        """
        Analisa uma fonte usando o melhor modelo para análise.

        Args:
            titulo: Título da fonte
            descricao: Descrição da fonte
            url: URL da fonte
            modo: "gratuito", "balanceado" ou "premium"

        Returns:
            Dicionário com análise da fonte
        """
        # Mapear modo para categoria de preço
        mapa_modo_categoria = {
            "gratuito": "free",
            "balanceado": "ultra_economico",
            "premium": "balanceado"
        }

        categoria = mapa_modo_categoria.get(modo, "ultra_economico")

        prompt = f"""Analyze the following research source and classify it:

Title: {titulo[:200]}
Description: {descricao[:500] if descricao else 'N/A'}
URL: {url}

Respond in JSON format (no markdown):
{{
    "tipo_fonte": "academica|governamental|tecnico|caso_sucesso|outro",
    "tem_implementacao": true|false,
    "tem_metricas": true|false,
    "confianca": 0.0-1.0
}}"""

        if self.usar_fallback and self.chamador_inteligente:
            resultado = await self.chamador_inteligente.chamar_modelo_ideal(
                prompt=prompt,
                tarefa="analise",
                categoria_preco=categoria
            )

            if resultado["sucesso"]:
                import json
                try:
                    return json.loads(resultado["resposta"])
                except json.JSONDecodeError:
                    return {
                        "tipo_fonte": "outro",
                        "tem_implementacao": False,
                        "tem_metricas": False,
                        "confianca": 0.5
                    }
        else:
            # Fallback heurístico
            return {
                "tipo_fonte": "outro",
                "tem_implementacao": False,
                "tem_metricas": False,
                "confianca": 0.5
            }

    def obter_estatisticas(self) -> Dict[str, Any]:
        """
        Obtém estatísticas de uso do cliente.

        Returns:
            Dicionário com estatísticas
        """
        if self.chamador_inteligente:
            return self.chamador_inteligente.obter_metricas()
        else:
            return {
                "total_chamadas": 0,
                "mensagem": "Fallback automático desabilitado"
            }

    def obter_custos_estimados(
        self,
        num_traducoes: int,
        categoria_preco: str = "free"
    ) -> Dict[str, Any]:
        """
        Estima custos para um número de traduções.

        Args:
            num_traducoes: Número de traduções estimadas
            categoria_preco: Categoria de preço a usar

        Returns:
            Dicionário com estimativas
        """
        modelos = self.obter_melhores_modelos_traducao(categoria_preco, limite=1)

        if not modelos:
            return {
                "erro": "Nenhum modelo disponível"
            }

        modelo = modelos[0]

        # Estimativa: ~200 tokens por tradução (título + descrição)
        tokens_por_traducao = 200
        total_tokens = num_traducoes * tokens_por_traducao

        # Custo (prompt + completion)
        custo_por_1k = modelo["pricing"]["total_per_1k"]
        custo_total_usd = (total_tokens / 1000) * custo_por_1k
        custo_total_brl = custo_total_usd * 5.0  # Conversão aproximada

        # Tempo estimado baseado no score de velocidade
        # Score 10 = ~1s, Score 5 = ~3s, Score 1 = ~8s
        segundos_por_traducao = max(1, 10 - modelo["scores"]["velocidade"])
        tempo_total_segundos = num_traducoes * segundos_por_traducao

        return {
            "modelo_recomendado": modelo["name"],
            "modelo_id": modelo["id"],
            "num_traducoes": num_traducoes,
            "tokens_estimados": total_tokens,
            "custo_usd": round(custo_total_usd, 6),
            "custo_brl": round(custo_total_brl, 4),
            "tempo_estimado_segundos": tempo_total_segundos,
            "tempo_estimado_minutos": round(tempo_total_segundos / 60, 1),
            "categoria_preco": categoria_preco,
            "scores": modelo["scores"]
        }


# Para facilitar migração gradual, manter compatibilidade com código antigo
class OpenRouterClient(OpenRouterClientV2):
    """
    Alias para manter compatibilidade com código existente.
    Redireciona para OpenRouterClientV2.
    """
    pass


if __name__ == "__main__":
    # Teste do cliente V2
    import asyncio

    async def teste():
        print("🧪 Testando OpenRouter Client V2\n")

        async with OpenRouterClientV2() as client:
            # Teste 1: Obter melhores modelos para tradução
            print("🌍 Melhores modelos para tradução (gratuitos):")
            modelos_traducao = client.obter_melhores_modelos_traducao("free", limite=3)
            for i, modelo in enumerate(modelos_traducao, 1):
                print(f"   {i}. {modelo['name']}")
                print(f"      Score: {modelo['scores']['traducao']}/10")
                print(f"      Velocidade: {modelo['scores']['velocidade']}/10")
                print(f"      Preço: ${modelo['pricing']['total_per_1k']:.6f}/1K tokens")
            print()

            # Teste 2: Estimativa de custos
            print("💰 Estimativa de custos para 100 traduções:")
            estimativa = client.obter_custos_estimados(100, "free")
            print(f"   Modelo: {estimativa['modelo_recomendado']}")
            print(f"   Custo: ${estimativa['custo_usd']:.6f} (≈R${estimativa['custo_brl']:.4f})")
            print(f"   Tempo: {estimativa['tempo_estimado_minutos']} minutos")
            print()

            # Teste 3: Tradução com fallback
            print("📝 Teste de tradução com fallback:")
            texto_teste = "Innovation policy frameworks"
            traducao = await client.traduzir_texto(texto_teste, "pt", "free")
            if traducao:
                print(f"   Original: {texto_teste}")
                print(f"   Tradução: {traducao}")
            print()

            # Teste 4: Estatísticas
            print("📊 Estatísticas de uso:")
            stats = client.obter_estatisticas()
            print(f"   Total de chamadas: {stats.get('total_chamadas', 0)}")
            if 'taxa_sucesso' in stats:
                print(f"   Taxa de sucesso: {stats['taxa_sucesso']*100:.1f}%")

    asyncio.run(teste())
