from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.knowledge.domain.chunks import (
    ChunkRecord,
    split_document_chunks,
)
from app.modules.knowledge.domain.embeddings import FakeEmbeddingProvider
from app.modules.knowledge.domain.files import document_extension, validate_document_file
from app.modules.knowledge.domain.parser import parse_document_content
from app.modules.knowledge.infra.repository import KnowledgeBaseRepository
from app.modules.knowledge.web.schemas import (
    ChunkResponse,
    DocumentPageResponse,
    DocumentResponse,
    KnowledgeBaseCreateRequest,
    KnowledgeBasePageResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdateRequest,
    format_datetime,
)


@dataclass(frozen=True)
class DocumentProcessingOutcome:
    document_id: int
    status: str
    chunk_count: int = 0
    embedding_count: int = 0
    error_message: str = ""


class KnowledgeBaseService:
    def __init__(self, repository: KnowledgeBaseRepository) -> None:
        self._repository = repository
        self._embedding_provider = FakeEmbeddingProvider()

    def list(self, page: int, page_size: int, name: str | None) -> dict[str, Any]:
        rows, total = self._repository.list_page(page, page_size, name)
        response = KnowledgeBasePageResponse(
            list=[self._response(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def create(self, request: KnowledgeBaseCreateRequest) -> dict[str, Any]:
        row = self._repository.create(
            {
                "name": request.name,
                "description": request.description,
            }
        )
        return self._response(row).model_dump(by_alias=True)

    def get(self, knowledge_base_id: int) -> dict[str, Any]:
        row = self._repository.get(knowledge_base_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Knowledge base not found")
        return self._response(row).model_dump(by_alias=True)

    def update(self, knowledge_base_id: int, request: KnowledgeBaseUpdateRequest) -> dict[str, Any]:
        values: dict[str, Any] = {}
        if request.name is not None:
            values["name"] = request.name
        if request.description is not None:
            values["description"] = request.description
        if request.enabled is not None:
            values["enabled"] = bool(request.enabled)
        row = self._repository.update(knowledge_base_id, values)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Knowledge base not found")
        return self._response(row).model_dump(by_alias=True)

    def delete(self, knowledge_base_id: int) -> None:
        if not self._repository.delete(knowledge_base_id):
            raise BizError(ErrorCode.NOT_FOUND, "Knowledge base not found")

    def upload_document(
        self,
        knowledge_base_id: int,
        filename: str,
        content: bytes,
    ) -> dict[str, Any]:
        if self._repository.get(knowledge_base_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Knowledge base not found")
        try:
            validate_document_file(filename, len(content))
        except ValueError as exc:
            raise BizError(ErrorCode.BAD_REQUEST, str(exc)) from exc
        row = self._repository.create_document(
            {
                "knowledge_base_id": knowledge_base_id,
                "name": filename,
                "file_type": document_extension(filename),
                "file_size": len(content),
            }
        )
        return self._document_response(row).model_dump(by_alias=True)

    def process_document(self, document_id: int, content: bytes) -> DocumentProcessingOutcome | None:
        row = self._repository.get_document(document_id)
        if row is None:
            return None
        self._repository.update_document_processing_state(document_id, "PROCESSING")
        try:
            parsed = parse_document_content(row["name"], content)
            chunks = self._repository.replace_document_chunks(
                document_id,
                split_document_chunks(parsed.text),
            )
            embeddings = self._embedding_provider.embed([chunk.content for chunk in chunks])
            embedding_rows = self._repository.replace_document_embeddings(
                chunks,
                embeddings,
                self._embedding_provider.model_name,
                self._embedding_provider.dimensions,
            )
            self._repository.update_document_processing_state(document_id, "DONE", chunk_count=len(chunks))
            return DocumentProcessingOutcome(
                document_id=document_id,
                status="DONE",
                chunk_count=len(chunks),
                embedding_count=len(embedding_rows),
            )
        except Exception as exc:
            error_message = str(exc)[:500]
            self._repository.clear_document_chunks(document_id)
            self._repository.update_document_processing_state(
                document_id,
                "FAILED",
                error_message=error_message,
            )
            return DocumentProcessingOutcome(
                document_id=document_id,
                status="FAILED",
                error_message=error_message,
            )

    def list_documents(self, knowledge_base_id: int, page: int, page_size: int) -> dict[str, Any]:
        if self._repository.get(knowledge_base_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Knowledge base not found")
        rows, total = self._repository.list_documents(knowledge_base_id, page, page_size)
        response = DocumentPageResponse(
            list=[self._document_response(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def get_document(self, document_id: int) -> dict[str, Any]:
        row = self._repository.get_document(document_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Document not found")
        return self._document_response(row).model_dump(by_alias=True)

    def list_chunks(self, document_id: int) -> Sequence[dict[str, Any]]:
        row = self._repository.get_document(document_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Document not found")
        return [
            self._chunk_response(chunk).model_dump(by_alias=True)
            for chunk in self._repository.list_document_chunks(document_id)
        ]

    def delete_document(self, document_id: int) -> None:
        if not self._repository.delete_document(document_id):
            raise BizError(ErrorCode.NOT_FOUND, "Document not found")

    def _response(self, row: dict[str, Any]) -> KnowledgeBaseResponse:
        return KnowledgeBaseResponse(
            id=int(row["id"]),
            name=row["name"],
            description=row["description"] or "",
            enabled=1 if row["enabled"] else 0,
            createdAt=format_datetime(row["created_at"]),
            updatedAt=format_datetime(row["updated_at"]),
        )

    def _document_response(self, row: dict[str, Any]) -> DocumentResponse:
        return DocumentResponse(
            id=int(row["id"]),
            knowledgeBaseId=int(row["knowledge_base_id"]),
            name=row["name"],
            fileType=row["file_type"],
            fileSize=int(row["file_size"]),
            status=row["status"],
            errorMessage=row["error_message"] or "",
            chunkCount=int(row["chunk_count"] or 0),
            createdAt=format_datetime(row["created_at"]),
        )

    def _chunk_response(self, chunk: ChunkRecord) -> ChunkResponse:
        return ChunkResponse(
            id=chunk.id,
            documentId=chunk.document_id,
            chunkIndex=chunk.chunk_index,
            content=chunk.content,
            tokenCount=chunk.token_count,
        )
