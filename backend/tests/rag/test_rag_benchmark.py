from pathlib import Path
from statistics import mean
from time import perf_counter

import fitz
import pytest
from qdrant_client import QdrantClient

from backend.app.rag.chunking import DocumentChunker
from backend.app.rag.documents.pdf import PDFDocumentLoader
from backend.app.rag.embeddings import (
    DeterministicEmbeddingProvider,
)
from backend.app.rag.evidence import RAGEvidenceBuilder
from backend.app.rag.indexer import RAGIndexer
from backend.app.rag.reranker import RAGReranker
from backend.app.rag.retriever import RAGRetriever
from backend.app.rag.service import RAGService
from backend.app.rag.vector_store import QdrantVectorStore


def create_benchmark_pdf(
    file_path: Path,
) -> None:
    """Create a deterministic engineering datasheet."""

    document = fitz.open()

    try:
        page_one = document.new_page()
        page_one.insert_text(
            (72, 72),
            "TPS7A4901 Datasheet\n"
            "Product Overview\n"
            "Low-noise linear regulator.",
        )

        page_two = document.new_page()
        page_two.insert_text(
            (72, 72),
            "TPS7A4901 Electrical Characteristics\n"
            "Input voltage range: 3 V to 36 V.\n"
            "Maximum output current: 300 mA.",
        )

        page_three = document.new_page()
        page_three.insert_text(
            (72, 72),
            "TPS7A4901 Operating Conditions\n"
            "Operating temperature: -40 C to 125 C.",
        )

        document.save(file_path)
    finally:
        document.close()


@pytest.mark.asyncio
async def test_rag_retrieval_benchmark(
    tmp_path: Path,
) -> None:
    """Benchmark deterministic RAG retrieval quality and latency."""

    pdf_path = (
        tmp_path / "TPS7A4901_benchmark.pdf"
    )

    create_benchmark_pdf(pdf_path)

    loader = PDFDocumentLoader()

    parsed_document = loader.load(
        pdf_path,
    )

    assert len(parsed_document.pages) == 3

    chunker = DocumentChunker(
        chunk_size=1000,
        chunk_overlap=0,
    )

    chunks = chunker.chunk_parsed_document(
        parsed_document,
    )

    assert len(chunks) == 3

    client = QdrantClient(
        location=":memory:",
    )

    embedding_provider = (
        DeterministicEmbeddingProvider(
            dimension=8,
        )
    )

    vector_store = QdrantVectorStore(
        client,
        collection_name="rag_benchmark",
        vector_size=embedding_provider.dimension,
    )

    vector_store.ensure_collection()

    indexer = RAGIndexer(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    indexed_count = await indexer.index(
        chunks=chunks,
    )

    assert indexed_count == len(chunks)

    retriever = RAGRetriever(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    rag_service = RAGService(
        retriever=retriever,
        reranker=RAGReranker(),
        evidence_builder=RAGEvidenceBuilder(),
    )

    cases = (
        (
            "Input voltage range: 3 V to 36 V.",
            "Input voltage range: 3 V to 36 V.",
            2,
        ),
        (
            "Maximum output current: 300 mA.",
            "Maximum output current: 300 mA.",
            2,
        ),
        (
            "Operating temperature: -40 C to 125 C.",
            "Operating temperature: -40 C to 125 C.",
            3,
        ),
    )

    latencies_ms: list[float] = []
    hits = 0

    for (
        query,
        expected_text,
        expected_page,
    ) in cases:
        start = perf_counter()

        evidence = (
            await rag_service.retrieve_evidence(
                query=query,
                retrieval_limit=3,
                evidence_limit=1,
            )
        )

        elapsed_ms = (
            perf_counter() - start
        ) * 1000

        latencies_ms.append(
            elapsed_ms,
        )

        assert evidence

        result = evidence[0]

        assert result.source == "rag"
        assert result.excerpt is not None

        chunk_metadata = result.metadata[
            "chunk_metadata"
        ]

        page_number = chunk_metadata[
            "page_number"
        ]

        if (
            expected_text in result.excerpt
            and page_number == expected_page
        ):
            hits += 1

    query_count = len(cases)

    hit_rate = (
        hits / query_count
    )

    ordered_latencies = sorted(
        latencies_ms,
    )

    p95_position = int(
        len(ordered_latencies) * 0.95
    )

    p95_index = min(
        len(ordered_latencies) - 1,
        p95_position,
    )

    p95_ms = ordered_latencies[
        p95_index
    ]

    mean_ms = mean(
        latencies_ms,
    )

    print()
    print("RAG retrieval benchmark:")
    print(
        f"  queries: {query_count}"
    )
    print(
        f"  hits: {hits}"
    )
    print(
        f"  hit rate: {hit_rate:.2%}"
    )
    print(
        f"  mean latency: {mean_ms:.3f} ms"
    )
    print(
        f"  p95 latency: {p95_ms:.3f} ms"
    )

    assert hits == query_count
    assert hit_rate == 1.0