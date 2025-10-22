# -*- coding: utf-8 -*-
"""
Schemas Pydantic para requests/responses da API
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ===== Request Schemas =====

class ResultadoCreate(BaseModel):
    """Schema para criar um novo resultado manualmente"""
    falha_id: int
    titulo: str
    descricao: Optional[str] = None
    fonte_url: str
    fonte_tipo: Optional[str] = None
    pais_origem: Optional[str] = None
    idioma: str = "pt"
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)


class ResultadoUpdate(BaseModel):
    """Schema para atualizar um resultado"""
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    fonte_tipo: Optional[str] = None
    pais_origem: Optional[str] = None


class PesquisaIniciar(BaseModel):
    """Schema para iniciar pesquisas"""
    falhas_ids: Optional[List[int]] = None  # Se None, pesquisa todas
    idiomas: Optional[List[str]] = None  # Se None, usa todos configurados
    ferramentas: Optional[List[str]] = None  # Se None, usa todas
    prioridade: int = 0


class PesquisaCustom(BaseModel):
    """Schema para pesquisa customizada"""
    falha_id: int
    instrucoes: str
    idiomas: List[str] = ["pt", "en"]
    ferramentas: List[str] = ["perplexity", "jina", "deep_research"]
    queries_customizadas: Optional[List[str]] = None


# ===== Response Schemas =====

class FalhaResponse(BaseModel):
    """Response de falha de mercado"""
    id: int
    titulo: str
    pilar: str
    descricao: str
    dica_busca: str


class ResultadoResponse(BaseModel):
    """Response de resultado de pesquisa"""
    id: int
    falha_id: int
    titulo: str
    descricao: Optional[str]
    fonte_url: str
    fonte_tipo: Optional[str]
    pais_origem: Optional[str]
    idioma: str
    confidence_score: float
    num_ocorrencias: int
    ferramenta_origem: str
    criado_em: datetime
    atualizado_em: datetime


class FalhaComResultados(FalhaResponse):
    """Response de falha com seus resultados"""
    resultados: List[ResultadoResponse]
    total_resultados: int


class StatusPesquisa(BaseModel):
    """Response de status do processamento"""
    ativo: bool
    porcentagem: float
    mensagem: str
    total_pendentes: int
    total_processando: int
    total_concluidas: int
    total_erros: int


class JobResponse(BaseModel):
    """Response de job de pesquisa iniciado"""
    job_id: str
    status: str
    queries_criadas: int
    tempo_estimado_minutos: int


class EstatisticasResponse(BaseModel):
    """Response de estatisticas gerais"""
    total_falhas: int
    total_resultados: int
    pesquisas_concluidas: int
    pesquisas_pendentes: int
    confidence_medio: float


class EstatisticasFalhaResponse(BaseModel):
    """Response de estatisticas de uma falha"""
    falha_id: int
    falha_titulo: str
    total_resultados: int
    confidence_medio: float
    top_paises: List[dict]
    idiomas: List[dict]
