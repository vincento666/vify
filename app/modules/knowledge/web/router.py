from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_session_factory
from app.core.database import get_session
from app.core.responses import success
from app.modules.knowledge.domain.service import KnowledgeBaseService
from app.modules.knowledge.infra.repository import KnowledgeBaseRepository
from app.modules.knowledge.web.schemas import KnowledgeBaseCreateRequest, KnowledgeBaseUpdateRequest

router = APIRouter(prefix="/api/v1/knowledge-bases", tags=["knowledge-bases"])
document_router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def get_knowledge_base_service(session: Session = Depends(get_session)) -> KnowledgeBaseService:
    return KnowledgeBaseService(KnowledgeBaseRepository(session))


def process_document_background(document_id: int, content: bytes) -> None:
    with get_session_factory()() as session:
        KnowledgeBaseService(KnowledgeBaseRepository(session)).process_document(document_id, content)


@router.get("")
def list_knowledge_bases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    name: str | None = None,
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    return success(service.list(page, page_size, name))


@router.post("")
def create_knowledge_base(
    request: KnowledgeBaseCreateRequest,
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    return success(service.create(request))


@router.get("/{knowledge_base_id}")
def get_knowledge_base(
    knowledge_base_id: int,
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    return success(service.get(knowledge_base_id))


@router.put("/{knowledge_base_id}")
def update_knowledge_base(
    knowledge_base_id: int,
    request: KnowledgeBaseUpdateRequest,
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    return success(service.update(knowledge_base_id, request))


@router.delete("/{knowledge_base_id}")
def delete_knowledge_base(
    knowledge_base_id: int,
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    service.delete(knowledge_base_id)
    return success(None)


@router.post("/{knowledge_base_id}/documents")
async def upload_document(
    knowledge_base_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    content = await file.read()
    document = service.upload_document(knowledge_base_id, file.filename or "document", content)
    background_tasks.add_task(process_document_background, document["id"], content)
    return success(document)


@router.get("/{knowledge_base_id}/documents")
def list_documents(
    knowledge_base_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    return success(service.list_documents(knowledge_base_id, page, page_size))


@document_router.get("/{document_id}")
def get_document(
    document_id: int,
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    return success(service.get_document(document_id))


@document_router.get("/{document_id}/chunks")
def list_chunks(
    document_id: int,
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    return success(service.list_chunks(document_id))


@document_router.delete("/{document_id}")
def delete_document(
    document_id: int,
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> dict[str, Any]:
    service.delete_document(document_id)
    return success(None)
