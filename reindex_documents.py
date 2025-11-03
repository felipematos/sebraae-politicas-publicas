# -*- coding: utf-8 -*-
"""
Script para re-indexar todos os documentos existentes no vector store
Usa o mesmo código de upload para garantir consistência
"""
import asyncio
import sys
from pathlib import Path

# Adicionar diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings, get_chroma_path
from app.vector.vector_store import get_vector_store
from app.vector.embeddings import EmbeddingClient
from app.api.knowledge_base import DOCS_DIR, extract_text_from_docx, extract_text_from_pdf, extract_text_from_csv, extract_text_from_markdown, store_document_in_vector_db


async def reindex_all_documents():
    """Re-indexa todos os documentos da pasta documentos/"""
    print(f"Iniciando re-indexação de documentos em {DOCS_DIR}")

    # Inicializar vector store
    embedding_client = EmbeddingClient(api_key=settings.OPENAI_API_KEY)
    persist_path = get_chroma_path()
    vector_store = await get_vector_store(persist_path=persist_path, embedding_client=embedding_client)

    # Listar todos os arquivos
    files = list(DOCS_DIR.glob("*"))
    valid_files = [f for f in files if f.is_file() and f.suffix.lower() in ['.docx', '.pdf', '.csv', '.md', '.txt']]

    print(f"Encontrados {len(valid_files)} documentos para re-indexar")

    indexed_count = 0
    error_count = 0

    for file_path in valid_files:
        try:
            print(f"\n[{indexed_count + error_count + 1}/{len(valid_files)}] Processando: {file_path.name}")

            # Ler arquivo
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # Extrair texto baseado na extensão
            if file_path.suffix.lower() == '.docx':
                text = extract_text_from_docx(file_content)
                file_type = 'docx'
            elif file_path.suffix.lower() == '.pdf':
                text = extract_text_from_pdf(file_content)
                file_type = 'pdf'
            elif file_path.suffix.lower() == '.csv':
                text = extract_text_from_csv(file_content)
                file_type = 'csv'
            elif file_path.suffix.lower() in ['.md', '.txt']:
                text = extract_text_from_markdown(file_content)
                file_type = file_path.suffix.lower()[1:]
            else:
                print(f"  ✗ Tipo não suportado: {file_path.suffix}")
                error_count += 1
                continue

            # Armazenar em vector DB
            success = await store_document_in_vector_db(
                file_name=file_path.name,
                text_content=text,
                file_type=file_type
            )

            if success:
                print(f"  ✓ Indexado com sucesso ({len(text)} caracteres)")
                indexed_count += 1
            else:
                print(f"  ✗ Falha ao indexar")
                error_count += 1

        except Exception as e:
            print(f"  ✗ Erro: {e}")
            error_count += 1
            import traceback
            traceback.print_exc()

    # Verificar estatísticas finais
    stats = vector_store.get_stats()
    print(f"\n{'=' * 60}")
    print(f"Re-indexação concluída!")
    print(f"  • Documentos indexados: {indexed_count}")
    print(f"  • Erros: {error_count}")
    print(f"  • Total de chunks no vector store: {stats.get('documents_count', 0)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(reindex_all_documents())
