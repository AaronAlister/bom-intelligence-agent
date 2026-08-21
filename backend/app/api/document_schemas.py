from pydantic import BaseModel, Field


class DocumentIngestionResponse(BaseModel):
    """
    API response returned after engineering document ingestion.
    """

    document_id: str = Field(
        ...,
        description="Deterministic identifier for the ingested document.",
    )

    source: str = Field(
        ...,
        description="Original uploaded filename.",
    )

    pages_processed: int = Field(
        ...,
        ge=1,
        description="Number of pages processed from the document.",
    )

    chunks_created: int = Field(
        ...,
        ge=1,
        description="Number of RAG chunks created.",
    )

    chunks_indexed: int = Field(
        ...,
        ge=0,
        description="Number of chunks successfully indexed.",
    )