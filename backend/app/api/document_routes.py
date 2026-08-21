import tempfile
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)

from backend.app.api.document_dependencies import (
    get_document_ingestion_service,
)
from backend.app.api.document_schemas import (
    DocumentIngestionResponse,
)
from backend.app.core.config import settings
from backend.app.rag.documents.service import (
    DocumentIngestionService,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".pdf",
}


MAX_DOCUMENT_FILE_SIZE_BYTES = (
    settings.max_bom_file_size_mb * 1024 * 1024
)


@router.post(
    "/upload",
    response_model=DocumentIngestionResponse,
)
async def upload_document(
    file: UploadFile = File(...),
    ingestion_service: DocumentIngestionService = Depends(
        get_document_ingestion_service,
    ),
) -> DocumentIngestionResponse:
    """
    Upload and index an engineering document.

    Currently supports PDF datasheets.
    """

    # ---------------------------------------------------------
    # 1. Validate filename
    # ---------------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="An engineering document is required.",
        )

    safe_filename = Path(
        file.filename
    ).name

    if not safe_filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid document filename.",
        )

    # ---------------------------------------------------------
    # 2. Validate file format
    # ---------------------------------------------------------

    extension = Path(
        safe_filename
    ).suffix.lower()

    if extension not in (
        SUPPORTED_DOCUMENT_EXTENSIONS
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported document format: {extension}. "
                "Currently supported formats are: "
                f"{', '.join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))}"
            ),
        )

    # ---------------------------------------------------------
    # 3. Save upload with size protection
    # ---------------------------------------------------------

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = (
                Path(temp_dir)
                / safe_filename
            )

            file_size = 0

            with temp_file.open("wb") as destination:
                while chunk := file.file.read(
                    1024 * 1024
                ):
                    file_size += len(chunk)

                    if (
                        file_size
                        > MAX_DOCUMENT_FILE_SIZE_BYTES
                    ):
                        raise HTTPException(
                            status_code=413,
                            detail=(
                                "Document file exceeds the "
                                "maximum allowed size of "
                                f"{settings.max_bom_file_size_mb} MB."
                            ),
                        )

                    destination.write(chunk)

            # -------------------------------------------------
            # 4. Reject empty files
            # -------------------------------------------------

            if file_size == 0:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "The uploaded document file is empty."
                    ),
                )

            # -------------------------------------------------
            # 5. Run document ingestion
            # -------------------------------------------------

            result = await ingestion_service.ingest(
                file_path=temp_file,
            )

        return DocumentIngestionResponse(
            document_id=result["document_id"],
            source=result["source"],
            pages_processed=result["pages_processed"],
            chunks_created=result["chunks_created"],
            chunks_indexed=result["chunks_indexed"],
        )

    # ---------------------------------------------------------
    # Expected HTTP errors
    # ---------------------------------------------------------

    except HTTPException:
        raise

    # ---------------------------------------------------------
    # Expected ingestion failures
    # ---------------------------------------------------------

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    # ---------------------------------------------------------
    # Unexpected failures
    # ---------------------------------------------------------

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Document ingestion failed.",
        ) from exc