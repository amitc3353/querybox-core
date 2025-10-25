# app/services/chunking/token_counter.py

from transformers import AutoTokenizer
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TokenCounter:
    """Accurate token counting using the actual embedding model's tokenizer

    Uses BGE-M3's XLMRobertaTokenizer for exact token counting that matches
    the embedding model. Runs 100% locally with no external API calls.
    """

    def __init__(self, model: str = "BAAI/bge-m3"):
        """
        Initialize token counter with embedding model's tokenizer

        Args:
            model: HuggingFace model name (default: BAAI/bge-m3)
                  Tokenizer is downloaded once and cached locally.
        """
        try:
            # Load tokenizer locally - downloads once, then cached
            self.tokenizer = AutoTokenizer.from_pretrained(
                model,
                trust_remote_code=False  # Security: don't execute remote code
            )
            logger.info(f"TokenCounter initialized with {model} tokenizer")
        except Exception as e:
            logger.error(f"Failed to load tokenizer for {model}: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        """Count exact tokens using the embedding model's tokenizer

        Args:
            text: Input text to tokenize

        Returns:
            Number of tokens (excluding special tokens like [CLS], [SEP])
        """
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to specified token count

        Args:
            text: Input text to truncate
            max_tokens: Maximum number of tokens to keep

        Returns:
            Truncated text decoded from tokens
        """
        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        if len(tokens) <= max_tokens:
            return text

        truncated_tokens = tokens[:max_tokens]
        return self.tokenizer.decode(truncated_tokens, skip_special_tokens=True)
