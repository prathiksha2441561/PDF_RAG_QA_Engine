import pytest
from backend.app.services.pdf_service import PDFService, PDFProcessingError
from backend.app.config import settings


def test_validate_pdf_valid(sample_pdf_bytes):
    # Should not raise exception
    PDFService.validate_pdf_file("valid_doc.pdf", len(sample_pdf_bytes), "application/pdf")


def test_validate_pdf_invalid_extension():
    with pytest.raises(PDFProcessingError) as exc_info:
        PDFService.validate_pdf_file("malicious.exe", 1024, "application/octet-stream")
    assert "Only PDF files (.pdf) are allowed" in str(exc_info.value)


def test_validate_pdf_empty_file():
    with pytest.raises(PDFProcessingError) as exc_info:
        PDFService.validate_pdf_file("empty.pdf", 0, "application/pdf")
    assert "is empty" in str(exc_info.value)


def test_validate_pdf_oversized():
    oversized = (settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024) + 100
    with pytest.raises(PDFProcessingError) as exc_info:
        PDFService.validate_pdf_file("large.pdf", oversized, "application/pdf")
    assert "exceeds maximum allowed size" in str(exc_info.value)


def test_extract_text_valid(sample_pdf_bytes):
    doc_id, path, pages = PDFService.save_and_extract_text(sample_pdf_bytes, "test_doc.pdf")
    assert doc_id is not None
    assert len(pages) == 1
    assert pages[0]["page_number"] == 1
    assert "OAuth 2.0" in pages[0]["text"]


def test_extract_text_corrupted_header():
    corrupted_bytes = b"NOT_A_REAL_PDF_HEADER"
    with pytest.raises(PDFProcessingError) as exc_info:
        PDFService.save_and_extract_text(corrupted_bytes, "corrupted.pdf")
    assert "missing %PDF- header" in str(exc_info.value)
