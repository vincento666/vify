from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


def format_datetime(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return value
