# Backend Dockerfile for PDF Q&A RAG Engine
FROM python:3.11-slim

# Prevent Python from writing .pyc and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal OS build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend application and documents
COPY backend /app/backend
COPY documents /app/documents
COPY evaluation /app/evaluation
COPY scripts /app/scripts
COPY pytest.ini /app/pytest.ini

# Ensure directories for data persistence
RUN mkdir -p /app/data/uploads /app/data/chroma

# Pre-seed benchmark document into vector store
RUN python /app/scripts/seed_database.py || true

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
