# -*- coding: utf-8 -*-
"""
Endpoints para gerenciamento de Base de Conhecimento com RAG
Gerencia upload de DOCX/PDF e armazenamento em vector database
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import io
import os
from pathlib import Path
from datetime import datetime

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

from app.config import settings, get_database_path
from app.database import db
from app.vector.vector_store import get_vector_store
from app.vector.embeddings import EmbeddingClient

router = APIRouter(prefix="/api/knowledge-base", tags=["Knowledge Base"])

# Diretório para armazenar documentos
DOCS_DIR = Path(__file__).parent.parent.parent / "documentos"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Limite máximo de tamanho de arquivo (25MB)
MAX_FILE_SIZE = 25 * 1024 * 1024  # 26,214,400 bytes


def extract_text_from_docx(file_content: bytes) -> str:
    """Extrai texto de arquivo DOCX"""
    if DocxDocument is None:
        raise HTTPException(status_code=400, detail="python-docx não instalado")

    try:
        doc = DocxDocument(io.BytesIO(file_content))
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao extrair DOCX: {str(e)}")


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extrai texto de arquivo PDF"""
    if PyPDF2 is None:
        raise HTTPException(status_code=400, detail="PyPDF2 não instalado")

    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao extrair PDF: {str(e)}")


def extract_text_from_csv(file_content: bytes) -> str:
    """Extrai texto de arquivo CSV"""
    try:
        text = file_content.decode('utf-8')
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao extrair CSV: {str(e)}")


def extract_text_from_markdown(file_content: bytes) -> str:
    """Extrai texto de arquivo Markdown"""
    try:
        text = file_content.decode('utf-8')
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao extrair Markdown: {str(e)}")



async def store_document_in_vector_db(
    file_name: str,
    text_content: str,
    file_type: str
) -> bool:
    """
    Armazena documento em ChromaDB com embeddings
    """
    try:
        # Obter vector store
        embedding_client = EmbeddingClient(api_key=settings.OPENAI_API_KEY)
        from app.config import get_chroma_path
        vector_store = await get_vector_store(
            persist_path=get_chroma_path(),
            embedding_client=embedding_client
        )

        # Dividir texto em chunks
        chunk_size = 1000
        chunks = [
            text_content[i:i + chunk_size]
            for i in range(0, len(text_content), chunk_size)
        ]

        # Adicionar cada chunk ao vector store
        for i, chunk in enumerate(chunks):
            if chunk.strip():
                doc_id = f"{file_name}_chunk_{i}"
                metadata = {
                    "source": file_name,
                    "type": file_type,
                    "chunk": i,
                    "uploaded_at": datetime.now().isoformat()
                }

                # Add to vector store
                await vector_store.add_texts(
                    texts=[chunk],
                    metadatas=[metadata],
                    ids=[doc_id]
                )

        return True
    except Exception as e:
        print(f"Erro ao armazenar documento em vector DB: {e}")
        return False


@router.post("/check-duplicates")
async def check_duplicates(files: List[UploadFile] = File(...)):
    """
    Verifica se há arquivos duplicados antes do upload
    Retorna lista de arquivos duplicados
    """
    try:
        duplicates = []

        for file in files:
            # Verificar se arquivo já existe
            file_path = DOCS_DIR / file.filename
            if file_path.exists():
                stat = file_path.stat()
                duplicates.append({
                    "nome": file.filename,
                    "tamanho_existente": stat.st_size,
                    "tamanho_novo": file.size
                })

        return JSONResponse({
            "duplicates": duplicates,
            "has_duplicates": len(duplicates) > 0
        })
    except Exception as e:
        print(f"[KB] Erro ao verificar duplicatas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao verificar duplicatas: {str(e)}")


@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    overwrite: str = "ask"  # "ask", "overwrite", "copy", "skip"
):
    """
    Upload de documentos DOCX ou PDF
    Armazena em vector database para RAG

    Parâmetros:
    - overwrite: "ask" (padrão), "overwrite" (sobrescrever), "copy" (criar cópia), "skip" (ignorar)
    """
    try:
        uploaded_files = []
        skipped_files = []

        for file in files:
            try:
                # Validar tipo baseado na extensão do arquivo (mais importante que content-type)
                # Alguns clientes enviam application/octet-stream para CSV/MD
                if not (file.filename.endswith('.docx') or
                        file.filename.endswith('.pdf') or
                        file.filename.endswith('.csv') or
                        file.filename.endswith('.md') or
                        file.filename.endswith('.txt')):
                    print(f"[KB] Arquivo {file.filename} com extensão não suportada")
                    continue

                # Validar content-type também (com fallback para octet-stream)
                if file.content_type not in [
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'application/pdf',
                    'text/csv',
                    'text/markdown',
                    'text/plain',
                    'application/octet-stream'  # Fallback para clientes que enviam tipo genérico
                ]:
                    print(f"[KB] Arquivo {file.filename} com tipo {file.content_type} ignorado")
                    continue

                # Verificar se arquivo já existe
                file_path = DOCS_DIR / file.filename
                file_exists = file_path.exists()

                # Determinar nome do arquivo baseado na política de duplicatas
                final_filename = file.filename

                if file_exists:
                    if overwrite == "skip":
                        print(f"[KB] Arquivo {file.filename} já existe - ignorado")
                        skipped_files.append(file.filename)
                        continue
                    elif overwrite == "copy":
                        # Criar nome único com sufixo
                        base_name = file.filename.rsplit('.', 1)[0]
                        extension = file.filename.rsplit('.', 1)[1] if '.' in file.filename else ''
                        counter = 1
                        while (DOCS_DIR / f"{base_name} ({counter}).{extension}").exists():
                            counter += 1
                        final_filename = f"{base_name} ({counter}).{extension}"
                        print(f"[KB] Criando cópia: {final_filename}")
                    elif overwrite == "overwrite":
                        # Remover arquivo antigo do vector store antes de sobrescrever
                        print(f"[KB] Sobrescrevendo arquivo {file.filename}")
                        # TODO: Implementar remoção do vector store
                    # Se overwrite == "ask", não deveria chegar aqui pois frontend deve perguntar primeiro

                # Ler conteúdo
                file_content = await file.read()

                # Validar tamanho do arquivo (máximo 25MB)
                if len(file_content) > MAX_FILE_SIZE:
                    print(f"[KB] Arquivo {file.filename} excede 25MB ({len(file_content)} bytes)")
                    continue

                # Extrair texto baseado no tipo
                if file.filename.endswith('.docx'):
                    text = extract_text_from_docx(file_content)
                    file_type = 'docx'
                elif file.filename.endswith('.pdf'):
                    text = extract_text_from_pdf(file_content)
                    file_type = 'pdf'
                elif file.filename.endswith('.csv'):
                    text = extract_text_from_csv(file_content)
                    file_type = 'csv'
                elif file.filename.endswith('.md'):
                    text = extract_text_from_markdown(file_content)
                    file_type = 'markdown'
                elif file.filename.endswith('.txt'):
                    text = extract_text_from_markdown(file_content)  # Usar mesma função para .txt
                    file_type = 'txt'
                else:
                    print(f"[KB] Arquivo {file.filename} com extensão não suportada")
                    continue

                # Armazenar em vector DB
                success = await store_document_in_vector_db(
                    file_name=final_filename,
                    text_content=text,
                    file_type=file_type
                )

                if success:
                    # Salvar arquivo localmente também
                    file_path = DOCS_DIR / final_filename
                    with open(file_path, 'wb') as f:
                        f.write(file_content)

                    uploaded_files.append({
                        "nome": final_filename,
                        "nome_original": file.filename if final_filename != file.filename else None,
                        "tamanho": len(file_content),
                        "tipo": file_type,
                        "status": "indexado",
                        "upload_em": datetime.now().isoformat()
                    })
                    print(f"[KB] Arquivo {final_filename} enviado com sucesso")
                else:
                    print(f"[KB] Falha ao armazenar {file.filename} em vector DB")

            except HTTPException:
                raise
            except Exception as e:
                print(f"[KB] Erro ao processar arquivo {file.filename}: {str(e)}")
                import traceback
                traceback.print_exc()

        return JSONResponse({
            "total": len(uploaded_files),
            "dados": uploaded_files,
            "ignorados": skipped_files,
            "mensagem": f"{len(uploaded_files)} arquivo(s) enviado(s) com sucesso" + (f", {len(skipped_files)} ignorado(s)" if skipped_files else "")
        })

    except HTTPException:
        # Re-raise HTTPException as-is (don't convert to 500)
        raise
    except Exception as e:
        print(f"[KB] Erro geral no upload: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro no upload: {str(e)}")


@router.get("/documentos")
async def list_documents():
    """
    Listar documentos armazenados na base de conhecimento
    """
    try:
        documentos = []

        # Listar arquivos do diretório
        if DOCS_DIR.exists():
            for file_path in DOCS_DIR.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()
                    tipo = file_path.suffix.lower().strip('.')

                    documentos.append({
                        "nome": file_path.name,
                        "tamanho": stat.st_size,
                        "tipo": tipo,
                        "status": "indexado",
                        "criado_em": datetime.fromtimestamp(stat.st_ctime).isoformat()
                    })

        return JSONResponse({
            "total": len(documentos),
            "dados": documentos
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao listar documentos: {str(e)}")


@router.get("/estatisticas")
async def get_statistics():
    """
    Obter estatísticas sobre documentos e vetores
    """
    try:
        # Contar documentos locais
        total_docs = 0
        if DOCS_DIR.exists():
            total_docs = len([f for f in DOCS_DIR.iterdir() if f.is_file()])

        # Tentar obter estatísticas do vector store
        total_vetores = 0
        try:
            embedding_client = EmbeddingClient(api_key=settings.OPENAI_API_KEY)
            from app.config import get_chroma_path
            vector_store = await get_vector_store(
                persist_path=get_chroma_path(),
                embedding_client=embedding_client
            )
            # Tentar contar documentos no ChromaDB
            try:
                collection = vector_store._client.get_or_create_collection("documents")
                total_vetores = collection.count()
            except:
                total_vetores = 0
        except:
            total_vetores = 0

        return JSONResponse({
            "total_documentos": total_docs,
            "total_indexados": total_docs,
            "total_vetores": total_vetores
        })

    except Exception as e:
        return JSONResponse({
            "total_documentos": 0,
            "total_indexados": 0,
            "total_vetores": 0,
            "erro": str(e)
        })


@router.delete("/documentos/{filename}")
async def delete_document(filename: str):
    """
    Deleta um documento da base de conhecimento
    """
    try:
        # Validar o nome do arquivo para prevenir path traversal
        if "/" in filename or "\\" in filename or ".." in filename:
            raise HTTPException(status_code=400, detail="Nome de arquivo inválido")

        file_path = DOCS_DIR / filename

        # Verificar se o arquivo existe
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Arquivo {filename} não encontrado")

        # Deletar o arquivo
        file_path.unlink()
        print(f"[KB] Arquivo {filename} deletado com sucesso")

        return JSONResponse({
            "mensagem": f"Documento {filename} removido com sucesso",
            "status": "deletado"
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"[KB] Erro ao deletar documento {filename}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao deletar documento: {str(e)}")
