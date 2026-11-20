import logging
import os

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.deps import ANY_ROLE, MANAGER_UP, get_owned_bot, parse_object_id, require_roles
from app.models import Chatbot, KnowledgeDocument, User
from app.schemas import DocumentOut
from app.services import rag
from app.services.vectorstore import get_vector_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bots/{bot_id}/documents", tags=["documents"])


async def process_document(doc_id: str, path: str, filename: str, org_id: str, bot_id: str) -> None:
    """Background job: index the PDF, then record the outcome on the document."""
    error: str | None = None
    count = 0
    try:
        count = await run_in_threadpool(rag.ingest_pdf, path, filename, org_id, bot_id, doc_id)
    except ValueError as e:  # user-fixable (e.g. scanned PDF)
        error = str(e)
    except Exception:
        logger.exception("Indexing failed for document %s", doc_id)
        error = "Indexing failed. Check the server logs."
    finally:
        if os.path.exists(path):
            os.remove(path)

    doc = await KnowledgeDocument.get(doc_id)
    if doc is None:  # deleted while we were indexing -> don't leave orphan vectors
        await run_in_threadpool(get_vector_store().delete_document, org_id, bot_id, doc_id)
        return
    doc.status, doc.chunks_count, doc.error = ("failed", 0, error) if error else ("ready", count, None)
    await doc.save()


@router.post("", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    bot: Chatbot = Depends(get_owned_bot),
    _: User = Depends(require_roles(*MANAGER_UP)),
):
    s = get_settings()
    filename = os.path.basename(file.filename or "")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF files are supported right now")

    max_bytes = s.max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File exceeds {s.max_upload_mb} MB")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is not a valid PDF")

    doc = await KnowledgeDocument(
        filename=filename[:200], chatbot_id=str(bot.id), organization_id=bot.organization_id
    ).insert()

    os.makedirs(s.upload_dir, exist_ok=True)
    path = os.path.join(s.upload_dir, f"{doc.id}.pdf")  # server-chosen name; never the client's
    with open(path, "wb") as f:
        f.write(data)

    background.add_task(process_document, str(doc.id), path, doc.filename, bot.organization_id, str(bot.id))
    return DocumentOut.of(doc)


@router.get("", response_model=list[DocumentOut])
async def list_documents(bot: Chatbot = Depends(get_owned_bot), _: User = Depends(require_roles(*ANY_ROLE))):
    docs = await KnowledgeDocument.find(KnowledgeDocument.chatbot_id == str(bot.id)).sort(
        -KnowledgeDocument.uploaded_at
    ).to_list()
    return [DocumentOut.of(d) for d in docs]


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str, bot: Chatbot = Depends(get_owned_bot), _: User = Depends(require_roles(*MANAGER_UP))
):
    doc = await KnowledgeDocument.find_one(
        KnowledgeDocument.id == parse_object_id(doc_id), KnowledgeDocument.chatbot_id == str(bot.id)
    )
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    await run_in_threadpool(get_vector_store().delete_document, bot.organization_id, str(bot.id), str(doc.id))
    await doc.delete()
