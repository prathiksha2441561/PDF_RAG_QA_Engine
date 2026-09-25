import os
import uuid
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Any, Tuple
from backend.app.config import settings
from backend.app.logger import logger


class PDFProcessingError(Exception):
    """Custom exception raised when PDF validation or extraction fails."""
    pass


class PDFService:
    @staticmethod
    def validate_pdf_file(filename: str, file_size: int, content_type: str = "") -> None:
        """
        Validates file extension, MIME type, and size constraints.
        Raises PDFProcessingError if validation fails.
        """
        if not filename.lower().endswith(".pdf"):
            raise PDFProcessingError(f"Invalid file type for '{filename}'. Only PDF files (.pdf) are allowed.")

        if content_type and content_type != "application/pdf" and content_type != "application/x-pdf":
            # Some clients might send application/octet-stream; if extension is .pdf, we will verify header magic bytes
            logger.warning(f"File '{filename}' content-type is '{content_type}', verifying magic bytes...")

        max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            raise PDFProcessingError(
                f"File '{filename}' exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
            )

        if file_size == 0:
            raise PDFProcessingError(f"Uploaded file '{filename}' is empty (0 bytes).")

    @classmethod
    def save_and_extract_text(
        cls,
        file_bytes: bytes,
        original_filename: str
    ) -> Tuple[str, str, List[Dict[str, Any]]]:
        """
        Validates magic bytes, saves PDF to storage directory, and extracts text page-by-page.
        
        Returns:
            Tuple of (document_id, saved_filepath, extracted_pages)
            where extracted_pages is a list of dicts:
            [{"page_number": int, "text": str, "char_count": int}, ...]
        """
        cls.validate_pdf_file(original_filename, len(file_bytes))

        # Validate PDF magic bytes (%PDF-)
        if not file_bytes.startswith(b"%PDF-"):
            raise PDFProcessingError(f"File '{original_filename}' is not a valid PDF binary (missing %PDF- header).")

        document_id = str(uuid.uuid4())
        safe_filename = f"{document_id}_{Path(original_filename).name}"
        save_path = Path(settings.UPLOAD_DIR) / safe_filename

        try:
            with open(save_path, "wb") as f:
                f.write(file_bytes)
        except Exception as e:
            logger.error(f"Failed to save uploaded file to disk: {str(e)}")
            raise PDFProcessingError(f"Could not persist uploaded file: {str(e)}")

        extracted_pages: List[Dict[str, Any]] = []

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            logger.error(f"Corrupted or unreadable PDF '{original_filename}': {str(e)}")
            # Cleanup saved file if invalid
            if save_path.exists():
                save_path.unlink()
            raise PDFProcessingError(f"PDF document is corrupted or password-protected and cannot be read.")

        try:
            total_pages = len(doc)
            if total_pages == 0:
                raise PDFProcessingError(f"PDF document '{original_filename}' contains 0 pages.")

            for page_idx in range(total_pages):
                page_num = page_idx + 1
                try:
                    page = doc.load_page(page_idx)
                    text = page.get_text("text").strip()
                    # Keep record even if page is blank/scanned, but mark text length
                    extracted_pages.append({
                        "page_number": page_num,
                        "text": text,
                        "char_count": len(text)
                    })
                except Exception as page_err:
                    logger.warning(f"Warning reading page {page_num} of {original_filename}: {str(page_err)}")
                    extracted_pages.append({
                        "page_number": page_num,
                        "text": "",
                        "char_count": 0
                    })
        finally:
            doc.close()

        # Check if the entire PDF yielded no extractable text
        total_text_chars = sum(p["char_count"] for p in extracted_pages)
        if total_text_chars == 0:
            logger.warning(f"PDF '{original_filename}' contains no extractable text (might be scanned images).")

        logger.info(
            f"Successfully processed PDF '{original_filename}' [ID: {document_id}]: "
            f"{len(extracted_pages)} pages extracted, {total_text_chars} total characters."
        )

        return document_id, str(save_path), extracted_pages
