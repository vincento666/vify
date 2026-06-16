from __future__ import annotations

from collections.abc import Sequence
import csv
from dataclasses import dataclass
import io
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.knowledge.domain.chunks import (
    ChunkRecord,
    split_document_chunks,
)
from app.modules.knowledge.domain.embeddings import create_embedding_provider
from app.modules.knowledge.domain.files import document_extension, validate_document_file
from app.modules.knowledge.domain.parser import parse_document_content
from app.modules.knowledge.domain.retrieval import RetrievalOptions
from app.modules.knowledge.domain.vector_store import VectorStore, create_vector_store
from app.modules.knowledge.infra.repository import KnowledgeBaseRepository
from app.modules.knowledge.web.schemas import (
    ChunkResponse,
    DocumentPageResponse,
    DocumentResponse,
    FaqCreateRequest,
    FaqImportResponse,
    FaqPageResponse,
    FaqResponse,
    FaqUpdateRequest,
    KnowledgeBaseCreateRequest,
    KnowledgeBasePageResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdateRequest,
    RetrievalHitResponse,
    RetrievalTestRequest,
    RetrievalTestResponse,
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
        self._embedding_provider = create_embedding_provider()
        self._vector_store: VectorStore = create_vector_store(self._repository)

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
            embedding_rows = self._get_vector_store().replace_document_embeddings(
                int(row["knowledge_base_id"]),
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
            self._get_vector_store().delete_document_embeddings(
                int(row["knowledge_base_id"]),
                document_id,
                self._embedding_provider.model_name,
            )
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
        row = self._repository.get_document(document_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Document not found")
        self._get_vector_store().delete_document_embeddings(
            int(row["knowledge_base_id"]),
            document_id,
            self._embedding_provider.model_name,
        )
        if not self._repository.delete_document(document_id):
            raise BizError(ErrorCode.NOT_FOUND, "Document not found")

    def list_faqs(self, knowledge_base_id: int, page: int, page_size: int) -> dict[str, Any]:
        if self._repository.get(knowledge_base_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Knowledge base not found")
        rows, total = self._repository.list_faqs(knowledge_base_id, page, page_size)
        response = FaqPageResponse(
            list=[self._faq_response(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def create_faq(self, knowledge_base_id: int, request: FaqCreateRequest) -> dict[str, Any]:
        if self._repository.get(knowledge_base_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Knowledge base not found")
        row = self._repository.create_faq(
            {
                "knowledge_base_id": knowledge_base_id,
                "question": request.question,
                "answer": request.answer,
                "alternative_questions": request.alternative_questions,
                "keywords": request.keywords,
                "category": request.category,
                "priority": request.priority,
                "enabled": request.enabled,
                "metadata": request.metadata,
                "source": request.source,
            }
        )
        if row.get("enabled"):
            self._replace_faq_embedding(row)
        return self._faq_response(row).model_dump(by_alias=True)

    def update_faq(self, faq_id: int, request: FaqUpdateRequest) -> dict[str, Any]:
        values = request.model_dump(exclude_unset=True, by_alias=False)
        if "alternative_questions" in values and values["alternative_questions"] is None:
            values.pop("alternative_questions")
        row = self._repository.update_faq(faq_id, values)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "FAQ not found")
        if row.get("enabled"):
            self._replace_faq_embedding(row)
        else:
            self._get_vector_store().delete_faq_embeddings(
                int(row["knowledge_base_id"]),
                faq_id,
                self._embedding_provider.model_name,
            )
        return self._faq_response(row).model_dump(by_alias=True)

    def delete_faq(self, faq_id: int) -> None:
        row = self._repository.get_faq(faq_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "FAQ not found")
        self._get_vector_store().delete_faq_embeddings(
            int(row["knowledge_base_id"]),
            faq_id,
            self._embedding_provider.model_name,
        )
        if not self._repository.delete_faq(faq_id):
            raise BizError(ErrorCode.NOT_FOUND, "FAQ not found")

    def import_faq_csv(self, knowledge_base_id: int, content: bytes) -> dict[str, Any]:
        if self._repository.get(knowledge_base_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Knowledge base not found")
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        imported = 0
        for row in reader:
            question = str(row.get("question") or "").strip()
            answer = str(row.get("answer") or "").strip()
            if not question or not answer:
                continue
            row = self._repository.create_faq(
                {
                    "knowledge_base_id": knowledge_base_id,
                    "question": question,
                    "answer": answer,
                    "alternative_questions": _split_csv_list(row.get("alternative_questions") or row.get("alternativeQuestions")),
                    "keywords": _split_csv_list(row.get("keywords")),
                    "category": str(row.get("category") or ""),
                    "priority": int(row.get("priority") or 0),
                    "enabled": str(row.get("enabled") or "true").lower() not in {"false", "0", "no"},
                    "metadata": {},
                    "source": str(row.get("source") or "csv"),
                }
            )
            if row.get("enabled"):
                self._replace_faq_embedding(row)
            imported += 1
        return FaqImportResponse(imported=imported).model_dump(by_alias=True)

    def export_faq_csv(self, knowledge_base_id: int) -> str:
        if self._repository.get(knowledge_base_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Knowledge base not found")
        rows, _total = self._repository.list_faqs(knowledge_base_id, 1, 10000)
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["question", "answer", "alternative_questions", "keywords", "category", "priority", "enabled", "source"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "question": row["question"],
                    "answer": row["answer"],
                    "alternative_questions": "|".join(_string_list(row.get("alternative_questions"))),
                    "keywords": "|".join(_string_list(row.get("keywords"))),
                    "category": row.get("category") or "",
                    "priority": int(row.get("priority") or 0),
                    "enabled": "true" if row.get("enabled") else "false",
                    "source": row.get("source") or "manual",
                }
            )
        return output.getvalue()

    def retrieval_test(self, knowledge_base_id: int, request: RetrievalTestRequest) -> dict[str, Any]:
        if self._repository.get(knowledge_base_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Knowledge base not found")
        options = RetrievalOptions.from_request(
            retrieval_mode=request.retrieval_mode,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            rerank=request.rerank,
        )
        hits = KnowledgeFacade(self._repository._session).search_context(
            knowledge_base_id,
            request.query,
            options=options,
        )
        response = RetrievalTestResponse(
            query=request.query,
            retrievalMode=options.mode.value,
            hits=[
                RetrievalHitResponse(
                    sourceType=hit.source_type,
                    matchType=hit.match_type,
                    score=hit.score,
                    title=hit.title,
                    content=hit.content,
                    answer=hit.answer,
                    faqId=hit.faq_id,
                    documentId=hit.document_id,
                    chunkId=hit.chunk_id,
                    chunkIndex=hit.chunk_index,
                    metadata=hit.metadata or {},
                )
                for hit in hits
            ],
        )
        return response.model_dump(by_alias=True)

    def _replace_faq_embedding(self, row: dict[str, Any]) -> None:
        text = _faq_embedding_text(row)
        embedding = self._embedding_provider.embed([text])[0]
        self._get_vector_store().replace_faq_embeddings(
            int(row["knowledge_base_id"]),
            [row],
            [embedding],
            self._embedding_provider.model_name,
            self._embedding_provider.dimensions,
        )

    def _get_vector_store(self) -> VectorStore:
        return getattr(self, "_vector_store", create_vector_store(self._repository))

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

    def _faq_response(self, row: dict[str, Any]) -> FaqResponse:
        return FaqResponse(
            id=int(row["id"]),
            knowledgeBaseId=int(row["knowledge_base_id"]),
            question=row["question"],
            answer=row["answer"],
            alternativeQuestions=_string_list(row.get("alternative_questions")),
            keywords=_string_list(row.get("keywords")),
            category=row.get("category") or "",
            priority=int(row.get("priority") or 0),
            enabled=bool(row.get("enabled")),
            metadata=dict(row.get("metadata") or {}),
            source=row.get("source") or "manual",
            createdAt=format_datetime(row["created_at"]),
            updatedAt=format_datetime(row["updated_at"]),
        )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _split_csv_list(value: Any) -> list[str]:
    raw = str(value or "")
    if not raw.strip():
        return []
    return [item.strip() for item in raw.replace(";", "|").split("|") if item.strip()]


def _faq_embedding_text(row: dict[str, Any]) -> str:
    parts = [
        str(row.get("question") or ""),
        str(row.get("answer") or ""),
        *[str(item) for item in _string_list(row.get("alternative_questions"))],
        *[str(item) for item in _string_list(row.get("keywords"))],
        str(row.get("category") or ""),
    ]
    return "\n".join(part for part in parts if part.strip())
