import hashlib
import numpy as np
from typing import List, Dict, Optional, Union
from backend.app.config import settings
from backend.app.logger import logger


class EmbeddingService:
    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.device = device or settings.EMBEDDING_DEVICE
        self._model = None
        self._cache: Dict[str, List[float]] = {}  # sha256(text) -> embedding

    def _get_model(self):
        """Lazy load the sentence-transformers model to save memory until needed."""
        if self._model is None:
            if self.model_name.lower() in ("mock", "test"):
                logger.info("Using deterministic mock embedding model for testing/offline mode.")
                return None
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model '{self.model_name}' on device '{self.device}'...")
                self._model = SentenceTransformer(self.model_name, device=self.device)
                logger.info("Embedding model loaded successfully.")
            except Exception as e:
                logger.warning(
                    f"Could not load SentenceTransformer '{self.model_name}': {str(e)}. "
                    "Falling back to deterministic hashed vector embedding for local reliability."
                )
                self._model = None
        return self._model

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    def _deterministic_embedding(self, text: str, dim: int = 384) -> List[float]:
        """
        Generates a deterministic pseudo-semantic normalized embedding vector
        based on character and word n-grams. Used when running offline or in unit tests.
        """
        vec = np.zeros(dim, dtype=np.float32)
        words = text.lower().split()
        for i, word in enumerate(words):
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            sign = 1.0 if ((h >> 8) % 2 == 0) else -1.0
            vec[idx] += sign * (1.0 / (1.0 + 0.1 * i))

        # Add character bi-grams for slight sub-word similarity
        for i in range(len(text) - 1):
            bg = text[i:i+2].lower()
            h = int(hashlib.md5(bg.encode("utf-8")).hexdigest(), 16)
            idx = (h >> 3) % dim
            vec[idx] += 0.2

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a list of texts, utilizing an in-memory cache to avoid duplicate computations.
        """
        results: List[Optional[List[float]]] = [None] * len(texts)
        texts_to_compute: List[str] = []
        indices_to_compute: List[int] = []

        # Check cache
        for idx, text in enumerate(texts):
            h = self._hash_text(text)
            if h in self._cache:
                results[idx] = self._cache[h]
            else:
                texts_to_compute.append(text)
                indices_to_compute.append(idx)

        # Compute missing embeddings
        if texts_to_compute:
            model = self._get_model()
            if model is not None:
                embeddings = model.encode(
                    texts_to_compute,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False
                )
                computed = [emb.tolist() for emb in embeddings]
            else:
                computed = [self._deterministic_embedding(t) for t in texts_to_compute]

            # Store in cache and populate results
            for idx, text, emb in zip(indices_to_compute, texts_to_compute, computed):
                h = self._hash_text(text)
                self._cache[h] = emb
                results[idx] = emb

        return [r for r in results if r is not None]

    def embed_query(self, query: str) -> List[float]:
        """Convenience method to embed a single user query."""
        return self.embed_texts([query])[0]


# Singleton instance
embedding_service = EmbeddingService()
