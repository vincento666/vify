from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from typing import Any


class KnowledgeBaseCreateRequest(BaseModel):
    name: str
    description: str = ""


class KnowledgeBaseUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: int | None = None


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    description: str
    enabled: int
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class KnowledgeBasePageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    list: list[KnowledgeBaseResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class DocumentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    knowledge_base_id: int = Field(alias="knowledgeBaseId")
    name: str
    file_type: str = Field(alias="fileType")
    file_size: int = Field(alias="fileSize")
    status: str
    error_message: str = Field(alias="errorMessage")
    chunk_count: int = Field(alias="chunkCount")
    created_at: str = Field(alias="createdAt")


class DocumentPageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    list: list[DocumentResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class ChunkResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    document_id: int = Field(alias="documentId")
    chunk_index: int = Field(alias="chunkIndex")
    content: str
    token_count: int = Field(alias="tokenCount")


class FaqCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question: str
    answer: str
    alternative_questions: list[str] = Field(default_factory=list, alias="alternativeQuestions")
    keywords: list[str] = Field(default_factory=list)
    category: str = ""
    priority: int = 0
    enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = "manual"


class FaqUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question: str | None = None
    answer: str | None = None
    alternative_questions: list[str] | None = Field(default=None, alias="alternativeQuestions")
    keywords: list[str] | None = None
    category: str | None = None
    priority: int | None = None
    enabled: bool | None = None
    metadata: dict[str, Any] | None = None
    source: str | None = None


class FaqResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    knowledge_base_id: int = Field(alias="knowledgeBaseId")
    question: str
    answer: str
    alternative_questions: list[str] = Field(alias="alternativeQuestions")
    keywords: list[str]
    category: str
    priority: int
    enabled: bool
    metadata: dict[str, Any]
    source: str
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class FaqPageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    list: list[FaqResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class FaqImportResponse(BaseModel):
    imported: int


class RetrievalTestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    query: str
    top_k: int = Field(default=3, alias="topK")
    retrieval_mode: str = Field(default="auto", alias="retrievalMode")
    score_threshold: float = Field(default=0.0, alias="scoreThreshold")
    rerank: bool = False


class RetrievalHitResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_type: str = Field(alias="sourceType")
    match_type: str = Field(alias="matchType")
    score: float
    title: str
    content: str
    answer: str = ""
    faq_id: int = Field(default=0, alias="faqId")
    document_id: int = Field(default=0, alias="documentId")
    chunk_id: int = Field(default=0, alias="chunkId")
    chunk_index: int = Field(default=0, alias="chunkIndex")
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalTestResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    query: str
    retrieval_mode: str = Field(alias="retrievalMode")
    hits: list[RetrievalHitResponse]


def format_datetime(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return value
