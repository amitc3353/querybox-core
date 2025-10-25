# app/services/chunking/sentence_splitter.py

import spacy
import nltk
import re
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Sentence:
    """Represents a sentence with metadata"""
    text: str
    start_char: int
    end_char: int
    tokens: List[str]
    token_count: int
    is_heading: bool
    part_of_list: bool


class SentenceSplitter:
    """Intelligent sentence splitting with spaCy/NLTK

    Uses spaCy for accurate sentence boundary detection with fallback to NLTK.
    Runs 100% locally with no external API calls.
    """

    def __init__(self, use_spacy: bool = True):
        """
        Initialize sentence splitter

        Args:
            use_spacy: If True, attempt to use spaCy (more accurate).
                      Falls back to NLTK if spaCy model not found.
        """
        self.use_spacy = use_spacy

        if use_spacy:
            try:
                # Load spaCy model (en_core_web_sm)
                # Disable NER and parser for speed (we only need sentence boundaries)
                self.nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
                self.nlp.add_pipe("sentencizer")
                logger.info("SentenceSplitter initialized with spaCy")
            except OSError:
                # Fallback to NLTK if spaCy model not found
                logger.warning("spaCy model not found, falling back to NLTK")
                self.use_spacy = False

        if not self.use_spacy:
            # Download NLTK punkt tokenizer if needed
            try:
                nltk.data.find('tokenizers/punkt')
                logger.info("SentenceSplitter initialized with NLTK")
            except LookupError:
                logger.info("Downloading NLTK punkt tokenizer...")
                nltk.download('punkt', quiet=True)
                nltk.download('punkt_tab', quiet=True)

    def split_sentences(self, text: str) -> List[Sentence]:
        """
        Split text into sentences with metadata

        Args:
            text: Input text to split into sentences

        Returns:
            List of Sentence objects with metadata
        """
        if self.use_spacy:
            return self._split_with_spacy(text)
        else:
            return self._split_with_nltk(text)

    def _split_with_spacy(self, text: str) -> List[Sentence]:
        """
        Use spaCy for sentence splitting (more accurate)

        Args:
            text: Input text to split

        Returns:
            List of Sentence objects
        """
        doc = self.nlp(text)
        sentences = []

        for sent in doc.sents:
            sentences.append(Sentence(
                text=sent.text.strip(),
                start_char=sent.start_char,
                end_char=sent.end_char,
                tokens=[token.text for token in sent],
                token_count=len(sent),
                is_heading=self._is_heading(sent.text),
                part_of_list=self._is_list_item(sent.text)
            ))

        return sentences

    def _split_with_nltk(self, text: str) -> List[Sentence]:
        """
        Fallback to NLTK sentence tokenizer

        Args:
            text: Input text to split

        Returns:
            List of Sentence objects
        """
        from nltk.tokenize import sent_tokenize, word_tokenize

        sentences = []
        offset = 0

        for sent_text in sent_tokenize(text):
            start_char = text.find(sent_text, offset)
            end_char = start_char + len(sent_text)
            tokens = word_tokenize(sent_text)

            sentences.append(Sentence(
                text=sent_text.strip(),
                start_char=start_char,
                end_char=end_char,
                tokens=tokens,
                token_count=len(tokens),
                is_heading=self._is_heading(sent_text),
                part_of_list=self._is_list_item(sent_text)
            ))

            offset = end_char

        return sentences

    @staticmethod
    def _is_heading(text: str) -> bool:
        """
        Detect if sentence is likely a heading

        Heuristics:
        - Short (< 100 chars)
        - Starts with uppercase
        - Doesn't end with sentence terminators
        - Has high ratio of uppercase letters (> 30%)

        Args:
            text: Text to analyze

        Returns:
            True if text appears to be a heading
        """
        if not text or len(text) == 0:
            return False

        return (
            len(text) < 100 and
            text[0].isupper() and
            not text.endswith(('.', '!', '?', ',')) and
            sum(1 for c in text if c.isupper()) / len(text) > 0.3
        )

    @staticmethod
    def _is_list_item(text: str) -> bool:
        """
        Detect if sentence is part of a list

        Checks for common list markers:
        - Bullets: -, •, *, ◦, ▪, ▫
        - Numbers: 1., 2), 3]
        - Dashes and other markers

        Args:
            text: Text to analyze

        Returns:
            True if text appears to be a list item
        """
        # Check for list markers: bullets, numbers, dashes
        # Pattern matches: bullet symbols OR number followed by ., ), or ]
        return bool(re.match(r'^\s*(?:[-•*◦▪▫]|\d+[\.)\]])\s+', text))
