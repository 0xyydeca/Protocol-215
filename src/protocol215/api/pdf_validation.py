"""PDF intake validation for amendment uploads."""

from __future__ import annotations

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from protocol215.api.errors import ApiError, ApiErrorCode
from protocol215.application.hashing import sha256_hex


def validate_pdf_upload(
    *,
    filename: str | None,
    data: bytes,
    max_bytes: int,
    max_pages: int,
) -> tuple[str, int]:
    """
    Validate a protocol PDF upload.

    Returns (sha256_hex, page_count).
    Raises ApiError on failure.
    """
    name = (filename or "").strip()
    if not name.lower().endswith(".pdf"):
        raise ApiError(
            error_code=ApiErrorCode.INVALID_PDF,
            message="Only PDF files are accepted.",
            status_code=400,
            details={"filename": name},
        )
    if not data:
        raise ApiError(
            error_code=ApiErrorCode.MALFORMED_PDF,
            message="Uploaded file is empty.",
            status_code=400,
        )
    if len(data) > max_bytes:
        raise ApiError(
            error_code=ApiErrorCode.FILE_TOO_LARGE,
            message=f"PDF exceeds the maximum size of {max_bytes} bytes.",
            status_code=413,
            details={"size": len(data), "max_bytes": max_bytes},
        )
    if not data.startswith(b"%PDF"):
        raise ApiError(
            error_code=ApiErrorCode.INVALID_PDF,
            message="File does not appear to be a PDF (missing magic bytes).",
            status_code=400,
        )
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
    except PdfReadError as exc:
        raise ApiError(
            error_code=ApiErrorCode.MALFORMED_PDF,
            message="PDF could not be parsed.",
            status_code=400,
            details={"reason": "parse_error"},
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise ApiError(
            error_code=ApiErrorCode.MALFORMED_PDF,
            message="PDF could not be parsed.",
            status_code=400,
            details={"reason": "unexpected_parse_error"},
        ) from exc

    if getattr(reader, "is_encrypted", False):
        # Try empty password; still reject if encryption remains.
        try:
            if reader.decrypt("") == 0:  # type: ignore[attr-defined]
                raise ApiError(
                    error_code=ApiErrorCode.ENCRYPTED_PDF,
                    message="Encrypted PDFs are not accepted.",
                    status_code=400,
                )
        except ApiError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ApiError(
                error_code=ApiErrorCode.ENCRYPTED_PDF,
                message="Encrypted PDFs are not accepted.",
                status_code=400,
            ) from exc
        # If decrypt "succeeded" with empty password, still treat as encrypted upload.
        raise ApiError(
            error_code=ApiErrorCode.ENCRYPTED_PDF,
            message="Encrypted PDFs are not accepted.",
            status_code=400,
        )

    try:
        page_count = len(reader.pages)
    except Exception as exc:  # noqa: BLE001
        raise ApiError(
            error_code=ApiErrorCode.MALFORMED_PDF,
            message="PDF page tree is unreadable.",
            status_code=400,
        ) from exc

    if page_count < 1:
        raise ApiError(
            error_code=ApiErrorCode.MALFORMED_PDF,
            message="PDF has no pages.",
            status_code=400,
        )
    if page_count > max_pages:
        raise ApiError(
            error_code=ApiErrorCode.TOO_MANY_PAGES,
            message=f"PDF exceeds the maximum page count of {max_pages}.",
            status_code=400,
            details={"pages": page_count, "max_pages": max_pages},
        )

    return sha256_hex(data), page_count
