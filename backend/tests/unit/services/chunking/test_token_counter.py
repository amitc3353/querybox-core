"""
Unit Tests for TokenCounter
Tests TokenCounter with BGE-M3 tokenizer for accurate token counting
"""
import pytest
from app.services.chunking.token_counter import TokenCounter


class TestTokenCounter:
    """Test TokenCounter class"""

    @pytest.fixture
    def counter(self):
        """Create TokenCounter instance with BGE-M3 tokenizer"""
        return TokenCounter()

    def test_initialization_default_model(self, counter):
        """Test TokenCounter initializes with default BGE-M3 model"""
        assert counter.tokenizer is not None
        assert hasattr(counter, 'tokenizer')
        # Verify it's using XLMRobertaTokenizer (BGE-M3's tokenizer)
        assert 'XLMRoberta' in type(counter.tokenizer).__name__

    def test_initialization_custom_model(self):
        """Test TokenCounter initializes with custom model"""
        # Use another XLMRoberta-based model
        counter = TokenCounter(model="BAAI/bge-m3")
        assert counter.tokenizer is not None

    def test_count_tokens_basic(self, counter):
        """Test basic token counting"""
        text = "This is a test sentence."
        token_count = counter.count_tokens(text)

        # Should return a positive integer
        assert isinstance(token_count, int)
        assert token_count > 0
        # Simple sentence should have reasonable token count
        assert 5 <= token_count <= 15

    def test_count_tokens_empty_string(self, counter):
        """Test token counting with empty string"""
        token_count = counter.count_tokens("")
        assert token_count == 0

    def test_count_tokens_single_word(self, counter):
        """Test token counting with single word"""
        token_count = counter.count_tokens("hello")
        assert token_count >= 1

    def test_count_tokens_whitespace_only(self, counter):
        """Test token counting with whitespace only"""
        token_count = counter.count_tokens("   ")
        # Whitespace should result in 0 or minimal tokens
        assert token_count >= 0

    def test_count_tokens_long_text(self, counter):
        """Test token counting with long text"""
        # Create text with ~100 words
        text = "This is a sentence. " * 20
        token_count = counter.count_tokens(text)

        # Should have reasonable token count (roughly 1 token per word)
        assert 80 <= token_count <= 150

    def test_count_tokens_technical_text(self, counter):
        """Test token counting with technical/domain-specific text"""
        text = "QueryboxCore uses BGE-M3 embeddings with semantic chunking for RAG."
        token_count = counter.count_tokens(text)

        # Technical terms may tokenize differently
        assert token_count > 0
        assert isinstance(token_count, int)

    def test_count_tokens_special_characters(self, counter):
        """Test token counting with special characters"""
        text = "Hello! How are you? I'm doing well. #Python @AI 50% done."
        token_count = counter.count_tokens(text)

        assert token_count > 0

    def test_count_tokens_numbers(self, counter):
        """Test token counting with numbers"""
        text = "The year 2024 has 365 days and 12 months."
        token_count = counter.count_tokens(text)

        assert token_count > 0

    def test_count_tokens_unicode(self, counter):
        """Test token counting with unicode characters"""
        text = "Hello 世界! Bonjour le monde! Hola mundo!"
        token_count = counter.count_tokens(text)

        assert token_count > 0

    def test_truncate_to_tokens_no_truncation_needed(self, counter):
        """Test truncation when text is already under limit"""
        text = "Short text."
        max_tokens = 100

        truncated = counter.truncate_to_tokens(text, max_tokens)

        # Should return original text unchanged
        assert truncated == text

    def test_truncate_to_tokens_basic(self, counter):
        """Test basic text truncation"""
        text = "This is a longer sentence that will be truncated to a specific token count."
        max_tokens = 10

        truncated = counter.truncate_to_tokens(text, max_tokens)

        # Truncated text should be shorter
        assert len(truncated) < len(text)
        # Truncated text should have <= max_tokens
        assert counter.count_tokens(truncated) <= max_tokens

    def test_truncate_to_tokens_exact_limit(self, counter):
        """Test truncation produces exactly max_tokens or less"""
        text = "Natural language processing is a subfield of linguistics, computer science, and artificial intelligence."
        max_tokens = 15

        truncated = counter.truncate_to_tokens(text, max_tokens)
        actual_tokens = counter.count_tokens(truncated)

        assert actual_tokens <= max_tokens

    def test_truncate_to_tokens_very_long_text(self, counter):
        """Test truncation with very long text"""
        # Create very long text (1000 words)
        text = "This is a test sentence. " * 200
        max_tokens = 50

        truncated = counter.truncate_to_tokens(text, max_tokens)
        actual_tokens = counter.count_tokens(truncated)

        assert actual_tokens <= max_tokens
        assert len(truncated) < len(text)

    def test_truncate_to_tokens_zero_limit(self, counter):
        """Test truncation with zero token limit"""
        text = "This should be completely truncated."
        max_tokens = 0

        truncated = counter.truncate_to_tokens(text, max_tokens)

        # Should return empty or minimal text
        assert len(truncated) <= len(text)
        assert counter.count_tokens(truncated) == 0

    def test_truncate_to_tokens_single_token(self, counter):
        """Test truncation to single token"""
        text = "This is a longer sentence with multiple tokens."
        max_tokens = 1

        truncated = counter.truncate_to_tokens(text, max_tokens)
        actual_tokens = counter.count_tokens(truncated)

        assert actual_tokens <= 1

    def test_truncate_to_tokens_preserves_meaning(self, counter):
        """Test truncation preserves start of text"""
        text = "QueryboxCore is a RAG system that uses semantic search for document retrieval."
        max_tokens = 5

        truncated = counter.truncate_to_tokens(text, max_tokens)

        # Truncated text should start with the original text
        assert text.startswith(truncated.split()[0])

    def test_truncate_to_tokens_empty_string(self, counter):
        """Test truncation with empty string"""
        truncated = counter.truncate_to_tokens("", 10)
        assert truncated == ""

    def test_consistency_count_and_truncate(self, counter):
        """Test that count_tokens and truncate_to_tokens are consistent"""
        text = "This is a test to verify consistency between counting and truncation."
        max_tokens = 10

        truncated = counter.truncate_to_tokens(text, max_tokens)
        actual_tokens = counter.count_tokens(truncated)

        # Count of truncated text should be <= max_tokens
        assert actual_tokens <= max_tokens

    def test_multiple_calls_same_result(self, counter):
        """Test multiple calls with same input return same result"""
        text = "Consistency test for multiple calls."

        count1 = counter.count_tokens(text)
        count2 = counter.count_tokens(text)

        assert count1 == count2

    def test_truncate_to_tokens_multiple_calls(self, counter):
        """Test multiple truncation calls return same result"""
        text = "Another consistency test for truncation."
        max_tokens = 5

        truncated1 = counter.truncate_to_tokens(text, max_tokens)
        truncated2 = counter.truncate_to_tokens(text, max_tokens)

        assert truncated1 == truncated2


class TestTokenCounterEdgeCases:
    """Test TokenCounter edge cases and error handling"""

    @pytest.fixture
    def counter(self):
        """Create TokenCounter instance"""
        return TokenCounter()

    def test_very_long_single_word(self, counter):
        """Test with very long single word"""
        text = "a" * 1000
        token_count = counter.count_tokens(text)

        # Should handle long words
        assert token_count > 0

    def test_repeated_characters(self, counter):
        """Test with repeated characters"""
        text = "!!!!!!!!!!!!!!!"
        token_count = counter.count_tokens(text)

        assert token_count >= 0

    def test_newlines_and_tabs(self, counter):
        """Test with newlines and tabs"""
        text = "Line 1\nLine 2\tTabbed text\n\nDouble newline"
        token_count = counter.count_tokens(text)

        assert token_count > 0

    def test_mixed_languages(self, counter):
        """Test with mixed language text"""
        text = "English, 中文, Español, Français, العربية"
        token_count = counter.count_tokens(text)

        assert token_count > 0

    def test_code_snippet(self, counter):
        """Test with code snippet"""
        text = "def hello_world():\n    print('Hello, World!')"
        token_count = counter.count_tokens(text)

        assert token_count > 0

    def test_markdown_text(self, counter):
        """Test with markdown formatted text"""
        text = "# Heading\n\n**Bold text** and *italic text*\n\n- List item 1\n- List item 2"
        token_count = counter.count_tokens(text)

        assert token_count > 0

    def test_truncate_large_max_tokens(self, counter):
        """Test truncation with very large max_tokens"""
        text = "Short text."
        max_tokens = 1000000

        truncated = counter.truncate_to_tokens(text, max_tokens)

        # Should return original text
        assert truncated == text


class TestTokenCounterAccuracy:
    """Test TokenCounter accuracy with BGE-M3 tokenizer"""

    @pytest.fixture
    def counter(self):
        """Create TokenCounter instance"""
        return TokenCounter()

    def test_tokenizer_matches_bge_m3(self, counter):
        """Test that tokenizer is actually BGE-M3's tokenizer"""
        # Verify using XLMRobertaTokenizer (BGE-M3's base)
        assert 'XLMRoberta' in type(counter.tokenizer).__name__

    def test_no_special_tokens_in_count(self, counter):
        """Test that special tokens ([CLS], [SEP]) are not included in count"""
        text = "Simple test."

        # Our count_tokens should NOT include special tokens
        our_count = counter.count_tokens(text)

        # Direct tokenizer call WITH special tokens
        with_special = len(counter.tokenizer.encode(text, add_special_tokens=True))

        # Our count should be less (no special tokens)
        assert our_count < with_special

    def test_count_tokens_deterministic(self, counter):
        """Test that token counting is deterministic"""
        text = "Deterministic test for consistent results."

        counts = [counter.count_tokens(text) for _ in range(5)]

        # All counts should be identical
        assert len(set(counts)) == 1

    def test_truncate_tokens_deterministic(self, counter):
        """Test that truncation is deterministic"""
        text = "Deterministic test for consistent truncation results."
        max_tokens = 7

        results = [counter.truncate_to_tokens(text, max_tokens) for _ in range(5)]

        # All results should be identical
        assert len(set(results)) == 1
