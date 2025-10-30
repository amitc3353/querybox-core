"""
Text Matching Utilities for Step 11.2 - Chain-of-Verification

Provides text normalization, sentence extraction, and similarity utilities
for quote matching and verification.
"""
import re
from typing import List
import nltk

# Ensure nltk punkt tokenizer is available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)


def normalize_text(text: str) -> str:
    """
    Normalize text for fuzzy matching.

    Normalization steps:
    1. Convert to lowercase
    2. Remove extra whitespace
    3. Strip leading/trailing whitespace
    4. Remove special characters that don't affect meaning

    Args:
        text: Raw text to normalize

    Returns:
        Normalized text string

    Example:
        >>> normalize_text("  Hello   World!  ")
        'hello world!'
    """
    if not text:
        return ""

    # Convert to lowercase
    normalized = text.lower()

    # Remove control characters
    normalized = ''.join(char for char in normalized if ord(char) >= 32 or char == '\n')

    # Normalize whitespace (replace multiple spaces/newlines with single space)
    normalized = re.sub(r'\s+', ' ', normalized)

    # Strip leading/trailing whitespace
    normalized = normalized.strip()

    return normalized


def extract_sentences(text: str, min_words: int = 3) -> List[str]:
    """
    Extract sentences from text using NLTK sentence tokenizer.

    Preserves sentence boundaries accurately using punkt tokenizer.
    Filters out very short sentences that are likely not complete claims.

    Args:
        text: Text to extract sentences from
        min_words: Minimum words per sentence (default: 3)

    Returns:
        List of sentence strings

    Example:
        >>> extract_sentences("Paris is the capital. It's beautiful.")
        ['Paris is the capital.', "It's beautiful."]
    """
    if not text or not text.strip():
        return []

    try:
        # Use NLTK's punkt sentence tokenizer
        sentences = nltk.sent_tokenize(text)

        # Filter out very short sentences
        filtered_sentences = []
        for sentence in sentences:
            # Count words (split on whitespace)
            word_count = len(sentence.split())
            if word_count >= min_words:
                filtered_sentences.append(sentence.strip())

        return filtered_sentences

    except Exception as e:
        # Fallback to simple sentence splitting if NLTK fails
        # Split on period, question mark, exclamation mark
        sentences = re.split(r'[.!?]+', text)
        filtered = [s.strip() for s in sentences if s.strip() and len(s.split()) >= min_words]
        return filtered


def extract_n_grams(text: str, n: int = 3) -> List[str]:
    """
    Extract word n-grams from text.

    Used for more granular text matching.

    Args:
        text: Text to extract n-grams from
        n: N-gram size (default: 3 for trigrams)

    Returns:
        List of n-gram strings

    Example:
        >>> extract_n_grams("The quick brown fox", n=2)
        ['The quick', 'quick brown', 'brown fox']
    """
    if not text or n < 1:
        return []

    # Tokenize into words
    words = text.split()

    if len(words) < n:
        return [text]  # Return whole text if shorter than n

    # Generate n-grams
    n_grams = []
    for i in range(len(words) - n + 1):
        n_gram = ' '.join(words[i:i + n])
        n_grams.append(n_gram)

    return n_grams


def contains_control_characters(text: str) -> bool:
    """
    Check if text contains control characters.

    Used for security validation in quote matching.

    Args:
        text: Text to check

    Returns:
        True if control characters found, False otherwise

    Example:
        >>> contains_control_characters("Hello\\x00World")
        True
        >>> contains_control_characters("Hello World")
        False
    """
    if not text:
        return False

    # Check for control characters (ASCII 0-31, excluding common ones like \\n, \\t)
    for char in text:
        code = ord(char)
        # Allow newline (10), tab (9), carriage return (13)
        if code < 32 and code not in (9, 10, 13):
            return True

    return False


def truncate_at_sentence_boundary(text: str, max_length: int) -> str:
    """
    Truncate text at sentence boundary without breaking sentences.

    Used when fitting passages to context window.

    Args:
        text: Text to truncate
        max_length: Maximum character length

    Returns:
        Truncated text ending at sentence boundary

    Example:
        >>> truncate_at_sentence_boundary("First. Second. Third.", 15)
        'First. Second.'
    """
    if not text or len(text) <= max_length:
        return text

    # Extract sentences
    sentences = extract_sentences(text)

    if not sentences:
        # Fallback: truncate at max_length
        return text[:max_length]

    # Build truncated text sentence by sentence
    truncated = ""
    for sentence in sentences:
        if len(truncated) + len(sentence) + 1 <= max_length:  # +1 for space
            if truncated:
                truncated += " " + sentence
            else:
                truncated = sentence
        else:
            break

    # If no sentences fit, return truncated first sentence
    if not truncated:
        truncated = text[:max_length]

    return truncated


def calculate_word_overlap(text1: str, text2: str) -> float:
    """
    Calculate word overlap ratio between two texts.

    Simple similarity metric based on shared words.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Overlap ratio (0.0 to 1.0)

    Example:
        >>> calculate_word_overlap("the quick brown fox", "the fast brown dog")
        0.5  # 2 words overlap (the, brown) out of 4 unique words
    """
    if not text1 or not text2:
        return 0.0

    # Normalize and tokenize
    words1 = set(normalize_text(text1).split())
    words2 = set(normalize_text(text2).split())

    if not words1 or not words2:
        return 0.0

    # Calculate Jaccard similarity
    intersection = len(words1 & words2)
    union = len(words1 | words2)

    if union == 0:
        return 0.0

    return intersection / union


def remove_citations(text: str) -> str:
    """
    Remove citation markers from text.

    Removes patterns like [1], [2], [1][2], etc.

    Args:
        text: Text with citation markers

    Returns:
        Text with citations removed

    Example:
        >>> remove_citations("Paris is capital [1]. It's beautiful [2][3].")
        "Paris is capital . It's beautiful ."
    """
    if not text:
        return ""

    # Remove citation patterns like [1], [2], [1][2]
    text_without_citations = re.sub(r'\[\d+\]', '', text)

    # Clean up extra spaces
    text_without_citations = re.sub(r'\s+', ' ', text_without_citations)

    return text_without_citations.strip()


def split_into_propositions(text: str, min_words: int = 5, max_words: int = 40) -> List[str]:
    """
    Split text into atomic propositions (claims).

    Used to break complex sentences into simpler claims for verification.

    Args:
        text: Text to split into propositions
        min_words: Minimum words per proposition
        max_words: Maximum words per proposition (split longer ones)

    Returns:
        List of proposition strings

    Example:
        >>> split_into_propositions("Paris is capital and it's beautiful.")
        ['Paris is capital', "it's beautiful"]
    """
    if not text:
        return []

    # Remove citations first
    text = remove_citations(text)

    # Extract sentences
    sentences = extract_sentences(text, min_words=min_words)

    propositions = []

    for sentence in sentences:
        word_count = len(sentence.split())

        # If sentence is short enough, keep as-is
        if word_count <= max_words:
            propositions.append(sentence)
            continue

        # If too long, try to split on conjunctions
        # Split on: and, but, however, although, while
        parts = re.split(r'\s+(?:and|but|however|although|while)\s+', sentence, flags=re.IGNORECASE)

        for part in parts:
            part = part.strip()
            if part and len(part.split()) >= min_words:
                # Still too long? Just truncate
                if len(part.split()) > max_words:
                    words = part.split()
                    part = ' '.join(words[:max_words])
                propositions.append(part)

    return propositions
