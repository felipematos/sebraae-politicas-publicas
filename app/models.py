# -*- coding: utf-8 -*-
"""
Models Pydantic para validacao de dados
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class FalhaMercado(BaseModel):
    """Modelo de Falha de Mercado"""
    id: int
    titulo: str
    pilar: str
    descricao: str
    dica_busca: str

    class Config:
        from_attributes = True


class ResultadoPesquisa(BaseModel):
    """Modelo de Resultado de Pesquisa"""
    id: Optional[int] = None
    falha_id: int
    titulo: str
    descricao: Optional[str] = None
    fonte_url: str
    fonte_tipo: Optional[str] = None  # 'artigo', 'estudo', 'lei', 'programa'
    pais_origem: Optional[str] = None
    idioma: str
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    num_ocorrencias: int = Field(default=1, ge=1)
    ferramenta_origem: str  # 'perplexity', 'jina', 'deep_research'
    hash_conteudo: str
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class HistoricoPesquisa(BaseModel):
    """Modelo de Historico de Pesquisa"""
    id: Optional[int] = None
    falha_id: int
    query: str
    idioma: str
    ferramenta: str
    status: str = "pendente"  # 'pendente', 'processando', 'concluido', 'erro'
    resultados_encontrados: int = 0
    erro_mensagem: Optional[str] = None
    tempo_execucao: Optional[float] = None
    executado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class FilaPesquisa(BaseModel):
    """Modelo de Fila de Pesquisa"""
    id: Optional[int] = None
    falha_id: int
    query: str
    idioma: str
    ferramenta: str
    prioridade: int = 0
    tentativas: int = 0
    max_tentativas: int = 3
    status: str = "pendente"  # 'pendente', 'processando', 'concluido', 'erro'
    criado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class Estatisticas(BaseModel):
    """Modelo de Estatisticas Gerais"""
    total_falhas: int
    total_resultados: int
    pesquisas_concluidas: int
    pesquisas_pendentes: int
    confidence_medio: float


class EstatisticasFalha(BaseModel):
    """Modelo de Estatisticas de uma Falha"""
    total_resultados: int
    confidence_medio: float
    top_paises: List[dict]
    idiomas: List[dict]
