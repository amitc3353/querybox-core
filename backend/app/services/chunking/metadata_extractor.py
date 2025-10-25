# app/services/chunking/metadata_extractor.py

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Heading:
    """Represents a document heading with hierarchy"""
    text: str
    level: int  # 1-6 for H1-H6
    start_char: int
    end_char: int
    child_ids: List[int] = field(default_factory=list)  # IDs of child headings


@dataclass
class Paragraph:
    """Represents a paragraph of text"""
    text: str
    start_char: int
    end_char: int
    parent_heading_id: Optional[int] = None  # ID of parent heading


@dataclass
class Table:
    """Represents a table with structure"""
    headers: List[str]
    rows: List[List[str]]
    caption: Optional[str]
    start_char: int
    end_char: int


@dataclass
class ListElement:
    """Represents a list (ordered or unordered)"""
    items: List[str]
    list_type: str  # "ordered" or "unordered"
    start_char: int
    end_char: int


@dataclass
class Figure:
    """Represents a figure or image reference"""
    caption: Optional[str]
    alt_text: Optional[str]
    figure_number: Optional[int]
    start_char: int
    end_char: int


@dataclass
class CodeBlock:
    """Represents a code block"""
    language: Optional[str]
    content: str
    start_char: int
    end_char: int


@dataclass
class Equation:
    """Represents a mathematical equation"""
    latex: Optional[str]
    plain_text: str
    start_char: int
    end_char: int


@dataclass
class Citation:
    """Represents a citation or reference"""
    text: str
    authors: Optional[List[str]]
    year: Optional[int]
    source: Optional[str]
    start_char: int
    end_char: int


@dataclass
class Footnote:
    """Represents a footnote"""
    number: int
    content: str
    reference_char: int  # Character position of the reference marker


@dataclass
class Definition:
    """Represents a term definition"""
    term: str
    definition: str
    context_paragraph_id: Optional[int] = None


@dataclass
class DocumentStructure:
    """Represents the complete document structure with all elements"""
    headings: List[Heading] = field(default_factory=list)
    paragraphs: List[Paragraph] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)
    lists: List[ListElement] = field(default_factory=list)
    figures: List[Figure] = field(default_factory=list)
    code_blocks: List[CodeBlock] = field(default_factory=list)
    equations: List[Equation] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    footnotes: List[Footnote] = field(default_factory=list)
    definitions: List[Definition] = field(default_factory=list)


class MetadataExtractor:
    """Extract comprehensive structural metadata from document text

    Supports extraction of:
    - Headings (Markdown, underlined, ALL CAPS)
    - Paragraphs (double newline separated)
    - Tables (Markdown and grid patterns)
    - Lists (ordered and unordered)
    - Code blocks (fenced and indented)
    - Figures (Markdown image syntax)
    - Equations (LaTeX and inline math)
    - Citations (various formats)
    - Footnotes
    - Definitions (term: definition patterns)
    """

    def extract_structure(self, text: str) -> DocumentStructure:
        """
        Extract complete document structure from text

        Args:
            text: Input document text

        Returns:
            DocumentStructure with all extracted elements
        """
        logger.info("Extracting document structure...")

        structure = DocumentStructure()

        # Extract all structural elements
        structure.headings = self._extract_headings(text)
        structure.paragraphs = self._extract_paragraphs(text, structure.headings)
        structure.tables = self._extract_tables(text)
        structure.lists = self._extract_lists(text)
        structure.code_blocks = self._extract_code_blocks(text)
        structure.figures = self._extract_figures(text)
        structure.equations = self._extract_equations(text)
        structure.citations = self._extract_citations(text)
        structure.footnotes = self._extract_footnotes(text)
        structure.definitions = self._extract_definitions(text, structure.paragraphs)

        # Build heading hierarchy
        self._build_heading_hierarchy(structure.headings)

        logger.info(
            f"Extracted structure: {len(structure.headings)} headings, "
            f"{len(structure.paragraphs)} paragraphs, {len(structure.tables)} tables, "
            f"{len(structure.lists)} lists, {len(structure.code_blocks)} code blocks"
        )

        return structure

    def _extract_headings(self, text: str) -> List[Heading]:
        """
        Extract headings using multiple heuristics:
        1. Markdown-style (# Heading)
        2. Underlined (Heading\\n====)
        3. ALL CAPS short lines
        """
        headings = []
        heading_id = 0

        # 1. Markdown-style headings (# Heading, ## Heading, etc.)
        for match in re.finditer(r'^(#{1,6})\s+(.+)$', text, re.MULTILINE):
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            headings.append(Heading(
                text=heading_text,
                level=level,
                start_char=match.start(),
                end_char=match.end()
            ))
            heading_id += 1

        # 2. Underlined headings (Setext-style)
        # Level 1: Heading\n======
        for match in re.finditer(r'^(.+)\n(=+)$', text, re.MULTILINE):
            heading_text = match.group(1).strip()
            if len(heading_text) < 100:  # Reasonable heading length
                headings.append(Heading(
                    text=heading_text,
                    level=1,
                    start_char=match.start(),
                    end_char=match.end()
                ))
                heading_id += 1

        # Level 2: Heading\n------
        for match in re.finditer(r'^(.+)\n(-{3,})$', text, re.MULTILINE):
            heading_text = match.group(1).strip()
            if len(heading_text) < 100:
                headings.append(Heading(
                    text=heading_text,
                    level=2,
                    start_char=match.start(),
                    end_char=match.end()
                ))
                heading_id += 1

        # 3. ALL CAPS headings (heuristic)
        for match in re.finditer(r'^([A-Z][A-Z\s]{5,80})$', text, re.MULTILINE):
            heading_text = match.group(1).strip()
            # Check if it's actually all caps (>90% uppercase)
            if sum(1 for c in heading_text if c.isupper()) / len(heading_text.replace(' ', '')) > 0.9:
                headings.append(Heading(
                    text=heading_text,
                    level=2,  # Assume level 2 for ALL CAPS
                    start_char=match.start(),
                    end_char=match.end()
                ))
                heading_id += 1

        # Sort by position in document
        headings.sort(key=lambda h: h.start_char)

        return headings

    def _extract_paragraphs(self, text: str, headings: List[Heading]) -> List[Paragraph]:
        """
        Extract paragraphs (double newline separated)

        Args:
            text: Input text
            headings: List of extracted headings to assign parent relationships

        Returns:
            List of Paragraph objects
        """
        paragraphs = []

        # Split on double newlines (paragraph separator)
        blocks = re.split(r'\n\s*\n', text)
        offset = 0

        for block in blocks:
            block_stripped = block.strip()
            if not block_stripped or len(block_stripped) < 10:
                offset += len(block) + 2  # Account for newlines
                continue

            # Find position in original text
            start_char = text.find(block_stripped, offset)
            if start_char == -1:
                offset += len(block) + 2
                continue

            end_char = start_char + len(block_stripped)

            # Find parent heading (most recent heading before this paragraph)
            parent_heading_id = None
            for i, heading in enumerate(headings):
                if heading.start_char < start_char:
                    parent_heading_id = i
                else:
                    break

            paragraphs.append(Paragraph(
                text=block_stripped,
                start_char=start_char,
                end_char=end_char,
                parent_heading_id=parent_heading_id
            ))

            offset = end_char

        return paragraphs

    def _extract_tables(self, text: str) -> List[Table]:
        """
        Detect table patterns (Markdown tables and grid patterns)

        Supports:
        - Markdown tables: | Header | Header |
        - Grid tables: +-----+-----+
        """
        tables = []

        # Markdown table pattern: | col1 | col2 |
        # Looks for table with header separator: |---|---|
        table_pattern = re.compile(
            r'(\|.+\|\n\|[-:| ]+\|\n(?:\|.+\|\n?)+)',
            re.MULTILINE
        )

        for match in table_pattern.finditer(text):
            table_text = match.group(1)
            lines = [line.strip() for line in table_text.split('\n') if line.strip()]

            if len(lines) < 2:
                continue

            # Parse header
            header_line = lines[0]
            headers = [cell.strip() for cell in header_line.split('|')[1:-1]]

            # Parse rows (skip separator line at index 1)
            rows = []
            for line in lines[2:]:
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if len(cells) == len(headers):
                    rows.append(cells)

            # Look for caption (line before or after table)
            caption = None
            caption_pattern = r'(?:Table \d+:|Caption:)\s*(.+)'
            before_text = text[max(0, match.start()-100):match.start()]
            after_text = text[match.end():min(len(text), match.end()+100)]

            caption_match = re.search(caption_pattern, before_text + after_text, re.IGNORECASE)
            if caption_match:
                caption = caption_match.group(1).strip()

            tables.append(Table(
                headers=headers,
                rows=rows,
                caption=caption,
                start_char=match.start(),
                end_char=match.end()
            ))

        return tables

    def _extract_lists(self, text: str) -> List[ListElement]:
        """
        Detect list blocks (ordered and unordered)

        Supports:
        - Unordered: -, *, •, +
        - Ordered: 1., 2), 3]
        """
        lists = []

        # Unordered list pattern: lines starting with -, *, •, +
        unordered_pattern = re.compile(
            r'((?:^[\s]*[-*•+]\s+.+\n?)+)',
            re.MULTILINE
        )

        for match in unordered_pattern.finditer(text):
            list_text = match.group(1)
            items = []

            for line in list_text.split('\n'):
                line = line.strip()
                if line:
                    # Remove list marker
                    item_text = re.sub(r'^[-*•+]\s+', '', line)
                    items.append(item_text)

            if items:
                lists.append(ListElement(
                    items=items,
                    list_type="unordered",
                    start_char=match.start(),
                    end_char=match.end()
                ))

        # Ordered list pattern: lines starting with 1., 2), etc.
        ordered_pattern = re.compile(
            r'((?:^[\s]*\d+[.)\]]\s+.+\n?)+)',
            re.MULTILINE
        )

        for match in ordered_pattern.finditer(text):
            list_text = match.group(1)
            items = []

            for line in list_text.split('\n'):
                line = line.strip()
                if line:
                    # Remove list marker (number + punctuation)
                    item_text = re.sub(r'^\d+[.)\]]\s+', '', line)
                    items.append(item_text)

            if items:
                lists.append(ListElement(
                    items=items,
                    list_type="ordered",
                    start_char=match.start(),
                    end_char=match.end()
                ))

        return lists

    def _extract_code_blocks(self, text: str) -> List[CodeBlock]:
        """
        Extract code blocks (fenced and indented)

        Supports:
        - Fenced code blocks: ```language\\ncode\\n```
        - Indented code blocks (4 spaces or tab)
        """
        code_blocks = []

        # Fenced code blocks (```language\ncode\n```)
        fenced_pattern = re.compile(
            r'```(\w+)?\n(.*?)\n```',
            re.DOTALL | re.MULTILINE
        )

        for match in fenced_pattern.finditer(text):
            language = match.group(1) if match.group(1) else None
            content = match.group(2)

            code_blocks.append(CodeBlock(
                language=language,
                content=content,
                start_char=match.start(),
                end_char=match.end()
            ))

        # Indented code blocks (4 spaces or tab at start of line)
        # Only if not already captured by fenced blocks
        indented_pattern = re.compile(
            r'((?:^(?:    |\t).+\n?)+)',
            re.MULTILINE
        )

        for match in indented_pattern.finditer(text):
            # Skip if overlaps with fenced code block
            start = match.start()
            if any(cb.start_char <= start <= cb.end_char for cb in code_blocks):
                continue

            content = match.group(1)
            # Remove indentation
            content = re.sub(r'^(?:    |\t)', '', content, flags=re.MULTILINE)

            code_blocks.append(CodeBlock(
                language=None,
                content=content,
                start_char=match.start(),
                end_char=match.end()
            ))

        return code_blocks

    def _extract_figures(self, text: str) -> List[Figure]:
        """
        Extract figure references

        Supports:
        - Markdown images: ![alt text](url "caption")
        - Figure references: Figure 1: Caption
        """
        figures = []
        figure_num = 1

        # Markdown image syntax: ![alt](url "caption")
        md_image_pattern = re.compile(
            r'!\[([^\]]*)\]\([^\)]+(?:\s+"([^"]+)")?\)',
            re.MULTILINE
        )

        for match in md_image_pattern.finditer(text):
            alt_text = match.group(1) if match.group(1) else None
            caption = match.group(2) if match.group(2) else None

            figures.append(Figure(
                caption=caption,
                alt_text=alt_text,
                figure_number=figure_num,
                start_char=match.start(),
                end_char=match.end()
            ))
            figure_num += 1

        # Figure captions: "Figure 1: Caption text"
        fig_caption_pattern = re.compile(
            r'Figure\s+(\d+):\s*(.+?)(?:\n|$)',
            re.IGNORECASE
        )

        for match in fig_caption_pattern.finditer(text):
            num = int(match.group(1))
            caption = match.group(2).strip()

            figures.append(Figure(
                caption=caption,
                alt_text=None,
                figure_number=num,
                start_char=match.start(),
                end_char=match.end()
            ))

        return figures

    def _extract_equations(self, text: str) -> List[Equation]:
        """
        Extract mathematical equations

        Supports:
        - LaTeX inline: $equation$
        - LaTeX display: $$equation$$
        - Plain text patterns: E = mc^2
        """
        equations = []

        # LaTeX display equations: $$...$$
        display_pattern = re.compile(r'\$\$(.+?)\$\$', re.DOTALL)
        for match in display_pattern.finditer(text):
            latex = match.group(1).strip()
            equations.append(Equation(
                latex=latex,
                plain_text=latex,  # Could parse LaTeX to plain text
                start_char=match.start(),
                end_char=match.end()
            ))

        # LaTeX inline equations: $...$
        inline_pattern = re.compile(r'\$(.+?)\$')
        for match in inline_pattern.finditer(text):
            # Skip if part of display equation
            if any(eq.start_char <= match.start() <= eq.end_char for eq in equations):
                continue

            latex = match.group(1).strip()
            equations.append(Equation(
                latex=latex,
                plain_text=latex,
                start_char=match.start(),
                end_char=match.end()
            ))

        return equations

    def _extract_citations(self, text: str) -> List[Citation]:
        """
        Extract citations and references

        Supports:
        - Markdown links: [Author et al., 2023](url)
        - Parenthetical: (Author, 2023)
        - Brackets: [1], [Author2023]
        """
        citations = []

        # Author-year pattern: (Smith et al., 2023)
        author_year_pattern = re.compile(
            r'\(([A-Z][a-z]+(?:\s+(?:et\s+al\.|&|and)\s+[A-Z][a-z]+)?),\s*(\d{4})\)'
        )

        for match in author_year_pattern.finditer(text):
            author_text = match.group(1)
            year = int(match.group(2))

            # Parse authors
            authors = [a.strip() for a in re.split(r'\s+(?:et\s+al\.|&|and)\s+', author_text)]

            citations.append(Citation(
                text=match.group(0),
                authors=authors,
                year=year,
                source=None,
                start_char=match.start(),
                end_char=match.end()
            ))

        # Numbered citations: [1], [2]
        numbered_pattern = re.compile(r'\[(\d+)\]')
        for match in numbered_pattern.finditer(text):
            citations.append(Citation(
                text=match.group(0),
                authors=None,
                year=None,
                source=f"Reference {match.group(1)}",
                start_char=match.start(),
                end_char=match.end()
            ))

        return citations

    def _extract_footnotes(self, text: str) -> List[Footnote]:
        """
        Extract footnotes

        Supports:
        - Markdown style: [^1], [^note]
        - Superscript numbers: ¹, ²
        """
        footnotes = []

        # Markdown footnote references: [^1]
        ref_pattern = re.compile(r'\[\^(\d+)\]')

        # Markdown footnote definitions: [^1]: content
        def_pattern = re.compile(r'^\[\^(\d+)\]:\s*(.+)$', re.MULTILINE)

        # Match references with definitions
        definitions = {}
        for match in def_pattern.finditer(text):
            num = int(match.group(1))
            content = match.group(2).strip()
            definitions[num] = (content, match.start())

        # Create footnotes from references
        for match in ref_pattern.finditer(text):
            num = int(match.group(1))
            if num in definitions:
                content, _ = definitions[num]
                footnotes.append(Footnote(
                    number=num,
                    content=content,
                    reference_char=match.start()
                ))

        return footnotes

    def _extract_definitions(self, text: str, paragraphs: List[Paragraph]) -> List[Definition]:
        """
        Extract term definitions

        Supports:
        - Explicit: Term: definition
        - Markdown definition lists
        - Bold/italic patterns: **Term** - definition
        """
        definitions = []

        # Pattern 1: "Term: definition" or "Term - definition"
        explicit_pattern = re.compile(
            r'^([A-Z][a-zA-Z\s]{2,50}):\s*(.+)$',
            re.MULTILINE
        )

        for match in explicit_pattern.finditer(text):
            term = match.group(1).strip()
            definition = match.group(2).strip()

            # Find containing paragraph
            para_id = None
            match_pos = match.start()
            for i, para in enumerate(paragraphs):
                if para.start_char <= match_pos <= para.end_char:
                    para_id = i
                    break

            definitions.append(Definition(
                term=term,
                definition=definition,
                context_paragraph_id=para_id
            ))

        # Pattern 2: Markdown bold: **Term** - definition
        bold_pattern = re.compile(
            r'\*\*([A-Z][a-zA-Z\s]{2,50})\*\*\s*[-–—]\s*(.+?)(?:\n|$)',
            re.MULTILINE
        )

        for match in bold_pattern.finditer(text):
            term = match.group(1).strip()
            definition = match.group(2).strip()

            # Find containing paragraph
            para_id = None
            match_pos = match.start()
            for i, para in enumerate(paragraphs):
                if para.start_char <= match_pos <= para.end_char:
                    para_id = i
                    break

            definitions.append(Definition(
                term=term,
                definition=definition,
                context_paragraph_id=para_id
            ))

        return definitions

    def _build_heading_hierarchy(self, headings: List[Heading]) -> None:
        """
        Build parent-child relationships between headings

        Args:
            headings: List of headings (modified in-place to add child_ids)
        """
        for i, heading in enumerate(headings):
            # Find all child headings (higher level numbers, before next same/lower level)
            for j in range(i + 1, len(headings)):
                next_heading = headings[j]

                # Child must have higher level number (H2 is child of H1)
                if next_heading.level > heading.level:
                    heading.child_ids.append(j)
                # Stop at same or lower level heading
                elif next_heading.level <= heading.level:
                    break
