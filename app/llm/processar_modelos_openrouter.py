#!/usr/bin/env python3
"""
Script para processar modelos da OpenRouter e adicionar metadados inteligentes.
Atualizado em: 2025-11-06
"""

import json
from datetime import datetime
from typing import Dict, List, Any
import re


def calcular_score_traducao(model: Dict[str, Any]) -> float:
    """
    Calcula score de adequação para tradução (0.0-10.0).
    Baseado em: capacidade multilíngue, context window, benchmarks conhecidos.
    """
    score = 5.0  # Base
    model_id = model["id"].lower()
    name = model["name"].lower()
    description = model.get("description", "").lower()

    # Modelos conhecidos por excelência em tradução
    excellent_for_translation = [
        "claude", "gpt-4", "gpt-3.5", "llama-3", "gemini", "gemma",
        "mistral", "mixtral", "qwen", "deepseek", "command"
    ]

    for keyword in excellent_for_translation:
        if keyword in model_id or keyword in name:
            score += 2.0
            break

    # Modelos multilíngues ou com suporte explícito
    if any(term in description for term in ["multilingual", "translation", "multiple languages", "language support"]):
        score += 1.5

    # Context window maior = melhor para contexto de tradução
    context = model.get("context_length", 0)
    if context >= 100000:
        score += 1.5
    elif context >= 32000:
        score += 1.0
    elif context >= 8000:
        score += 0.5

    # Modelos maiores geralmente traduzem melhor
    if "405b" in model_id or "405b" in name:
        score += 1.0
    elif any(size in model_id or size in name for size in ["70b", "72b", "180b"]):
        score += 0.7
    elif any(size in model_id or size in name for size in ["13b", "27b", "30b", "34b"]):
        score += 0.3

    # Modelos "instruct" são melhores para seguir instruções de tradução
    if "instruct" in model_id or "instruct" in name:
        score += 0.5

    # Penalizar modelos muito especializados em outras tarefas
    if any(term in description for term in ["code only", "math only", "vision only"]):
        score -= 2.0

    return min(10.0, max(0.0, score))


def calcular_score_analise(model: Dict[str, Any]) -> float:
    """
    Calcula score de adequação para análise e raciocínio (0.0-10.0).
    Baseado em: capacidade de raciocínio, benchmarks, context window.
    """
    score = 5.0  # Base
    model_id = model["id"].lower()
    name = model["name"].lower()
    description = model.get("description", "").lower()

    # Modelos premium conhecidos por raciocínio
    premium_reasoning = [
        "gpt-4", "claude-3-opus", "claude-3.5-sonnet", "claude-3-sonnet",
        "gemini-1.5-pro", "gemini-2.0", "o1", "o3", "grok-3", "grok-4",
        "deepseek-r1", "qwen-2.5", "llama-3.3-70b", "llama-3.1-405b"
    ]

    for keyword in premium_reasoning:
        if keyword in model_id or keyword in name:
            score += 3.0
            break

    # Termos relacionados a raciocínio avançado
    if any(term in description for term in ["reasoning", "analysis", "thinking", "complex", "advanced", "agentic"]):
        score += 1.5

    # Context window maior = melhor para análise de documentos longos
    context = model.get("context_length", 0)
    if context >= 200000:
        score += 2.0
    elif context >= 100000:
        score += 1.5
    elif context >= 32000:
        score += 1.0

    # Modelos maiores têm melhor capacidade de raciocínio
    if "405b" in model_id or "405b" in name:
        score += 1.5
    elif any(size in model_id or size in name for size in ["70b", "72b", "180b"]):
        score += 1.0
    elif any(size in model_id or size in name for size in ["13b", "27b", "30b", "34b"]):
        score += 0.5

    return min(10.0, max(0.0, score))


def calcular_score_velocidade(model: Dict[str, Any]) -> float:
    """
    Calcula score de velocidade (0.0-10.0).
    Baseado em: tamanho do modelo, provider, termos como "fast", "turbo", etc.
    """
    score = 5.0  # Base
    model_id = model["id"].lower()
    name = model["name"].lower()
    description = model.get("description", "").lower()

    # Indicadores de velocidade no nome
    if any(term in model_id or term in name for term in ["fast", "turbo", "speed", "quick", "instant", "flash", "lite", "mini"]):
        score += 3.0

    # Modelos menores são mais rápidos
    if any(size in model_id or size in name for size in ["7b", "8b", "mini", "small", "lite"]):
        score += 2.0
    elif any(size in model_id or size in name for size in ["13b", "14b", "20b", "27b"]):
        score += 1.0
    elif any(size in model_id or size in name for size in ["70b", "72b"]):
        score -= 1.0
    elif any(size in model_id or size in name for size in ["180b", "405b"]):
        score -= 2.0

    # Providers conhecidos por velocidade
    if any(provider in model_id for provider in ["gemini-flash", "gpt-4o-mini", "claude-haiku", "grok-fast"]):
        score += 2.0

    # Termos relacionados à velocidade na descrição
    if any(term in description for term in ["fast", "efficient", "optimized", "quick", "low latency"]):
        score += 1.0

    return min(10.0, max(0.0, score))


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
    Maior = melhor relação qualidade/preço.
    """
    prompt_price = float(model["pricing"]["prompt"])
    completion_price = float(model["pricing"]["completion"])
    total_price = prompt_price + completion_price

    # Score médio de qualidade
    quality_score = (
        metadata["scores"]["traducao"] +
        metadata["scores"]["analise"] +
        metadata["scores"]["velocidade"]
    ) / 3

    # Modelos gratuitos têm excelente custo-benefício se tiverem qualidade razoável
    if total_price == 0:
        return min(10.0, quality_score * 1.5)

    # Para modelos pagos, calcular relação qualidade/preço
    # Normalizar preço (assumindo range típico de $0.00001 a $0.1)
    normalized_price = min(10.0, total_price * 1000)  # Escala para 0-10

    # Custo-benefício = qualidade / preço normalizado
    if normalized_price > 0:
        cost_benefit = (quality_score / normalized_price) * 10
    else:
        cost_benefit = quality_score

    return min(10.0, max(0.0, cost_benefit))


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
                "traducao": round(score_traducao, 2),
                "analise": round(score_analise, 2),
                "velocidade": round(score_velocidade, 2),
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
        model["scores"]["custo_beneficio"] = round(
            calcular_custo_beneficio(original, model), 2
        )

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
            "versao_schema": "1.0"
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

    print("\n🏆 Top 5 Custo-Benefício:")
    for i, model in enumerate(output_data["top_models"]["custo_beneficio"][:5], 1):
        print(f"   {i}. {model['name']}")
        print(f"      Score: {model['scores']['custo_beneficio']}/10")
        print(f"      Preço: ${model['pricing']['total_per_1k']:.6f}/1K tokens")
        print(f"      Categoria: {model['pricing']['categoria']}")
        print()

    print("✅ Processamento concluído!")


if __name__ == "__main__":
    import sys

    input_file = sys.argv[1] if len(sys.argv) > 1 else "/tmp/openrouter_models.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "app/llm/modelos_openrouter.json"

    processar_modelos(input_file, output_file)
