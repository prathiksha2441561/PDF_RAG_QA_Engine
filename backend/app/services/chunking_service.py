import re
import uuid
from typing import List, Dict, Any, Optional
from backend.app.config import settings
from backend.app.logger import logger


class ChunkingService:
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) must be strictly less than chunk_size ({self.chunk_size})"
            )

    def _split_into_semantic_segments(self, text: str) -> List[str]:
        """
        Splits raw text into natural semantic units:
        paragraphs -> sentences -> words, avoiding cutting sentences or words midway.
        """
        # Normalize whitespace and carriage returns
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Split primarily on double line-breaks (paragraphs) or sentence delimiters
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        segments: List[str] = []
        for para in paragraphs:
            # Split paragraph into sentences using regex matching punctuation + space
            sentences = re.split(r'(?<=[.?!])\s+', para)
            for s in sentences:
                s = s.strip()
                if s:
                    segments.append(s)
        return segments

    def chunk_page_text(
        self,
        text: str,
        document_id: str,
        filename: str,
        page_number: int
    ) -> List[Dict[str, Any]]:
        """
        Splits page text into overlapping, boundary-aware chunks preserving full metadata.
        
        Returns:
            List of chunk dictionaries:
            [
                {
                    "chunk_id": str,
                    "document_id": str,
                    "filename": str,
                    "page_number": int,
                    "text": str,
                    "char_count": int
                },
                ...
            ]
        """
        clean_text = text.strip()
        if not clean_text:
            return []

        segments = self._split_into_semantic_segments(clean_text)
        if not segments:
            segments = [clean_text]

        chunks: List[Dict[str, Any]] = []
        current_chunk_segments: List[str] = []
        current_length = 0

        for segment in segments:
            segment_len = len(segment)

            # If adding this segment exceeds chunk_size and we already have content
            if current_chunk_segments and (current_length + segment_len + 1 > self.chunk_size):
                chunk_str = " ".join(current_chunk_segments).strip()
                chunk_id = f"{document_id}_p{page_number}_c{len(chunks) + 1}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "filename": filename,
                    "page_number": page_number,
                    "text": chunk_str,
                    "char_count": len(chunk_str)
                })

                # Carry over overlap from the end of current_chunk_segments
                overlap_segments: List[str] = []
                overlap_len = 0
                for prev_seg in reversed(current_chunk_segments):
                    if overlap_len + len(prev_seg) + 1 <= self.chunk_overlap:
                        overlap_segments.insert(0, prev_seg)
                        overlap_len += len(prev_seg) + 1
                    else:
                        break

                current_chunk_segments = overlap_segments
                current_length = sum(len(s) + 1 for s in current_chunk_segments)

            # If a single segment itself is longer than chunk_size, split by words
            if segment_len > self.chunk_size:
                words = segment.split()
                sub_chunk: List[str] = []
                sub_len = 0
                for w in words:
                    if sub_len + len(w) + 1 > self.chunk_size and sub_chunk:
                        sub_text = " ".join(sub_chunk).strip()
                        chunk_id = f"{document_id}_p{page_number}_c{len(chunks) + 1}"
                        chunks.append({
                            "chunk_id": chunk_id,
                            "document_id": document_id,
                            "filename": filename,
                            "page_number": page_number,
                            "text": sub_text,
                            "char_count": len(sub_text)
                        })
                        sub_chunk = []
                        sub_len = 0
                    sub_chunk.append(w)
                    sub_len += len(w) + 1
                if sub_chunk:
                    current_chunk_segments = sub_chunk
                    current_length = sub_len
            else:
                current_chunk_segments.append(segment)
                current_length += segment_len + 1

        # Flush any remaining buffer
        if current_chunk_segments:
            chunk_str = " ".join(current_chunk_segments).strip()
            if chunk_str:
                chunk_id = f"{document_id}_p{page_number}_c{len(chunks) + 1}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "filename": filename,
                    "page_number": page_number,
                    "text": chunk_str,
                    "char_count": len(chunk_str)
                })

        return chunks

    def chunk_document(
        self,
        extracted_pages: List[Dict[str, Any]],
        document_id: str,
        filename: str
    ) -> List[Dict[str, Any]]:
        """Processes all pages of a document and returns a consolidated list of chunks."""
        all_chunks: List[Dict[str, Any]] = []
        for page in extracted_pages:
            page_chunks = self.chunk_page_text(
                text=page["text"],
                document_id=document_id,
                filename=filename,
                page_number=page["page_number"]
            )
            all_chunks.extend(page_chunks)

        logger.info(
            f"Chunked document '{filename}' into {len(all_chunks)} chunks "
            f"(chunk_size={self.chunk_size}, chunk_overlap={self.chunk_overlap})"
        )
        return all_chunks
