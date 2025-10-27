#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para regenerar a fila de pesquisas com distribuição correta
"""
import asyncio
import sys
sys.path.insert(0, '/Users/felipematossardinhapinto/Library/CloudStorage/GoogleDrive-Felipe@felipematos.net/My Drive/10K/Projetos/2025/Sebrae Nacional/Code')

from app.agente.pesquisador import AgentePesquisador
from app.config import settings

async def main():
    """Regenera a fila com todas as falhas, idiomas e ferramentas ativadas"""
    print("=" * 80)
    print("REGENERANDO FILA DE PESQUISAS COM DISTRIBUIÇÃO CORRETA")
    print("=" * 80)
    
    # Mostrar configuração
    print(f"\n📊 Configuração:")
    print(f"  - Ferramentas ativadas: {list(settings.SEARCH_CHANNELS_ENABLED.keys())}")
    ferramentas_ativas = [f for f, a in settings.SEARCH_CHANNELS_ENABLED.items() if a]
    print(f"  - Ferramentas realmente ativas: {ferramentas_ativas}")
    print(f"  - Idiomas: {settings.IDIOMAS}")
    print(f"  - Total esperado: 50 falhas × {len(settings.IDIOMAS)} idiomas × {len(ferramentas_ativas)} ferramentas = {50 * len(settings.IDIOMAS) * len(ferramentas_ativas)} entradas")
    
    # Criar agente
    agente = AgentePesquisador()
    
    # Popular fila com todas as falhas e ferramentas ativadas
    print(f"\n🔄 Populando fila...")
    total = await agente.popular_fila()
    
    print(f"\n✅ Fila regenerada com sucesso!")
    print(f"   Total de entradas criadas: {total}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
