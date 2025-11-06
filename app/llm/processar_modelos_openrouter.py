#!/usr/bin/env python3
"""
Script para processar modelos da OpenRouter e adicionar metadados inteligentes.
Atualizado em: 2025-11-06

Sistema de scoring granular:
- Tier S (9.0-10.0): Modelos top-tier, estado da arte
- Tier A (7.5-8.9): Modelos excelentes, altamente recomendados
- Tier B (6.0-7.4): Modelos bons, confiáveis
- Tier C (4.5-5.9): Modelos medianos, uso específico
- Tier D (3.0-4.4): Modelos básicos, limitados
- Tier E (0.0-2.9): Modelos fracos ou inadequados
"""

import json
from datetime import datetime
from typing import Dict, List, Any
import re


# Benchmarks conhecidos (baseado em dados públicos)
BENCHMARK_TIERS = {
    # Tier S - Estado da arte
    "tier_s": [
        "gpt-4-turbo", "gpt-4o", "claude-3.5-sonnet", "claude-3-opus",
        "gemini-1.5-pro", "gemini-2.0-flash-thinking", "o1", "o3-mini",
        "deepseek-v3", "qwen-2.5-72b", "llama-3.3-70b"
    ],
    # Tier A - Excelentes
    "tier_a": [
        "gpt-4o-mini", "claude-3-sonnet", "claude-3-haiku",
        "gemini-1.5-flash", "gemini-flash-1.5", "mistral-large",
        "llama-3.1-405b", "qwen-2-72b", "mixtral-8x22b",
        "deepseek-r1", "grok-3"
    ],
    # Tier B - Bons
    "tier_b": [
        "gpt-3.5-turbo", "claude-2", "gemini-pro",
        "llama-3.1-70b", "llama-3-70b", "mixtral-8x7b",
        "mistral-medium", "gemma-2-27b", "qwen-1.5-72b"
    ],
    # Tier C - Medianos
    "tier_c": [
        "llama-3-8b", "llama-2-70b", "mistral-7b",
        "gemma-7b", "phi-3", "yi-34b"
    ]
}


def identificar_tier_modelo(model_id: str, name: str) -> str:
    """Identifica o tier do modelo baseado em benchmarks conhecidos"""
    model_lower = (model_id + " " + name).lower()

    for tier, modelos in BENCHMARK_TIERS.items():
        for modelo_ref in modelos:
            if modelo_ref.replace("-", " ") in model_lower or modelo_ref.replace(" ", "-") in model_lower:
                return tier

    return "tier_d"  # Padrão para modelos desconhecidos


def calcular_score_traducao(model: Dict[str, Any]) -> float:
    """
    Calcula score de adequação para tradução (0.0-10.0).
    Sistema granular baseado em:
    - Tier do modelo (benchmarks conhecidos)
    - Tamanho e arquitetura
    - Context window
    - Capacidade multilíngue
    """
    model_id = model["id"].lower()
    name = model["name"].lower()
    description = model.get("description", "").lower()
    context = model.get("context_length", 0)

    # Base score por tier
    tier = identificar_tier_modelo(model_id, name)
    tier_scores = {
        "tier_s": 8.5,
        "tier_a": 7.2,
        "tier_b": 5.8,
        "tier_c": 4.2,
        "tier_d": 2.5
    }
    score = tier_scores.get(tier, 2.5)

    # Ajustes por características específicas

    # 1. Tamanho do modelo (granular)
    if "405b" in model_id or "405b" in name:
        score += 1.2
    elif any(size in model_id or size in name for size in ["180b", "175b"]):
        score += 1.0
    elif any(size in model_id or size in name for size in ["70b", "72b"]):
        score += 0.8
    elif any(size in model_id or size in name for size in ["30b", "34b"]):
        score += 0.5
    elif any(size in model_id or size in name for size in ["20b", "27b"]):
        score += 0.3
    elif any(size in model_id or size in name for size in ["13b", "14b"]):
        score += 0.1
    elif any(size in model_id or size in name for size in ["7b", "8b"]):
        score -= 0.3
    elif any(size in model_id or size in name for size in ["3b", "1b"]):
        score -= 0.8

    # 2. Context window (impacta capacidade de tradução com contexto)
    if context >= 1000000:
        score += 0.8
    elif context >= 200000:
        score += 0.6
    elif context >= 128000:
        score += 0.4
    elif context >= 32000:
        score += 0.2
    elif context < 8000:
        score -= 0.5

    # 3. Capacidade multilíngue explícita
    multilingual_indicators = [
        "multilingual", "multi-lingual", "translation",
        "multiple languages", "language support", "polyglot"
    ]
    if any(term in description for term in multilingual_indicators):
        score += 0.6

    # 4. Tipo de instrução
    if "instruct" in model_id or "instruct" in name:
        score += 0.4
    elif "chat" in model_id or "chat" in name:
        score += 0.2

    # 5. Modelos especializados (bônus ou penalidade)
    if any(term in description for term in ["code generation", "coding", "code-specific"]):
        score -= 0.4  # Menos adequado para tradução geral
    if any(term in description for term in ["vision", "image", "multimodal"]):
        score -= 0.3  # Foco dividido

    # 6. Versões específicas (refinamentos)
    if "turbo" in model_id or "turbo" in name:
        score += 0.3
    if "preview" in model_id or "preview" in name:
        score -= 0.2  # Versões preview podem ser instáveis

    # 7. Provider quality adjustments
    if "openai" in model_id:
        score += 0.3
    elif "anthropic" in model_id or "claude" in name:
        score += 0.4
    elif "google" in model_id or "gemini" in name:
        score += 0.3
    elif "meta" in model_id or "llama" in name:
        score += 0.2

    # 8. Modelos free têm mais rate limits (pequena penalidade)
    if ":free" in model_id:
        score -= 0.2

    return round(min(10.0, max(0.0, score)), 2)


def calcular_score_analise(model: Dict[str, Any]) -> float:
    """
    Calcula score de adequação para análise e raciocínio (0.0-10.0).
    Sistema granular baseado em:
    - Tier do modelo
    - Capacidade de raciocínio
    - Context window para análise longa
    - Benchmarks de raciocínio
    """
    model_id = model["id"].lower()
    name = model["name"].lower()
    description = model.get("description", "").lower()
    context = model.get("context_length", 0)

    # Base score por tier (análise requer modelos melhores)
    tier = identificar_tier_modelo(model_id, name)
    tier_scores = {
        "tier_s": 9.0,
        "tier_a": 7.5,
        "tier_b": 6.0,
        "tier_c": 4.5,
        "tier_d": 2.8
    }
    score = tier_scores.get(tier, 2.8)

    # 1. Modelos com capacidade de raciocínio avançada
    reasoning_models = [
        "o1", "o3", "deepseek-r1", "deepseek-reasoner",
        "thinking", "reasoning", "r1"
    ]
    if any(term in model_id or term in name for term in reasoning_models):
        score += 1.0

    # 2. Descrição menciona raciocínio/análise
    reasoning_terms = [
        "reasoning", "analysis", "thinking", "chain-of-thought",
        "step-by-step", "complex reasoning", "problem solving"
    ]
    reasoning_count = sum(1 for term in reasoning_terms if term in description)
    score += min(0.8, reasoning_count * 0.2)

    # 3. Context window (crítico para análise de documentos)
    if context >= 1000000:
        score += 1.0
    elif context >= 500000:
        score += 0.8
    elif context >= 200000:
        score += 0.6
    elif context >= 128000:
        score += 0.4
    elif context >= 32000:
        score += 0.2
    elif context < 16000:
        score -= 0.5

    # 4. Tamanho do modelo (para raciocínio complexo)
    if "405b" in model_id or "405b" in name:
        score += 1.0
    elif any(size in model_id or size in name for size in ["180b", "175b"]):
        score += 0.8
    elif any(size in model_id or size in name for size in ["70b", "72b"]):
        score += 0.6
    elif any(size in model_id or size in name for size in ["30b", "34b"]):
        score += 0.3
    elif any(size in model_id or size in name for size in ["7b", "8b"]):
        score -= 0.4
    elif any(size in model_id or size in name for size in ["3b", "1b"]):
        score -= 0.8

    # 5. Modelos especializados em análise
    if "research" in model_id or "research" in name:
        score += 0.5
    if "analyst" in model_id or "analysis" in name:
        score += 0.4

    # 6. Penalidades
    if any(term in description for term in ["chat only", "conversation", "casual"]):
        score -= 0.3
    if "mini" in model_id or "lite" in model_id:
        score -= 0.4

    return round(min(10.0, max(0.0, score)), 2)


def calcular_score_velocidade(model: Dict[str, Any]) -> float:
    """
    Calcula score de velocidade (0.0-10.0).
    Sistema granular baseado em:
    - Tamanho do modelo (menor = mais rápido)
    - Indicadores de otimização
    - Provider
    - Arquitetura
    """
    model_id = model["id"].lower()
    name = model["name"].lower()
    description = model.get("description", "").lower()

    # Base score - assume mediano
    score = 5.0

    # 1. Tamanho do modelo (MAIOR IMPACTO em velocidade)
    if any(size in model_id or size in name for size in ["1b", "3b"]):
        score += 3.0
    elif any(size in model_id or size in name for size in ["7b", "8b"]):
        score += 2.5
    elif any(size in model_id or size in name for size in ["13b", "14b"]):
        score += 1.5
    elif any(size in model_id or size in name for size in ["20b", "27b"]):
        score += 0.5
    elif any(size in model_id or size in name for size in ["30b", "34b"]):
        score -= 0.5
    elif any(size in model_id or size in name for size in ["70b", "72b"]):
        score -= 1.5
    elif any(size in model_id or size in name for size in ["180b", "175b"]):
        score -= 2.5
    elif any(size in model_id or size in name for size in ["405b"]):
        score -= 3.0

    # 2. Indicadores explícitos de velocidade
    speed_terms = ["fast", "turbo", "speed", "quick", "instant", "flash", "lite", "mini", "rapid"]
    speed_count = sum(1 for term in speed_terms if term in model_id or term in name)
    score += min(2.0, speed_count * 0.8)

    # 3. Descrição menciona velocidade/eficiência
    if any(term in description for term in ["fast", "low latency", "efficient", "optimized", "quick"]):
        score += 0.6

    # 4. Providers conhecidos por velocidade
    if "gemini-flash" in model_id:
        score += 1.5
    elif "gpt-4o-mini" in model_id or "gpt-3.5" in model_id:
        score += 1.2
    elif "claude-haiku" in model_id or "claude-3-haiku" in model_id:
        score += 1.0
    elif "grok" in model_id and "fast" in model_id:
        score += 1.0

    # 5. Arquitetura (se disponível na descrição)
    if "mamba" in description:
        score += 0.5  # Arquitetura eficiente
    if "moe" in description or "mixture of experts" in description:
        score += 0.3  # MoE pode ser mais eficiente

    # 6. Penalidades
    if "reasoning" in model_id or "thinking" in model_id:
        score -= 1.0  # Modelos de raciocínio são mais lentos
    if any(term in description for term in ["comprehensive", "thorough", "detailed"]):
        score -= 0.3

    # 7. Modelos preview/beta podem ser mais lentos
    if "preview" in model_id or "beta" in model_id:
        score -= 0.4

    return round(min(10.0, max(0.0, score)), 2)


def calcular_categoria_preco(prompt_price: float, completion_price: float) -> str:
    """
    Categoriza o modelo por faixa de preço.
    """
    total_price = prompt_price + completion_price

    if total_price == 0:
        return "free"
    elif total_price < 0.0001:
        return "ultra_economico"
    elif total_price < 0.0005:
        return "economico"
    elif total_price < 0.002:
        return "balanceado"
    elif total_price < 0.01:
        return "premium"
    else:
        return "ultra_premium"


def calcular_custo_beneficio(model: Dict[str, Any], metadata: Dict[str, Any]) -> float:
    """
    Calcula score geral de custo-benefício (0.0-10.0).
    Fórmula refinada que considera:
    - Qualidade média do modelo
    - Preço
    - Adequação para casos de uso comuns
    """
    prompt_price = float(model["pricing"]["prompt"])
    completion_price = float(model["pricing"]["completion"])
    total_price = prompt_price + completion_price

    # Score médio de qualidade (ponderado)
    # Tradução e análise têm peso maior (mais comuns)
    quality_score = (
        metadata["scores"]["traducao"] * 0.35 +
        metadata["scores"]["analise"] * 0.35 +
        metadata["scores"]["velocidade"] * 0.30
    )

    # Modelos gratuitos têm excelente custo-benefício se tiverem qualidade razoável
    if total_price == 0:
        # Score máximo para gratuitos de alta qualidade
        if quality_score >= 7.5:
            return 10.0
        elif quality_score >= 6.0:
            return 9.5
        elif quality_score >= 4.5:
            return 9.0
        else:
            return 8.0  # Mesmo gratuito, se for fraco não é bom custo-benefício

    # Para modelos pagos, calcular relação qualidade/preço
    # Normalizar preço em escala logarítmica para melhor distribuição
    import math
    if total_price > 0:
        # Log scale: $0.00001 = -5, $0.0001 = -4, $0.001 = -3, $0.01 = -2, $0.1 = -1
        log_price = math.log10(total_price)

        # Normalizar para escala 0-10 (preços mais altos = score menor)
        # -6 (muito barato) a -1 (muito caro)
        price_score = max(0, min(10, 10 + log_price))  # Inverter: preço alto = score baixo

        # Custo-benefício = média ponderada de qualidade e preço
        # Qualidade tem peso 60%, preço tem peso 40%
        cost_benefit = (quality_score * 0.6) + (price_score * 0.4)
    else:
        cost_benefit = quality_score

    return round(min(10.0, max(0.0, cost_benefit)), 2)


def identificar_modelos_similares(model: Dict[str, Any], all_models: List[Dict[str, Any]]) -> List[str]:
    """
    Identifica modelos similares para fallback.
    Baseado em: mesmo provider, categoria de preço similar, scores similares.
    """
    model_id = model["id"]
    provider = model_id.split("/")[0] if "/" in model_id else ""

    prompt_price = float(model["pricing"]["prompt"])
    completion_price = float(model["pricing"]["completion"])
    total_price = prompt_price + completion_price

    similar = []

    for other_model in all_models:
        if other_model["id"] == model_id:
            continue

        other_provider = other_model["id"].split("/")[0] if "/" in other_model["id"] else ""
        other_prompt = float(other_model["pricing"]["prompt"])
        other_completion = float(other_model["pricing"]["completion"])
        other_total = other_prompt + other_completion

        # Critérios de similaridade
        same_provider = provider == other_provider
        similar_price = abs(total_price - other_total) < 0.001
        similar_context = abs(model.get("context_length", 0) - other_model.get("context_length", 0)) < 50000

        # Se pelo menos 2 critérios forem atendidos
        if sum([same_provider, similar_price, similar_context]) >= 2:
            similar.append(other_model["id"])

    return similar[:5]  # Máximo 5 modelos similares


def processar_modelos(input_file: str, output_file: str):
    """
    Processa os modelos da OpenRouter e adiciona metadados.
    """
    print(f"📖 Lendo modelos de {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    models = data["data"]
    print(f"✅ {len(models)} modelos carregados")

    print("🔍 Processando e adicionando metadados...")
    processed_models = []

    for i, model in enumerate(models, 1):
        if i % 50 == 0:
            print(f"   Processando modelo {i}/{len(models)}...")

        # Calcular scores
        score_traducao = calcular_score_traducao(model)
        score_analise = calcular_score_analise(model)
        score_velocidade = calcular_score_velocidade(model)

        # Extrair preços
        prompt_price = float(model["pricing"].get("prompt", 0))
        completion_price = float(model["pricing"].get("completion", 0))
        request_price = float(model["pricing"].get("request", 0))

        # Categoria de preço
        categoria_preco = calcular_categoria_preco(prompt_price, completion_price)

        # Criar metadados
        metadata = {
            "id": model["id"],
            "name": model["name"],
            "description": model["description"],
            "context_length": model.get("context_length", 0),
            "max_completion_tokens": model.get("top_provider", {}).get("max_completion_tokens", 0),
            "pricing": {
                "prompt": prompt_price,
                "completion": completion_price,
                "request": request_price,
                "total_per_1k": prompt_price + completion_price,
                "categoria": categoria_preco
            },
            "scores": {
                "traducao": score_traducao,
                "analise": score_analise,
                "velocidade": score_velocidade,
                "custo_beneficio": 0.0  # Será calculado após
            },
            "architecture": model.get("architecture", {}),
            "supported_parameters": model.get("supported_parameters", []),
            "fallback_similar": []  # Será preenchido após
        }

        processed_models.append(metadata)

    print("💰 Calculando scores de custo-benefício...")
    for model in processed_models:
        # Encontrar o modelo original para passar ao cálculo
        original = next(m for m in models if m["id"] == model["id"])
        model["scores"]["custo_beneficio"] = calcular_custo_beneficio(original, model)

    print("🔗 Identificando modelos similares para fallback...")
    for i, model in enumerate(processed_models):
        original = next(m for m in models if m["id"] == model["id"])
        model["fallback_similar"] = identificar_modelos_similares(original, models)

    # Ordenar por custo-benefício
    processed_models.sort(key=lambda x: x["scores"]["custo_beneficio"], reverse=True)

    # Criar estrutura final
    output_data = {
        "metadata": {
            "ultima_atualizacao": datetime.now().isoformat(),
            "data_atualizacao_legivel": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_modelos": len(processed_models),
            "versao_schema": "1.1"
        },
        "categorias": {
            "free": [m for m in processed_models if m["pricing"]["categoria"] == "free"],
            "ultra_economico": [m for m in processed_models if m["pricing"]["categoria"] == "ultra_economico"],
            "economico": [m for m in processed_models if m["pricing"]["categoria"] == "economico"],
            "balanceado": [m for m in processed_models if m["pricing"]["categoria"] == "balanceado"],
            "premium": [m for m in processed_models if m["pricing"]["categoria"] == "premium"],
            "ultra_premium": [m for m in processed_models if m["pricing"]["categoria"] == "ultra_premium"]
        },
        "top_models": {
            "traducao": sorted(processed_models, key=lambda x: x["scores"]["traducao"], reverse=True)[:10],
            "analise": sorted(processed_models, key=lambda x: x["scores"]["analise"], reverse=True)[:10],
            "velocidade": sorted(processed_models, key=lambda x: x["scores"]["velocidade"], reverse=True)[:10],
            "custo_beneficio": processed_models[:10]  # Já ordenado por custo-benefício
        },
        "todos_modelos": processed_models
    }

    print(f"💾 Salvando em {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("\n📊 Estatísticas:")
    print(f"   Total de modelos: {len(processed_models)}")
    print(f"   Modelos gratuitos: {len(output_data['categorias']['free'])}")
    print(f"   Modelos ultra econômicos: {len(output_data['categorias']['ultra_economico'])}")
    print(f"   Modelos econômicos: {len(output_data['categorias']['economico'])}")
    print(f"   Modelos balanceados: {len(output_data['categorias']['balanceado'])}")
    print(f"   Modelos premium: {len(output_data['categorias']['premium'])}")
    print(f"   Modelos ultra premium: {len(output_data['categorias']['ultra_premium'])}")

    print("\n🏆 Top 10 Custo-Benefício:")
    for i, model in enumerate(output_data["top_models"]["custo_beneficio"][:10], 1):
        print(f"   {i}. {model['name']}")
        print(f"      Custo-Benefício: {model['scores']['custo_beneficio']}/10")
        print(f"      Tradução: {model['scores']['traducao']}/10 | Análise: {model['scores']['analise']}/10 | Velocidade: {model['scores']['velocidade']}/10")
        print(f"      Preço: ${model['pricing']['total_per_1k']:.6f}/1K tokens")
        print()

    print("\n🌍 Top 5 Tradução:")
    for i, model in enumerate(output_data["top_models"]["traducao"][:5], 1):
        print(f"   {i}. {model['name']} - {model['scores']['traducao']}/10 (${model['pricing']['total_per_1k']:.6f}/1K)")

    print("\n🔬 Top 5 Análise:")
    for i, model in enumerate(output_data["top_models"]["analise"][:5], 1):
        print(f"   {i}. {model['name']} - {model['scores']['analise']}/10 (${model['pricing']['total_per_1k']:.6f}/1K)")

    print("\n⚡ Top 5 Velocidade:")
    for i, model in enumerate(output_data["top_models"]["velocidade"][:5], 1):
        print(f"   {i}. {model['name']} - {model['scores']['velocidade']}/10 (${model['pricing']['total_per_1k']:.6f}/1K)")

    print("\n✅ Processamento concluído!")


if __name__ == "__main__":
    import sys

    input_file = sys.argv[1] if len(sys.argv) > 1 else "/tmp/openrouter_models.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "app/llm/modelos_openrouter.json"

    processar_modelos(input_file, output_file)
