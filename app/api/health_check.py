# -*- coding: utf-8 -*-
"""
Endpoints para health check do sistema
Testa a saúde de todos os serviços e APIs
"""
import asyncio
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
from datetime import datetime

from app.config import settings
from app.integracao.perplexity_api import PerplexityClient
from app.integracao.jina_api import JinaClient
from app.integracao.deep_research_mcp import DeepResearchClient

router = APIRouter(tags=["Health Check"])


class HealthChecker:
    """Classe para testar saúde do sistema"""

    def __init__(self):
        self.results: Dict[str, Any] = {}

    async def test_perplexity(self) -> Dict[str, Any]:
        """Testa Perplexity API"""
        try:
            client = PerplexityClient(settings.PERPLEXITY_API_KEY)

            # Fazer uma pesquisa simples
            resultado = await client.pesquisar(
                query="Qual é a capital da França?",
                idioma="pt",
                max_resultados=1
            )

            if resultado and len(resultado) > 0:
                return {
                    "status": "ok",
                    "servico": "Perplexity AI",
                    "mensagem": "Perplexity API respondendo normalmente",
                    "detalhes": f"Retornou {len(resultado)} resultado(s)",
                    "tempo_teste": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "warning",
                    "servico": "Perplexity AI",
                    "mensagem": "Perplexity respondeu mas sem resultados",
                    "detalhes": "API retornou vazio",
                    "tempo_teste": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "status": "error",
                "servico": "Perplexity AI",
                "mensagem": "Perplexity API indisponível",
                "detalhes": str(e),
                "tempo_teste": datetime.now().isoformat()
            }

    async def test_jina(self) -> Dict[str, Any]:
        """Testa Jina API"""
        try:
            client = JinaClient(settings.JINA_API_KEY)

            # Fazer uma busca simples
            resultado = await client.search_web(
                query="python programming",
                idioma="en",
                max_resultados=3
            )

            if resultado and len(resultado) > 0:
                return {
                    "status": "ok",
                    "servico": "Jina AI",
                    "mensagem": "Jina API respondendo normalmente",
                    "detalhes": f"Retornou {len(resultado)} resultado(s)",
                    "tempo_teste": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "warning",
                    "servico": "Jina AI",
                    "mensagem": "Jina respondeu mas sem resultados",
                    "detalhes": "API retornou vazio",
                    "tempo_teste": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "status": "error",
                "servico": "Jina AI",
                "mensagem": "Jina API indisponível",
                "detalhes": str(e),
                "tempo_teste": datetime.now().isoformat()
            }

    async def test_deep_research(self) -> Dict[str, Any]:
        """Testa Deep Research MCP"""
        try:
            client = DeepResearchClient()

            # Teste básico de inicialização
            resultado = await client.pesquisar(
                query="machine learning applications",
                fontes="web",
                max_resultados=2
            )

            if resultado and len(resultado) > 0:
                return {
                    "status": "ok",
                    "servico": "Deep Research",
                    "mensagem": "Deep Research MCP respondendo normalmente",
                    "detalhes": f"Retornou {len(resultado)} resultado(s)",
                    "tempo_teste": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "warning",
                    "servico": "Deep Research",
                    "mensagem": "Deep Research respondeu mas sem resultados",
                    "detalhes": "MCP retornou vazio",
                    "tempo_teste": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "status": "error",
                "servico": "Deep Research",
                "mensagem": "Deep Research MCP indisponível",
                "detalhes": str(e),
                "tempo_teste": datetime.now().isoformat()
            }

    async def test_database(self) -> Dict[str, Any]:
        """Testa conexão com banco de dados"""
        try:
            from app.database import db

            # Tentar fazer uma query simples
            resultado = await db.fetch_one(
                "SELECT COUNT(*) as total FROM falhas_mercado"
            )

            if resultado and resultado["total"] > 0:
                return {
                    "status": "ok",
                    "servico": "Database (SQLite)",
                    "mensagem": "Banco de dados respondendo normalmente",
                    "detalhes": f"Total de falhas: {resultado['total']}",
                    "tempo_teste": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "warning",
                    "servico": "Database (SQLite)",
                    "mensagem": "Banco de dados vazio",
                    "detalhes": "Nenhum registro encontrado",
                    "tempo_teste": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "status": "error",
                "servico": "Database (SQLite)",
                "mensagem": "Banco de dados indisponível",
                "detalhes": str(e),
                "tempo_teste": datetime.now().isoformat()
            }

    async def run_all_tests(self) -> Dict[str, Any]:
        """Executa todos os testes em paralelo"""
        # Executar testes em paralelo
        resultados = await asyncio.gather(
            self.test_database(),
            self.test_perplexity(),
            self.test_jina(),
            self.test_deep_research(),
            return_exceptions=True
        )

        # Processar resultados
        testes = []
        status_geral = "ok"

        for resultado in resultados:
            if isinstance(resultado, Exception):
                testes.append({
                    "status": "error",
                    "servico": "Teste",
                    "mensagem": "Erro ao executar teste",
                    "detalhes": str(resultado)
                })
                status_geral = "error"
            else:
                testes.append(resultado)
                if resultado["status"] == "error":
                    status_geral = "error"
                elif resultado["status"] == "warning" and status_geral == "ok":
                    status_geral = "warning"

        # Contar status
        ok_count = sum(1 for t in testes if t["status"] == "ok")
        warning_count = sum(1 for t in testes if t["status"] == "warning")
        error_count = sum(1 for t in testes if t["status"] == "error")

        return {
            "status_geral": status_geral,
            "timestamp": datetime.now().isoformat(),
            "resumo": {
                "total_testes": len(testes),
                "sucesso": ok_count,
                "avisos": warning_count,
                "erros": error_count
            },
            "testes": testes
        }


@router.get("/health")
async def health_simple():
    """Health check simples"""
    return {
        "status": "ok",
        "mensagem": "Sistema operacional"
    }


@router.post("/health/check")
async def health_check_completo():
    """
    Executa health check completo de todos os serviços
    Testa: Database, Perplexity, Jina, Deep Research
    """
    checker = HealthChecker()
    resultado = await checker.run_all_tests()
    return resultado


@router.get("/health/status")
async def get_health_status():
    """
    Retorna status rápido do sistema (sem testes)
    """
    try:
        from app.database import db

        # Verificar banco de dados
        resultado = await db.fetch_one(
            "SELECT COUNT(*) as total FROM falhas_mercado"
        )

        return {
            "status": "ok",
            "sistema": "operacional",
            "database": "conectado",
            "falhas_mapeadas": resultado["total"] if resultado else 0
        }
    except Exception as e:
        return {
            "status": "error",
            "sistema": "degradado",
            "database": "desconectado",
            "erro": str(e)
        }
