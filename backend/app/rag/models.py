from typing import Any

from pydantic import BaseModel, Field


class Document(BaseModel):
    """
    Source document used for retrieval.

    A document represents the original engineering or
    procurement source before it is split into chunks.
    """

    document_id: str
    title: str

    source: str

    source_url: str | None = None

    manufacturer: str | None = None
    mpn: str | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class DocumentChunk(BaseModel):
    """
    Retrieval unit produced by the document chunking stage.
    """

    chunk_id: str
    document_id: str

    text: str

    chunk_index: int

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )


class RetrievedChunk(BaseModel):
    """
    Chunk returned by a retrieval operation.

    The score represents the retrieval system's relevance
    score. Its exact interpretation depends on the backend.
    """

    chunk: DocumentChunk

    score: float

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )