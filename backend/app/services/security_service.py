import re
import os
from typing import Tuple, Optional, List
from backend.app.config import settings
from backend.app.logger import logger


class SecurityService:
    # Common prompt injection signatures and adversarial jailbreak patterns
    INJECTION_PATTERNS = [
        r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b",
        r"(?i)\bdisregard\s+(all\s+)?(previous|system)\s+instructions\b",
        r"(?i)\bprint\s+(your\s+)?(system\s+prompt|instructions)\b",
        r"(?i)\breveal\s+(the\s+)?(system\s+prompt|api\s*key|secret|env)\b",
        r"(?i)\bshow\s+me\s+(your\s+)?(system\s+prompt|raw\s+instructions)\b",
        r"(?i)\bwhat\s+(is|are)\s+your\s+(initial|internal|system)\s+instructions\b",
        r"(?i)\benable\s+developer\s+mode\b",
        r"(?i)\bjailbreak\b",
        r"(?i)\b(dan\s+mode|do\s+anything\s+now)\b",
        r"(?i)\b(api_key|openai_api_key|jwt_secret|os\.environ)\b",
        r"(?i)\byou\s+are\s+now\s+an\s+unrestricted\b",
    ]

    # Secret patterns to prevent data leakage in output
    LEAK_PATTERNS = [
        r"sk-[A-Za-z0-9_-]{20,}",  # Typical OpenAI / provider keys
        r"(?i)bearer\s+[A-Za-z0-9_\-\.]{25,}",
        r"(?i)password\s*=\s*['\"][^'\"]+['\"]",
    ]

    @classmethod
    def inspect_query(cls, question: str) -> Tuple[bool, Optional[str]]:
        """
        Inspects incoming query for injection attempts, system prompt extraction,
        and prohibited probing.
        
        Returns:
            Tuple of (is_flagged: bool, reason: Optional[str])
        """
        if not settings.ENABLE_INJECTION_DEFENSE:
            return False, None

        q_clean = question.strip()

        # Check maximum length
        if len(q_clean) > settings.MAX_QUESTION_LENGTH:
            return True, f"Query length ({len(q_clean)}) exceeds maximum allowed limit of {settings.MAX_QUESTION_LENGTH} characters."

        # Scan for known injection and extraction patterns
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, q_clean):
                logger.warning(f"Security Alert: Potential prompt injection / system probe detected in query.")
                return True, "Potential prompt injection or internal instruction extraction attempt detected."

        return False, None

    @classmethod
    def sanitize_context_chunks(cls, chunks_text: str) -> str:
        """
        Neutralizes potential command markers in retrieved untrusted document text.
        Escapes XML-like delimiters to prevent document text breaking out of the context container.
        """
        # Escape context tags so document content cannot inject fake closing tags
        sanitized = chunks_text.replace("</document_context>", "&lt;/document_context&gt;")
        sanitized = sanitized.replace("<document_context>", "&lt;document_context&gt;")
        return sanitized

    @classmethod
    def filter_output_for_leakage(cls, text: str) -> Tuple[str, bool]:
        """
        Scans model output to ensure secrets, environment variables,
        or internal tokens are never returned to the client.
        
        Returns:
            Tuple of (sanitized_text, was_modified)
        """
        modified = False
        result = text

        # Check for configured active secrets
        sensitive_values = []
        if settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY) > 6:
            sensitive_values.append(settings.OPENAI_API_KEY)

        for secret in sensitive_values:
            if secret in result:
                result = result.replace(secret, "[REDACTED_API_KEY]")
                modified = True

        # Check regex leak patterns
        for pattern in cls.LEAK_PATTERNS:
            if re.search(pattern, result):
                result = re.sub(pattern, "[REDACTED_SECRET]", result)
                modified = True

        if modified:
            logger.warning("Security Alert: Redacted sensitive pattern from generated model response.")

        return result, modified


security_service = SecurityService()
