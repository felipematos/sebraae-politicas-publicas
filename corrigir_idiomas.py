#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para corrigir idiomas incorretos nas fontes da base de dados.
Detecta automaticamente o idioma correto do texto e atualiza o banco.
"""

import sqlite3
from app.utils.language_detector import detectar_idioma

DATABASE_PATH = "falhas_mercado_v1.db"

def corrigir_idiomas_incorretos():
    """
    Detecta e corrige idiomas incorretos nas fontes
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Buscar todas as fontes
    cursor.execute("""
        SELECT id, titulo, descricao, idioma
        FROM resultados_pesquisa
        WHERE idioma IS NOT NULL
        ORDER BY id
    """)

    fontes = cursor.fetchall()
    total = len(fontes)
    corrigidas = 0
    erros = 0

    print(f"📊 Total de fontes a verificar: {total}")
    print("=" * 80)

    for idx, (fonte_id, titulo, descricao, idioma_atual) in enumerate(fontes, 1):
        # Usar título + descrição para detecção mais precisa
        texto_completo = f"{titulo or ''} {descricao or ''}"[:1000]  # Primeiros 1000 chars

        if not texto_completo.strip():
            continue

        try:
            # Detectar idioma correto - retorna tupla (idioma, confianca)
            idioma_detectado, confianca = detectar_idioma(texto_completo)

            # Se idioma diferente E confiança >= 15%, atualizar
            if idioma_detectado != idioma_atual and idioma_detectado != 'unknown' and confianca >= 0.15:
                cursor.execute("""
                    UPDATE resultados_pesquisa
                    SET idioma = ?
                    WHERE id = ?
                """, (idioma_detectado, fonte_id))

                corrigidas += 1
                print(f"✓ [{idx}/{total}] ID {fonte_id}: {idioma_atual} → {idioma_detectado} (conf: {confianca:.2f})")
                print(f"  Título: {titulo[:70]}...")

        except Exception as e:
            erros += 1
            print(f"✗ [{idx}/{total}] ID {fonte_id}: Erro - {str(e)}")

        # Progress indicator a cada 1000 registros
        if idx % 1000 == 0:
            print(f"\n📈 Progresso: {idx}/{total} ({idx/total*100:.1f}%)")
            print(f"   Corrigidas até agora: {corrigidas}\n")
            conn.commit()  # Commit parcial para não perder progresso

    # Commit final
    conn.commit()
    conn.close()

    print("\n" + "=" * 80)
    print(f"✅ Correção concluída!")
    print(f"   - Total verificado: {total}")
    print(f"   - Fontes corrigidas: {corrigidas}")
    print(f"   - Erros: {erros}")
    print(f"   - Taxa de correção: {corrigidas/total*100:.2f}%")
    print("=" * 80)

if __name__ == "__main__":
    corrigir_idiomas_incorretos()
