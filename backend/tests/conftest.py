import pytest
import os
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import settings

# Force offline/mock mode for deterministic and fast tests
os.environ["LLM_PROVIDER"] = "mock"
os.environ["ENABLE_INJECTION_DEFENSE"] = "true"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_pdf_bytes():
    """Generates a minimal valid PDF binary with extractable text."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        fitz.Point(50, 72),
        "Architecture Overview: The platform uses OAuth 2.0 with PKCE and JWT tokens with 15-minute expiry. "
        "PostgreSQL 16 is used for metadata storage and ChromaDB for vector retrieval."
    )
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes
