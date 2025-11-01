# -*- coding: utf-8 -*-
"""
Endpoints para gerenciamento de Base de Conhecimento com RAG
Gerencia upload de DOCX/PDF e armazenamento em vector database
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List
from pydantic import BaseModel
import io
import os
import json
import asyncio
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
from app.utils.text_chunker import create_smart_chunks, clean_text

router = APIRouter(prefix="/api/knowledge-base", tags=["Knowledge Base"])

# Diretório para armazenar documentos
DOCS_DIR = Path(__file__).parent.parent.parent / "documentos"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Limite máximo de tamanho de arquivo (25MB)
MAX_FILE_SIZE = 25 * 1024 * 1024  # 26,214,400 bytes


class ChatRequest(BaseModel):
    pergunta: str


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
    file_type: str,
    progress_callback=None
) -> bool:
    """
    Armazena documento em ChromaDB com embeddings
    progress_callback: função opcional para reportar progresso de indexação
    """
    try:
        # Obter vector store global (singleton já inicializado no startup)
        vector_store = await get_vector_store()

        # Dividir texto em chunks inteligentes (otimizado para RAG de alta qualidade)
        # - Limpa espaços extras entre letras (problema OCR)
        # - Respeita limites de frases completas
        # - Chunks maiores (1500 chars) para melhor contexto
        # - Overlap de 300 chars para continuidade semântica
        chunks = create_smart_chunks(
            text=text_content,
            chunk_size=1500,  # Chunks maiores para melhor qualidade
            overlap=300,       # Overlap maior para não perder contexto
            clean=True         # Limpa espaços extras e caracteres estranhos
        )

        total_chunks = len(chunks)

        # Adicionar cada chunk ao vector store com progresso incremental
        for i, chunk in enumerate(chunks):
            if chunk.strip():
                doc_id = f"{file_name}_chunk_{i}"
                metadata = {
                    "source": file_name,
                    "type": file_type,
                    "chunk": i,
                    "uploaded_at": datetime.now().isoformat()
                }

                # Reportar progresso durante indexação (60% a 90%)
                # Cada chunk representa uma fração do progresso total
                if progress_callback:
                    # Progresso de 60% a 90% dividido pelos chunks
                    chunk_progress = 60 + int(((i + 1) / total_chunks) * 30)
                    await progress_callback({
                        "phase": "indexing",
                        "progress": chunk_progress,
                        "detail": f"Indexando chunk {i+1}/{total_chunks}"
                    })

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


async def process_single_file(
    file: UploadFile,
    overwrite: str,
    progress_callback=None
) -> dict:
    """
    Processa um único arquivo e retorna resultado
    progress_callback: função opcional para enviar atualizações de progresso
    """
    try:
        # Validar tipo baseado na extensão do arquivo
        if not (file.filename.endswith('.docx') or
                file.filename.endswith('.pdf') or
                file.filename.endswith('.csv') or
                file.filename.endswith('.md') or
                file.filename.endswith('.txt')):
            return {"status": "error", "filename": file.filename, "error": "Extensão não suportada"}

        # Validar content-type
        if file.content_type not in [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/pdf',
            'text/csv',
            'text/markdown',
            'text/plain',
            'application/octet-stream'
        ]:
            return {"status": "error", "filename": file.filename, "error": "Tipo de arquivo não suportado"}

        if progress_callback:
            await progress_callback({"phase": "reading", "filename": file.filename, "progress": 10})

        # Verificar se arquivo já existe
        file_path = DOCS_DIR / file.filename
        file_exists = file_path.exists()
        final_filename = file.filename

        if file_exists:
            if overwrite == "skip":
                return {"status": "skipped", "filename": file.filename}
            elif overwrite == "copy":
                base_name = file.filename.rsplit('.', 1)[0]
                extension = file.filename.rsplit('.', 1)[1] if '.' in file.filename else ''
                counter = 1
                while (DOCS_DIR / f"{base_name} ({counter}).{extension}").exists():
                    counter += 1
                final_filename = f"{base_name} ({counter}).{extension}"

        if progress_callback:
            await progress_callback({"phase": "extracting", "filename": file.filename, "progress": 30})

        # Ler conteúdo
        file_content = await file.read()

        if len(file_content) > MAX_FILE_SIZE:
            return {"status": "error", "filename": file.filename, "error": "Arquivo excede 25MB"}

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
            file_type = 'md'
        elif file.filename.endswith('.txt'):
            text = extract_text_from_markdown(file_content)
            file_type = 'txt'
        else:
            return {"status": "error", "filename": file.filename, "error": "Extensão não reconhecida"}

        # Armazenar em vector DB com callback de progresso
        # A indexação vai de 60% a 90% (dividido pelos chunks)
        success = await store_document_in_vector_db(
            file_name=final_filename,
            text_content=text,
            file_type=file_type,
            progress_callback=progress_callback
        )

        if not success:
            return {"status": "error", "filename": file.filename, "error": "Falha ao indexar"}

        if progress_callback:
            await progress_callback({"phase": "saving", "filename": file.filename, "progress": 92})

        # Salvar arquivo localmente
        file_path = DOCS_DIR / final_filename
        with open(file_path, 'wb') as f:
            f.write(file_content)

        if progress_callback:
            await progress_callback({"phase": "complete", "filename": file.filename, "progress": 100})

        return {
            "status": "success",
            "nome": final_filename,
            "nome_original": file.filename if final_filename != file.filename else None,
            "tamanho": len(file_content),
            "tipo": file_type,
            "upload_em": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"[KB] Erro ao processar {file.filename}: {str(e)}")
        return {"status": "error", "filename": file.filename, "error": str(e)}


@router.post("/upload-stream")
async def upload_documents_stream(
    files: List[UploadFile] = File(...),
    overwrite: str = "ask"
):
    """
    Upload de documentos com progresso em tempo real via SSE
    """
    async def event_generator():
        try:
            total_files = len(files)

            # Enviar evento de início
            yield f"data: {json.dumps({'type': 'start', 'total': total_files})}\n\n"
            await asyncio.sleep(0)  # Força flush

            uploaded_files = []
            skipped_files = []

            for index, file in enumerate(files):
                # Lista para coletar eventos de progresso
                progress_events = []

                # Callback que coleta eventos ao invés de enviá-los
                async def collect_progress(data):
                    progress_events.append({
                        'type': 'progress',
                        'file_index': index,
                        'file_name': file.filename,
                        **data
                    })

                # Processar arquivo
                result = await process_single_file(file, overwrite, collect_progress)

                # Enviar todos os eventos de progresso coletados
                for event in progress_events:
                    yield f"data: {json.dumps(event)}\n\n"
                    await asyncio.sleep(0)

                if result["status"] == "success":
                    uploaded_files.append(result)
                elif result["status"] == "skipped":
                    skipped_files.append(result["filename"])

                # Enviar resultado do arquivo
                yield f"data: {json.dumps({'type': 'file_complete', 'file_index': index, 'result': result})}\n\n"
                await asyncio.sleep(0)

            # Enviar evento de conclusão
            final_result = {
                'type': 'complete',
                'total': len(uploaded_files),
                'dados': uploaded_files,
                'ignorados': skipped_files,
                'mensagem': f"{len(uploaded_files)} arquivo(s) enviado(s) com sucesso" + (f", {len(skipped_files)} ignorado(s)" if skipped_files else "")
            }
            yield f"data: {json.dumps(final_result)}\n\n"

        except Exception as e:
            print(f"[KB Upload Stream] Erro: {str(e)}")
            import traceback
            traceback.print_exc()
            error_data = {'type': 'error', 'message': str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    overwrite: str = "ask"  # "ask", "overwrite", "copy", "skip"
):
    """
    Upload de documentos DOCX ou PDF (versão sem streaming - mantida para compatibilidade)
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
            vector_store = await get_vector_store()
            # Contar documentos no vector store
            stats = vector_store.get_stats()
            total_vetores = stats.get("documents_count", 0)
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


@router.post("/chat")
async def chat_knowledge_base(request: ChatRequest):
    """
    Chat com RAG sobre a base de conhecimento
    """
    try:
        from app.llm.openai_client import OpenAIClient

        debug_info = {
            "total_documentos_vector_store": 0,
            "documentos_encontrados": 0,
            "fontes_consultadas": [],
            "chunks_utilizados": [],
            "modelo_llm": "gpt-4o",  # Modelo com maior janela de contexto (128k tokens)
            "temperatura": 0.3,
            "chunk_size": 1500,
            "overlap": 300
        }

        # Obter vector store global (singleton)
        vector_store = await get_vector_store()

        # Obter estatísticas do vector store
        stats = vector_store.get_stats()
        debug_info["total_documentos_vector_store"] = stats.get("documents_count", 0)

        # Buscar mais documentos relevantes para melhor cobertura
        resultados = await vector_store.similarity_search(
            query=request.pergunta,
            k=10  # Top 10 chunks mais relevantes (com chunks de 1500 chars, temos ~15k chars de contexto)
        )

        debug_info["documentos_encontrados"] = len(resultados)

        if not resultados:
            return JSONResponse({
                "resposta": "Não encontrei informações relevantes na base de conhecimento para responder sua pergunta.",
                "fontes": [],
                "debug": debug_info
            })

        # Preparar contexto a partir dos documentos
        contexto_partes = []
        fontes = set()

        for i, doc in enumerate(resultados):
            contexto_partes.append(f"[Documento {i+1}]:\n{doc['text']}\n")
            if 'metadata' in doc and 'source' in doc['metadata']:
                fonte = doc['metadata']['source']
                fontes.add(fonte)
                debug_info["fontes_consultadas"].append(fonte)

            # Adicionar informações de debug sobre os chunks
            debug_info["chunks_utilizados"].append({
                "chunk_index": i + 1,
                "fonte": doc['metadata'].get('source', 'Desconhecida') if 'metadata' in doc else 'Desconhecida',
                "tamanho_texto": len(doc['text']),
                "distancia": doc.get('distance', 0.0),
                "preview": doc['text'][:200] + "..." if len(doc['text']) > 200 else doc['text']
            })

        contexto = "\n".join(contexto_partes)

        # Criar prompt para o LLM
        prompt = f"""Você é um assistente especializado em analisar documentos da base de conhecimento do Sebrae Nacional sobre inovação e políticas públicas.

Contexto dos documentos encontrados:
{contexto}

Pergunta do usuário: {request.pergunta}

Por favor, responda a pergunta baseando-se EXCLUSIVAMENTE nas informações fornecidas no contexto acima. Se a informação não estiver disponível no contexto, informe isso claramente.

Responda de forma clara, objetiva e estruturada."""

        # Chamar LLM com modelo de alta performance
        # GPT-4o: 128k tokens de contexto, melhor raciocínio e compreensão
        llm_client = OpenAIClient(api_key=settings.OPENAI_API_KEY)
        resposta = await llm_client.generate_completion(
            prompt=prompt,
            model="gpt-4o",  # Modelo premium com maior janela de contexto
            temperature=0.3
        )

        return JSONResponse({
            "resposta": resposta,
            "fontes": list(fontes),
            "debug": debug_info
        })

    except Exception as e:
        print(f"[KB Chat] Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao processar pergunta: {str(e)}")


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
