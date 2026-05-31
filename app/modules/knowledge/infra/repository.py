from collections.abc import Sequence
from datetime import datetime
import hashlib
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.database import Base
from app.core.schema import register_baseline_tables
from app.modules.knowledge.domain.chunks import ChunkRecord, estimate_token_count
from app.modules.knowledge.domain.vector_search import (
    EmbeddedChunk,
    SimilarChunk,
    rank_embedded_chunks,
)

register_baseline_tables()


class KnowledgeBaseRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._knowledge_base = Base.metadata.tables["knowledge_base"]
        self._document = Base.metadata.tables["document"]
        self._document_chunk = Base.metadata.tables["document_chunk"]
        self._document_embedding = Base.metadata.tables["document_embedding"]

    def list_page(
        self,
        page: int,
        page_size: int,
        name: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._knowledge_base.c.deleted.is_(False)]
        if name:
            conditions.append(self._knowledge_base.c.name.like(f"%{name}%"))
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._knowledge_base).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._knowledge_base)
            .where(*conditions)
            .order_by(self._knowledge_base.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def create(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._knowledge_base.insert()
            .values(
                **values,
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._knowledge_base)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        return row

    def get(self, knowledge_base_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._knowledge_base).where(
                self._knowledge_base.c.id == knowledge_base_id,
                self._knowledge_base.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def update(self, knowledge_base_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
        values["updated_at"] = datetime.now()
        self._session.execute(
            self._knowledge_base.update()
            .where(
                self._knowledge_base.c.id == knowledge_base_id,
                self._knowledge_base.c.deleted.is_(False),
            )
            .values(**values)
        )
        self._session.commit()
        return self.get(knowledge_base_id)

    def delete(self, knowledge_base_id: int) -> bool:
        result = self._session.execute(
            self._knowledge_base.update()
            .where(
                self._knowledge_base.c.id == knowledge_base_id,
                self._knowledge_base.c.deleted.is_(False),
            )
            .values(deleted=True, updated_at=datetime.now())
        )
        self._session.commit()
        return isinstance(result, CursorResult) and result.rowcount > 0

    def create_document(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        result = self._session.execute(
            self._document.insert()
            .values(
                **values,
                status="PENDING",
                error_message="",
                chunk_count=0,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._document)
        )
        row = dict(result.mappings().one())
        self._session.commit()
        return row

    def list_documents(
        self,
        knowledge_base_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [
            self._document.c.knowledge_base_id == knowledge_base_id,
            self._document.c.deleted.is_(False),
        ]
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._document).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._document)
            .where(*conditions)
            .order_by(self._document.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def get_document(self, document_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._document).where(
                self._document.c.id == document_id,
                self._document.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def list_done_documents(self, knowledge_base_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._document)
            .where(
                self._document.c.knowledge_base_id == knowledge_base_id,
                self._document.c.status == "DONE",
                self._document.c.deleted.is_(False),
            )
            .order_by(self._document.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def update_document_processing_state(
        self,
        document_id: int,
        status: str,
        chunk_count: int = 0,
        error_message: str = "",
    ) -> dict[str, Any] | None:
        self._session.execute(
            self._document.update()
            .where(self._document.c.id == document_id, self._document.c.deleted.is_(False))
            .values(
                status=status,
                chunk_count=chunk_count,
                error_message=error_message,
                updated_at=datetime.now(),
            )
        )
        self._session.commit()
        return self.get_document(document_id)

    def replace_document_chunks(self, document_id: int, chunk_texts: Sequence[str]) -> list[ChunkRecord]:
        now = datetime.now()
        self._clear_document_embeddings(document_id)
        self._session.execute(
            self._document_chunk.delete().where(self._document_chunk.c.document_id == document_id)
        )
        rows: list[dict[str, Any]] = []
        for index, content in enumerate(chunk_texts):
            row = dict(
                self._session.execute(
                    self._document_chunk.insert()
                    .values(
                        document_id=document_id,
                        chunk_index=index,
                        content=content,
                        token_count=estimate_token_count(content),
                        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        metadata={},
                        deleted=False,
                        created_at=now,
                        updated_at=now,
                    )
                    .returning(self._document_chunk)
                )
                .mappings()
                .one()
            )
            rows.append(row)
        self._session.commit()
        return [self._chunk_record(row) for row in rows]

    def replace_document_embeddings(
        self,
        chunks: Sequence[ChunkRecord],
        embeddings: Sequence[Sequence[float]],
        model_name: str,
        dimensions: int,
    ) -> list[dict[str, Any]]:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        chunk_ids = [chunk.id for chunk in chunks]
        if not chunk_ids:
            return []
        now = datetime.now()
        self._session.execute(
            self._document_embedding.delete().where(self._document_embedding.c.chunk_id.in_(chunk_ids))
        )
        rows: list[dict[str, Any]] = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            row = dict(
                self._session.execute(
                    self._document_embedding.insert()
                    .values(
                        chunk_id=chunk.id,
                        embedding_model=model_name,
                        embedding=list(embedding),
                        dimension=dimensions,
                        metadata={},
                        deleted=False,
                        created_at=now,
                        updated_at=now,
                    )
                    .returning(self._document_embedding)
                )
                .mappings()
                .one()
            )
            rows.append(row)
        self._session.commit()
        return rows

    def search_similar_chunks(
        self,
        knowledge_base_id: int,
        query_embedding: Sequence[float],
        model_name: str,
        top_k: int,
    ) -> list[SimilarChunk]:
        if top_k <= 0:
            return []
        bind = self._session.get_bind()
        if bind.dialect.name == "postgresql":
            return self._search_similar_chunks_postgresql(
                knowledge_base_id,
                query_embedding,
                model_name,
                top_k,
            )
        return self._search_similar_chunks_in_memory(
            knowledge_base_id,
            query_embedding,
            model_name,
            top_k,
        )

    def list_document_chunks(self, document_id: int) -> list[ChunkRecord]:
        rows = self._session.execute(
            sa.select(self._document_chunk)
            .where(
                self._document_chunk.c.document_id == document_id,
                self._document_chunk.c.deleted.is_(False),
            )
            .order_by(self._document_chunk.c.chunk_index.asc())
        ).mappings().all()
        return [self._chunk_record(dict(row)) for row in rows]

    def clear_document_chunks(self, document_id: int) -> None:
        self._clear_document_embeddings(document_id)
        self._session.execute(
            self._document_chunk.delete().where(self._document_chunk.c.document_id == document_id)
        )
        self._session.commit()

    def delete_document(self, document_id: int) -> bool:
        self.clear_document_chunks(document_id)
        result = self._session.execute(
            self._document.update()
            .where(self._document.c.id == document_id, self._document.c.deleted.is_(False))
            .values(deleted=True, updated_at=datetime.now())
        )
        self._session.commit()
        return isinstance(result, CursorResult) and result.rowcount > 0

    def _chunk_record(self, row: dict[str, Any]) -> ChunkRecord:
        return ChunkRecord(
            id=int(row["id"]),
            document_id=int(row["document_id"]),
            chunk_index=int(row["chunk_index"]),
            content=str(row["content"]),
            token_count=int(row["token_count"] or 0),
        )

    def _clear_document_embeddings(self, document_id: int) -> None:
        chunk_ids = self._session.execute(
            sa.select(self._document_chunk.c.id).where(self._document_chunk.c.document_id == document_id)
        ).scalars().all()
        if not chunk_ids:
            return
        self._session.execute(
            self._document_embedding.delete().where(self._document_embedding.c.chunk_id.in_(chunk_ids))
        )

    def _search_similar_chunks_in_memory(
        self,
        knowledge_base_id: int,
        query_embedding: Sequence[float],
        model_name: str,
        top_k: int,
    ) -> list[SimilarChunk]:
        rows = self._session.execute(
            sa.select(
                self._document_chunk.c.id,
                self._document_chunk.c.document_id,
                self._document_chunk.c.chunk_index,
                self._document_chunk.c.content,
                self._document_chunk.c.token_count,
                self._document_embedding.c.embedding,
            )
            .join(self._document, self._document.c.id == self._document_chunk.c.document_id)
            .join(
                self._document_embedding,
                self._document_embedding.c.chunk_id == self._document_chunk.c.id,
            )
            .where(
                self._document.c.knowledge_base_id == knowledge_base_id,
                self._document.c.status == "DONE",
                self._document.c.deleted.is_(False),
                self._document_chunk.c.deleted.is_(False),
                self._document_embedding.c.deleted.is_(False),
                self._document_embedding.c.embedding_model == model_name,
            )
            .order_by(self._document_chunk.c.chunk_index.asc())
        ).mappings().all()
        candidates = [
            EmbeddedChunk(
                chunk=self._chunk_record(dict(row)),
                embedding=[float(value) for value in row["embedding"]],
            )
            for row in rows
        ]
        return rank_embedded_chunks(candidates, query_embedding, top_k)

    def _search_similar_chunks_postgresql(
        self,
        knowledge_base_id: int,
        query_embedding: Sequence[float],
        model_name: str,
        top_k: int,
    ) -> list[SimilarChunk]:
        vector_literal = "[" + ",".join(str(float(value)) for value in query_embedding) + "]"
        rows = self._session.execute(
            sa.text(
                """
                SELECT
                    dc.id,
                    dc.document_id,
                    dc.chunk_index,
                    dc.content,
                    dc.token_count,
                    1 - (de.embedding <=> CAST(:query_embedding AS vector)) AS score
                FROM document_chunk dc
                JOIN document d ON d.id = dc.document_id
                JOIN document_embedding de ON de.chunk_id = dc.id
                WHERE d.knowledge_base_id = :knowledge_base_id
                  AND d.status = 'DONE'
                  AND d.deleted = false
                  AND dc.deleted = false
                  AND de.deleted = false
                  AND de.embedding_model = :model_name
                ORDER BY de.embedding <=> CAST(:query_embedding AS vector), dc.chunk_index ASC, dc.id ASC
                LIMIT :top_k
                """
            ),
            {
                "knowledge_base_id": knowledge_base_id,
                "query_embedding": vector_literal,
                "model_name": model_name,
                "top_k": top_k,
            },
        ).mappings().all()
        return [
            SimilarChunk(
                chunk=self._chunk_record(dict(row)),
                score=float(row["score"] or 0.0),
            )
            for row in rows
        ]
