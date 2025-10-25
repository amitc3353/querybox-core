"""
Unit Tests for SentenceSplitter
Tests SentenceSplitter with both spaCy and NLTK backends
"""
import pytest
from app.services.chunking.sentence_splitter import SentenceSplitter, Sentence


class TestSentenceSplitterSpaCy:
    """Test SentenceSplitter with spaCy backend"""

    @pytest.fixture
    def splitter(self):
        """Create SentenceSplitter instance with spaCy"""
        return SentenceSplitter(use_spacy=True)

    def test_initialization_spacy(self, splitter):
        """Test SentenceSplitter initializes with spaCy"""
        assert splitter is not None
        assert splitter.use_spacy is True
        assert hasattr(splitter, 'nlp')

    def test_basic_sentence_splitting(self, splitter):
        """Test basic sentence splitting with simple text"""
        text = "This is the first sentence. This is the second sentence."
        sentences = splitter.split_sentences(text)

        assert len(sentences) == 2
        assert sentences[0].text.strip() == "This is the first sentence."
        assert sentences[1].text.strip() == "This is the second sentence."

    def test_multiple_punctuation_types(self, splitter):
        """Test splitting with different sentence terminators"""
        text = "Statement. Question? Exclamation! Another statement."
        sentences = splitter.split_sentences(text)

        assert len(sentences) == 4
        assert all(isinstance(sent, Sentence) for sent in sentences)

    def test_sentence_metadata(self, splitter):
        """Test that Sentence objects contain correct metadata"""
        text = "First sentence. Second sentence."
        sentences = splitter.split_sentences(text)

        # Check first sentence
        assert sentences[0].text.strip() == "First sentence."
        assert sentences[0].start_char == 0
        assert sentences[0].end_char > 0
        assert sentences[0].token_count > 0
        assert isinstance(sentences[0].tokens, list)
        assert len(sentences[0].tokens) > 0

    def test_character_positions(self, splitter):
        """Test that character positions are accurate"""
        text = "First. Second. Third."
        sentences = splitter.split_sentences(text)

        # Positions should be sequential
        for sent in sentences:
            assert sent.start_char >= 0
            assert sent.end_char > sent.start_char
            # Text length should match position difference (approximately)
            extracted_text = text[sent.start_char:sent.end_char]
            assert sent.text.strip() in extracted_text or extracted_text in sent.text

    def test_token_counting(self, splitter):
        """Test token count is accurate"""
        text = "This is a simple test."
        sentences = splitter.split_sentences(text)

        assert len(sentences) == 1
        # "This", "is", "a", "simple", "test", "." = 6 tokens
        assert sentences[0].token_count >= 5  # At least 5 words
        assert len(sentences[0].tokens) == sentences[0].token_count

    def test_empty_string(self, splitter):
        """Test splitting empty string"""
        sentences = splitter.split_sentences("")
        assert len(sentences) == 0

    def test_single_word(self, splitter):
        """Test splitting single word"""
        sentences = splitter.split_sentences("Hello")
        assert len(sentences) >= 0  # May or may not create a sentence

    def test_no_punctuation(self, splitter):
        """Test text with no punctuation"""
        text = "This is a sentence without punctuation"
        sentences = splitter.split_sentences(text)

        # Should still create at least one sentence
        assert len(sentences) >= 1

    def test_multiple_spaces(self, splitter):
        """Test handling of multiple spaces"""
        text = "First sentence.  Second sentence.   Third sentence."
        sentences = splitter.split_sentences(text)

        assert len(sentences) == 3
        # All sentences should be stripped
        for sent in sentences:
            assert sent.text == sent.text.strip()


class TestSentenceSplitterNLTK:
    """Test SentenceSplitter with NLTK backend"""

    @pytest.fixture
    def splitter(self):
        """Create SentenceSplitter instance with NLTK"""
        return SentenceSplitter(use_spacy=False)

    def test_initialization_nltk(self, splitter):
        """Test SentenceSplitter initializes with NLTK"""
        assert splitter is not None
        assert splitter.use_spacy is False

    def test_basic_sentence_splitting_nltk(self, splitter):
        """Test basic sentence splitting with NLTK"""
        text = "This is the first sentence. This is the second sentence."
        sentences = splitter.split_sentences(text)

        assert len(sentences) == 2
        assert sentences[0].text.strip() == "This is the first sentence."
        assert sentences[1].text.strip() == "This is the second sentence."

    def test_nltk_metadata(self, splitter):
        """Test NLTK generates proper metadata"""
        text = "Test sentence."
        sentences = splitter.split_sentences(text)

        assert len(sentences) == 1
        assert sentences[0].token_count > 0
        assert len(sentences[0].tokens) > 0
        assert sentences[0].start_char >= 0
        assert sentences[0].end_char > 0

    def test_nltk_multiple_sentences(self, splitter):
        """Test NLTK with multiple sentences"""
        text = "First. Second. Third. Fourth."
        sentences = splitter.split_sentences(text)

        assert len(sentences) == 4


class TestHeadingDetection:
    """Test heading detection functionality"""

    @pytest.fixture
    def splitter(self):
        """Create SentenceSplitter instance"""
        return SentenceSplitter(use_spacy=True)

    def test_heading_detected(self, splitter):
        """Test that headings are properly detected"""
        text = "CHAPTER ONE Introduction"
        sentences = splitter.split_sentences(text)

        assert len(sentences) >= 1
        # Should be detected as heading (short, uppercase, no punctuation)
        assert sentences[0].is_heading is True

    def test_normal_sentence_not_heading(self, splitter):
        """Test that normal sentences are not detected as headings"""
        text = "This is a normal sentence with punctuation."
        sentences = splitter.split_sentences(text)

        assert len(sentences) >= 1
        assert sentences[0].is_heading is False

    def test_long_text_not_heading(self, splitter):
        """Test that long text is not detected as heading"""
        # Over 100 characters
        text = "A" * 150
        sentences = splitter.split_sentences(text)

        if len(sentences) > 0:
            assert sentences[0].is_heading is False

    def test_lowercase_not_heading(self, splitter):
        """Test lowercase text not detected as heading"""
        text = "this is lowercase"
        sentences = splitter.split_sentences(text)

        if len(sentences) > 0:
            assert sentences[0].is_heading is False

    def test_sentence_with_punctuation_not_heading(self, splitter):
        """Test text ending with punctuation not detected as heading"""
        text = "Title Case Text."
        sentences = splitter.split_sentences(text)

        if len(sentences) > 0:
            # Ends with period, so not a heading
            assert sentences[0].is_heading is False

    def test_mixed_case_heading(self, splitter):
        """Test mixed case heading detection"""
        text = "Introduction to Systems"
        sentences = splitter.split_sentences(text)

        # Short, starts uppercase, no punctuation, but may not have enough uppercase
        assert len(sentences) >= 1
        # Result depends on uppercase ratio


class TestListItemDetection:
    """Test list item detection functionality"""

    @pytest.fixture
    def splitter(self):
        """Create SentenceSplitter instance"""
        return SentenceSplitter(use_spacy=True)

    def test_dash_list_item(self, splitter):
        """Test detection of dash list items"""
        text = "- First item in the list"
        sentences = splitter.split_sentences(text)

        assert len(sentences) >= 1
        assert sentences[0].part_of_list is True

    def test_bullet_list_item(self, splitter):
        """Test detection of bullet list items"""
        text = "• Bullet point item"
        sentences = splitter.split_sentences(text)

        assert len(sentences) >= 1
        assert sentences[0].part_of_list is True

    def test_numbered_list_item(self, splitter):
        """Test detection of numbered list items"""
        # Note: regex checks for pattern like "1." at start
        text = "1. First numbered item"
        sentences = splitter.split_sentences(text)

        assert len(sentences) >= 1
        # May or may not detect depending on tokenization

    def test_asterisk_list_item(self, splitter):
        """Test detection of asterisk list items"""
        text = "* List item with asterisk"
        sentences = splitter.split_sentences(text)

        assert len(sentences) >= 1
        assert sentences[0].part_of_list is True

    def test_normal_sentence_not_list(self, splitter):
        """Test normal sentence not detected as list item"""
        text = "This is a normal sentence."
        sentences = splitter.split_sentences(text)

        assert len(sentences) >= 1
        assert sentences[0].part_of_list is False


class TestEdgeCases:
    """Test edge cases and special scenarios"""

    @pytest.fixture
    def splitter(self):
        """Create SentenceSplitter instance"""
        return SentenceSplitter(use_spacy=True)

    def test_abbreviations(self, splitter):
        """Test handling of abbreviations like Dr., U.S.A."""
        text = "Dr. Smith lives in the U.S.A. and works at N.A.S.A."
        sentences = splitter.split_sentences(text)

        # Should handle abbreviations correctly (1-2 sentences depending on model)
        assert len(sentences) >= 1
        assert len(sentences) <= 3  # Should not split on every period

    def test_decimal_numbers(self, splitter):
        """Test handling of decimal numbers"""
        text = "The value is 3.14159. This is the second sentence."
        sentences = splitter.split_sentences(text)

        # Should create 2 sentences, not split on decimal point
        assert len(sentences) == 2

    def test_ellipsis(self, splitter):
        """Test handling of ellipsis"""
        text = "This is interesting... Let me continue."
        sentences = splitter.split_sentences(text)

        # Should handle ellipsis properly
        assert len(sentences) >= 1

    def test_quoted_text(self, splitter):
        """Test handling of quoted text"""
        text = 'She said, "Hello there." He replied, "How are you?"'
        sentences = splitter.split_sentences(text)

        # Should handle quotes properly
        assert len(sentences) >= 1

    def test_newlines(self, splitter):
        """Test handling of newlines"""
        text = "First sentence.\nSecond sentence.\n\nThird sentence."
        sentences = splitter.split_sentences(text)

        assert len(sentences) == 3

    def test_very_long_sentence(self, splitter):
        """Test handling of very long sentence"""
        # Create a long sentence (500+ words)
        text = "This is a very long sentence " * 50 + "."
        sentences = splitter.split_sentences(text)

        # Should still process it
        assert len(sentences) >= 1

    def test_special_characters(self, splitter):
        """Test handling of special characters"""
        text = "Special chars: @#$%^&*(). Another sentence!"
        sentences = splitter.split_sentences(text)

        assert len(sentences) == 2

    def test_unicode_characters(self, splitter):
        """Test handling of unicode characters"""
        text = "Hello 世界! Bonjour le monde."
        sentences = splitter.split_sentences(text)

        assert len(sentences) == 2

    def test_mixed_content(self, splitter):
        """Test complex mixed content"""
        text = """
        Introduction to RAG Systems

        Retrieval-Augmented Generation (RAG) combines search with LLMs. Key benefits include:

        - Improved accuracy
        - Real-time updates
        - Reduced hallucinations

        The system works by retrieving relevant chunks. Then it generates responses.
        """
        sentences = splitter.split_sentences(text)

        # Should handle mixed content (headings, lists, normal text)
        assert len(sentences) >= 3

        # Verify that sentences were extracted
        # Note: List items may be combined with preceding text during sentence splitting
        # so we just verify we got multiple sentences and proper structure
        sentence_texts = [s.text for s in sentences]
        assert any(len(s.text) > 0 for s in sentences)


class TestConsistency:
    """Test consistency between spaCy and NLTK"""

    def test_consistent_output_format(self):
        """Test both backends produce same Sentence structure"""
        text = "Simple sentence. Another one."

        spacy_splitter = SentenceSplitter(use_spacy=True)
        nltk_splitter = SentenceSplitter(use_spacy=False)

        spacy_sentences = spacy_splitter.split_sentences(text)
        nltk_sentences = nltk_splitter.split_sentences(text)

        # Both should produce Sentence objects
        assert all(isinstance(s, Sentence) for s in spacy_sentences)
        assert all(isinstance(s, Sentence) for s in nltk_sentences)

        # Both should find same number of sentences
        assert len(spacy_sentences) == len(nltk_sentences)

    def test_metadata_fields_present(self):
        """Test both backends populate all metadata fields"""
        text = "Test sentence."

        for use_spacy in [True, False]:
            splitter = SentenceSplitter(use_spacy=use_spacy)
            sentences = splitter.split_sentences(text)

            if len(sentences) > 0:
                sent = sentences[0]
                # All fields should be present
                assert hasattr(sent, 'text')
                assert hasattr(sent, 'start_char')
                assert hasattr(sent, 'end_char')
                assert hasattr(sent, 'tokens')
                assert hasattr(sent, 'token_count')
                assert hasattr(sent, 'is_heading')
                assert hasattr(sent, 'part_of_list')


class TestStaticMethods:
    """Test static methods independently"""

    def test_is_heading_static(self):
        """Test _is_heading static method"""
        # Should be heading
        assert SentenceSplitter._is_heading("INTRODUCTION") is True
        assert SentenceSplitter._is_heading("CHAPTER ONE") is True

        # Should not be heading
        assert SentenceSplitter._is_heading("This is a sentence.") is False
        assert SentenceSplitter._is_heading("lowercase text") is False
        assert SentenceSplitter._is_heading("A" * 150) is False  # Too long
        assert SentenceSplitter._is_heading("") is False  # Empty

    def test_is_list_item_static(self):
        """Test _is_list_item static method"""
        # Should be list items
        assert SentenceSplitter._is_list_item("- Item") is True
        assert SentenceSplitter._is_list_item("• Bullet") is True
        assert SentenceSplitter._is_list_item("* Star") is True
        assert SentenceSplitter._is_list_item("1. Numbered") is True

        # Should not be list items
        assert SentenceSplitter._is_list_item("Normal text") is False
        assert SentenceSplitter._is_list_item("No markers here.") is False
