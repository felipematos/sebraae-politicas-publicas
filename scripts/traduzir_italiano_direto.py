#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Traduz diretamente para italiano as queries que ainda estão em português.
"""
import sqlite3

DB_PATH = "falhas_mercado_v1.db"

# Dicionário de mapeamento de português para italiano (baseado nas queries encontradas)
MAPEAMENTO_QUERIES = {
    'Qualidade Relativa Incipiente dos Ambientes de Inovação': 'Qualità Relativa Nascente degli Ambienti di Innovazione',
    'Ausência de Políticas Claras sobre Governança e Soberania de Dados': 'Assenza di Politiche Chiare su Governance e Sovranità dei Dati',
    'Ausência de Regulamentação sobre "Stock Options"': 'Assenza di Regolamentazione su "Stock Options"',
    'Aversão ao Risco e Empreendedorismo de Necessidade': 'Avversione al Rischio e Imprenditorialità per Necessità',
    'Baixa Representatividade de Gênero e Raça': 'Bassa Rappresentanza di Genere e Razza',
    'Baixo Nível de Confiança Para Geração de Negócios': 'Basso Livello di Fiducia per Generazione di Affari',
    'Baixo Nível de Internacionalização': 'Basso Livello di Internazionalizzazione',
    'Baixo Nível de Transferência de Tecnologia Entre Universidades e Empresas': 'Basso Livello di Trasferimento di Tecnologia Tra Università e Aziende',
    'Barreiras ao Capital Estrangeiro': 'Barriere al Capitale Straniero',
    'Barreiras de Entrada e Compras Públicas': 'Barriere di Accesso e Acquisti Pubblici',
    'Bases Curriculares Nacionais Desatualizadas': 'Basi Curricolari Nazionali Obsolete',
}

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

atualizadas = 0

for pt, it in MAPEAMENTO_QUERIES.items():
    # Atualizar a query exata
    cursor.execute(
        "UPDATE fila_pesquisas SET query = ? WHERE idioma = 'it' AND query = ? AND status = 'pendente'",
        (it, pt)
    )
    atualizadas += cursor.rowcount

conn.commit()
conn.close()

print(f"✓ {atualizadas} queries italianas atualizadas")
