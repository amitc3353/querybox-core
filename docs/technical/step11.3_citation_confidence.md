# Step 11.3: Citation & Confidence Scoring

**Status**: Design Documentation
**Created**: 2025-10-30
**Dependencies**: Step 11.2 (Chain-of-Verification), Step 10.3 (Citation Extraction)
**Enables**: Deliverable "POST /api/v1/answer endpoint with verified citations"

---

## Table of Contents
1. [Goal & Architecture](#1-goal--architecture)
2. [Implementation](#2-implementation)
3. [Security & Validation](#3-security--validation)
4. [Performance Decisions](#4-performance-decisions)
5. [Error Handling](#5-error-handling)
6. [Configuration](#6-configuration)
7. [Integration Details](#7-integration-details)
8. [Testing Approach](#8-testing-approach)
9. [Monitoring](#9-monitoring)
10. [Code Snippets](#10-code-snippets)
11. [Important Decisions](#11-important-decisions)

---

## 1. GOAL & ARCHITECTURE

### Objective

**Primary Goal**: Deliver production-ready answer generation with transparent, granular confidence scoring and rich citation formatting that enables users to verify every claim against source documents with clear abstention when answers cannot be reliably generated.

**Why This Approach**: Building on Step 11.2's hallucination detection, Step 11.3 transforms raw verification signals into actionable user-facing features: **intelligent abstention** (no answer is better than wrong answer), **per-claim confidence** (not just overall answer confidence), and **citation quality indicators** (strong/medium/weak evidence markers). This approach prioritizes user trust and citation transparency - QueryboxCore's core differentiator.

### System Design Pattern

**Pattern**: **Strategy Pattern** for confidence calculation + **Decorator Pattern** for citation enrichment

The citation & confidence system implements a 4-stage enhancement pipeline:

```
┌────────────────────────────────────────────────────────────────┐
│          CITATION & CONFIDENCE ENHANCEMENT PIPELINE            │
└────────────────────────────────────────────────────────────────┘

Input: VerifiedAnswerResponse (from Step 11.2)
  ↓
┌──────────────────────────────────────────────────────────────┐
│ Stage 1: Abstention Decision Engine                         │
│ - Multi-factor abstention analysis                          │
│   * Low confidence (<0.3)                                    │
│   * High hallucination probability (>0.7)                   │
│   * No quote matches for propositions                       │
│   * All verifications failed                                │
│ - Categorize abstention reason                              │
│ - Calculate abstention confidence (how sure we can't answer) │
└──────────────────────────────────────────────────────────────┘
  ↓
┌──────────────────────────────────────────────────────────────┐
│ Stage 2: Granular Confidence Calculation                    │
│ - Per-proposition confidence scoring                         │
│   * Factor 1: Passage relevance (rerank_score) - 40%       │
│   * Factor 2: Quote match quality (similarity) - 35%       │
│   * Factor 3: Verification agreement - 15%                  │
│   * Factor 4: Citation count - 10%                         │
│ - Confidence breakdown for transparency                      │
│ - Aggregate to overall verified confidence                   │
└──────────────────────────────────────────────────────────────┘
  ↓
┌──────────────────────────────────────────────────────────────┐
│ Stage 3: Citation Enrichment                                 │
│ - Link quote matches to specific citations                   │
│ - Calculate citation quality (strong/medium/weak)            │
│ - Add matched text highlighting                              │
│ - Support multiple citations per claim                       │
│ - Inline citation formatting [1: doc_name, p.5]            │
└──────────────────────────────────────────────────────────────┘
  ↓
┌──────────────────────────────────────────────────────────────┐
│ Stage 4: Enhanced Metadata Assembly                          │
│ - Build proposition details array                            │
│   * Per-prop: confidence, citations, quote, verified status │
│ - Add confidence breakdown                                   │
│ - Add abstention factors analysis                            │
│ - Citation validation (all [N] markers have sources)        │
└──────────────────────────────────────────────────────────────┘

Output: EnhancedAnswerResponse (production-ready with full metadata)
```

### Component Boundaries and Interfaces

**Core Components:**

1. **AbstentionService** (`abstention_service.py`)
   - Makes intelligent abstention decisions based on verification signals
   - Interface: `async should_abstain(verified_response: VerifiedAnswerResponse) -> AbstentionDecision`
   - Depends on: VerificationMetadata
   - Returns: Decision (abstain/answer), reason category, confidence

2. **ConfidenceCalculator** (`confidence_calculator.py`)
   - Calculates granular per-proposition confidence scores
   - Interface: `calculate_proposition_confidence(prop: Proposition, quote_matches: List[QuoteMatch], verification: VerificationAnswer) -> PropConfidence`
   - Algorithm: Weighted multi-factor scoring (passage relevance, quote quality, verification agreement, citation count)
   - Returns: Confidence score (0-1) with factor breakdown

3. **CitationEnricher** (`citation_enricher.py`)
   - Links quote matches to citations and adds quality indicators
   - Interface: `enrich_citations(citations: List[Citation], quote_matches: Dict[str, List[QuoteMatch]]) -> List[EnrichedCitation]`
   - Functionality: Citation quality scoring, matched text highlighting, inline formatting
   - Returns: Enhanced citations with quote match info

4. **MetadataAssembler** (`metadata_assembler.py`)
   - Assembles comprehensive metadata for API response
   - Interface: `build_enhanced_metadata(verified_response: VerifiedAnswerResponse, prop_details: List[PropDetail]) -> EnhancedMetadata`
   - Consolidates: Confidence breakdown, proposition details, abstention factors, citation validation

### Data Flow Architecture

**Request Flow:**
```
VerifiedAnswerResponse (Step 11.2) → POST /api/v1/answer
    → CitationConfidenceService.enhance()
    → Stage 1: AbstentionService.should_abstain()
    → If ABSTAIN: Return abstention response
    → If ANSWER: Stage 2: ConfidenceCalculator.calculate_all()
    → Stage 3: CitationEnricher.enrich()
    → Stage 4: MetadataAssembler.build()
    → EnhancedAnswerResponse (production-ready)
```

**Data Models:**

- `AbstentionDecision`: Decision (abstain/answer), category, reason, confidence
- `PropConfidence`: Proposition ID, confidence score, factor breakdown
- `EnrichedCitation`: Extends Citation with quote_match, quality_indicator, highlighted_text
- `PropositionDetail`: Comprehensive per-prop metadata (confidence, citations, quote, verified status)
- `EnhancedMetadata`: Extends VerificationMetadata with confidence_breakdown, proposition_details, abstention_factors
- `EnhancedAnswerResponse`: Final production response model

---

## 2. IMPLEMENTATION

### Files to Create

**Core Service Files:**

1. **`backend/app/services/citation_confidence/abstention_service.py`** (280 lines)
   - Purpose: Multi-factor abstention decision engine
   - Key classes: `AbstentionService`, `AbstentionDecision`
   - Algorithm: 4-factor scoring (confidence, hallucination, quotes, verification)
   - Dependencies: VerificationMetadata

2. **`backend/app/services/citation_confidence/confidence_calculator.py`** (320 lines)
   - Purpose: Granular per-proposition confidence calculation
   - Key classes: `ConfidenceCalculator`, `PropConfidence`, `ConfidenceBreakdown`
   - Algorithm: Weighted 4-factor scoring with aggregation strategies
   - Dependencies: QuoteMatch, VerificationAnswer, Proposition

3. **`backend/app/services/citation_confidence/citation_enricher.py`** (350 lines)
   - Purpose: Link quotes to citations and add quality indicators
   - Key classes: `CitationEnricher`, `EnrichedCitation`, `CitationQuality`
   - Features: Quality scoring (strong/medium/weak), text highlighting, inline formatting
   - Dependencies: Citation, QuoteMatch

4. **`backend/app/services/citation_confidence/metadata_assembler.py`** (240 lines)
   - Purpose: Build comprehensive enhanced metadata
   - Key classes: `MetadataAssembler`, `PropositionDetail`, `EnhancedMetadata`
   - Features: Proposition details array, confidence breakdown, abstention factors
   - Dependencies: All above services

5. **`backend/app/services/citation_confidence_service.py`** (400 lines)
   - Purpose: Main orchestration service (facade pattern)
   - Key classes: `CitationConfidenceService`
   - Orchestrates: All 4 stages of enhancement pipeline
   - Interface: `async enhance(verified_response: VerifiedAnswerResponse) -> EnhancedAnswerResponse`

**Schema Files:**

6. **`backend/app/schemas/citation_confidence.py`** (380 lines)
   - Purpose: Pydantic models for citation & confidence
   - Models: `AbstentionDecision`, `PropConfidence`, `EnrichedCitation`, `PropositionDetail`, `ConfidenceBreakdown`, `EnhancedMetadata`, `EnhancedAnswerResponse`

**API Files:**

7. **`backend/app/api/v1/endpoints/answer.py`** (modify existing)
   - Update: `POST /api/v1/answer` to use CitationConfidenceService
   - Update: `POST /api/v1/answer/verified` to return EnhancedAnswerResponse
   - Add: Response examples with abstention cases

**Utility Files:**

8. **`backend/app/utils/citation_formatting.py`** (180 lines)
   - Purpose: Citation formatting utilities
   - Functions: `format_inline_citation()`, `highlight_text()`, `validate_citation_numbers()`

### Core Classes and Function Signatures

**CitationConfidenceService (Main Orchestrator):**

```python
class CitationConfidenceService:
    def __init__(
        self,
        abstention_service: AbstentionService,
        confidence_calculator: ConfidenceCalculator,
        citation_enricher: CitationEnricher,
        metadata_assembler: MetadataAssembler
    ):
        """Initialize citation & confidence service with dependencies."""

    async def enhance(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> EnhancedAnswerResponse:
        """
        Execute full citation & confidence enhancement pipeline.

        Complexity: O(P) where P = propositions (3-5 typically)
        Time: ~100-200ms additional latency (mostly CPU-bound)

        Returns EnhancedAnswerResponse with granular confidence and rich citations.
        """

    async def _process_abstention(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> Optional[EnhancedAnswerResponse]:
        """Stage 1: Check if should abstain and return abstention response if yes."""

    async def _calculate_confidences(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> Dict[str, PropConfidence]:
        """Stage 2: Calculate per-proposition confidence scores."""

    async def _enrich_citations(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> List[EnrichedCitation]:
        """Stage 3: Enrich citations with quote matches and quality indicators."""

    async def _build_enhanced_metadata(
        self,
        verified_response: VerifiedAnswerResponse,
        prop_confidences: Dict[str, PropConfidence],
        enriched_citations: List[EnrichedCitation],
        abstention_decision: AbstentionDecision
    ) -> EnhancedMetadata:
        """Stage 4: Assemble comprehensive enhanced metadata."""
```

**AbstentionService:**

```python
class AbstentionService:
    def __init__(self, config: AbstentionConfig):
        """Initialize with threshold configuration."""

    async def should_abstain(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> AbstentionDecision:
        """
        Multi-factor abstention decision.

        Factors:
        1. Low confidence: verified_confidence < 0.3
        2. High hallucination: hallucination_probability > 0.7
        3. No quotes: All propositions lack quote matches
        4. Verification failed: All verification questions failed

        Algorithm:
        - If ANY critical factor triggered → ABSTAIN
        - Categorize reason (confidence/hallucination/evidence/verification)
        - Calculate abstention confidence (how sure we can't answer)

        Complexity: O(P) where P = propositions
        Time: <10ms
        """

    def _check_low_confidence(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> bool:
        """Check if verified_confidence below threshold."""

    def _check_high_hallucination(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> bool:
        """Check if hallucination_probability above threshold."""

    def _check_no_quotes(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> bool:
        """Check if all propositions lack quote matches."""

    def _check_verification_failed(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> bool:
        """Check if all verification questions failed."""

    def _categorize_reason(
        self,
        factors_triggered: List[str]
    ) -> AbstentionCategory:
        """Categorize abstention reason for user-facing message."""
```

**ConfidenceCalculator:**

```python
class ConfidenceCalculator:
    def __init__(self, weights: ConfidenceWeights):
        """
        Initialize with factor weights.

        Default weights:
        - passage_relevance: 0.40 (rerank_score from Step 10.2)
        - quote_match_quality: 0.35 (similarity_score from quote matching)
        - verification_agreement: 0.15 (verification answer matches proposition)
        - citation_count: 0.10 (number of supporting citations)
        """

    async def calculate_all(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> Dict[str, PropConfidence]:
        """
        Calculate confidence for all propositions.

        Returns:
            Dict mapping proposition_id → PropConfidence
        """

    async def calculate_proposition_confidence(
        self,
        proposition: Proposition,
        quote_matches: List[QuoteMatch],
        verification_answer: Optional[VerificationAnswer],
        citations: List[Citation]
    ) -> PropConfidence:
        """
        Calculate confidence for a single proposition.

        4-Factor Algorithm:

        1. Passage Relevance (40%):
           score = max(passage.rerank_score for passage in citations)
           Rationale: Use best passage score

        2. Quote Match Quality (35%):
           score = max(quote.similarity_score for quote in quote_matches)
           Rationale: Best quote indicates strong evidence

        3. Verification Agreement (15%):
           score = 1.0 if verification agrees, 0.5 if neutral, 0.0 if disagrees
           Rationale: Independent verification confirms claim

        4. Citation Count (10%):
           score = min(1.0, len(citations) / 3.0)
           Rationale: Multiple sources increase confidence, capped at 3

        Final confidence = weighted_sum(factors) * (1 - hallucination_probability)

        Complexity: O(C + Q) where C = citations, Q = quote matches
        Time: ~5-10ms per proposition
        """

    def _calculate_passage_relevance_score(
        self,
        citations: List[Citation]
    ) -> float:
        """Factor 1: Best passage relevance score."""

    def _calculate_quote_match_score(
        self,
        quote_matches: List[QuoteMatch]
    ) -> float:
        """Factor 2: Best quote similarity score."""

    def _calculate_verification_agreement_score(
        self,
        proposition: Proposition,
        verification_answer: Optional[VerificationAnswer]
    ) -> float:
        """Factor 3: Verification agreement score."""

    def _calculate_citation_count_score(
        self,
        citations: List[Citation]
    ) -> float:
        """Factor 4: Citation diversity score."""

    def _aggregate_to_overall_confidence(
        self,
        prop_confidences: Dict[str, PropConfidence]
    ) -> float:
        """
        Aggregate per-prop confidences to overall verified confidence.

        Strategies:
        - Weighted average (default): Avg all prop confidences
        - Minimum (conservative): Use lowest prop confidence
        - Probabilistic: 1 - product(1 - conf_i) for all i

        Default: Weighted average
        """
```

**CitationEnricher:**

```python
class CitationEnricher:
    def __init__(self):
        """Initialize citation enricher."""

    async def enrich_citations(
        self,
        citations: List[Citation],
        quote_matches: Dict[str, List[QuoteMatch]],
        propositions: List[Proposition]
    ) -> List[EnrichedCitation]:
        """
        Enrich citations with quote match info and quality indicators.

        Enhancements:
        1. Link quote matches to specific citations
        2. Calculate citation quality (strong/medium/weak)
        3. Add highlighted matched text
        4. Map citations to propositions (which claims cite which docs)
        5. Validate citation numbers [1], [2], etc.

        Complexity: O(C * Q) where C = citations, Q = quote matches
        Time: ~50-100ms
        """

    def _link_quote_to_citation(
        self,
        quote_match: QuoteMatch,
        citations: List[Citation]
    ) -> Optional[Citation]:
        """Find citation corresponding to quote match's passage."""

    def _calculate_citation_quality(
        self,
        citation: Citation,
        quote_matches: List[QuoteMatch]
    ) -> CitationQuality:
        """
        Calculate citation quality indicator.

        Quality Levels:
        - STRONG: similarity_score >= 0.95 (exact or near-exact quote)
        - MEDIUM: 0.85 <= similarity_score < 0.95 (paraphrased quote)
        - WEAK: citation exists but no quote match (indirect support)

        Returns: Enum [STRONG, MEDIUM, WEAK]
        """

    def _highlight_matched_text(
        self,
        passage_text: str,
        quote_match: QuoteMatch
    ) -> str:
        """
        Add HTML highlighting to matched text in passage.

        Example:
        Input: "France's capital is Paris, located in the north."
        Quote match: "capital is Paris" (positions 10-26)
        Output: "France's <mark>capital is Paris</mark>, located in the north."
        """

    def _format_inline_citation(
        self,
        citation: EnrichedCitation,
        format_style: Literal["simple", "detailed"]
    ) -> str:
        """
        Format inline citation marker.

        Styles:
        - simple: "[1]"
        - detailed: "[1: doc_name, p.5]"

        Default: simple (detailed available via API parameter)
        """

    async def _validate_citation_numbers(
        self,
        answer_text: str,
        citations: List[EnrichedCitation]
    ) -> List[str]:
        """
        Validate all [N] markers in answer have corresponding citations.

        Returns:
            List of validation errors (empty if valid)

        Example errors:
        - "Citation [3] referenced but not found in citations list"
        - "Citation [1] appears in list but not referenced in answer"
        """
```

### Database Schema Changes

**New Table: `answer_confidence_logs`**

```sql
CREATE TABLE answer_confidence_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    answer_id UUID REFERENCES answers(id) ON DELETE CASCADE,
    verification_log_id UUID REFERENCES verification_logs(id),

    -- Abstention data
    abstained BOOLEAN NOT NULL,
    abstention_reason VARCHAR(50),  -- 'low_confidence', 'high_hallucination', 'no_evidence', 'verification_failed'
    abstention_confidence FLOAT,

    -- Overall confidence
    verified_confidence FLOAT NOT NULL,
    confidence_breakdown JSONB NOT NULL,  -- {passage_relevance: 0.45, quote_quality: 0.30, ...}

    -- Per-proposition details
    proposition_details JSONB NOT NULL,  -- Array of {prop_id, confidence, citations, has_quote, verified}

    -- Citation metadata
    total_citations INTEGER NOT NULL,
    strong_citations INTEGER DEFAULT 0,
    medium_citations INTEGER DEFAULT 0,
    weak_citations INTEGER DEFAULT 0,
    citation_validation_errors JSONB,  -- Array of error messages

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_answer_id (answer_id),
    INDEX idx_abstained (abstained),
    INDEX idx_created_at (created_at)
);
```

**Modify Table: `answers`** (from Step 11.1)

```sql
ALTER TABLE answers ADD COLUMN abstained BOOLEAN DEFAULT FALSE;
ALTER TABLE answers ADD COLUMN abstention_reason VARCHAR(100);
ALTER TABLE answers ADD COLUMN confidence_log_id UUID REFERENCES answer_confidence_logs(id);
```

**No changes to existing tables**: `verification_logs`, `citations` remain unchanged

### Critical Algorithms with Complexity Analysis

**1. Multi-Factor Abstention Algorithm:**

```python
def should_abstain(verified_response):
    """
    Complexity: O(P) where P = propositions (3-5 typically)
    Time: <10ms

    Decision tree:
    1. Check verified_confidence < LOW_CONFIDENCE_THRESHOLD (0.3)
       → ABSTAIN with reason "low_confidence"
    2. Check hallucination_probability > HIGH_HALLUCINATION_THRESHOLD (0.7)
       → ABSTAIN with reason "high_hallucination"
    3. Check if all propositions lack quote matches
       → ABSTAIN with reason "no_evidence"
    4. Check if verification_metadata.status == "failed"
       → ABSTAIN with reason "verification_failed"
    5. Else → ANSWER
    """
    factors_triggered = []

    # Factor 1: Low confidence
    if verified_response.verified_confidence < settings.LOW_CONFIDENCE_THRESHOLD:
        factors_triggered.append("low_confidence")

    # Factor 2: High hallucination
    if verified_response.verification_metadata.hallucination_probability > settings.HIGH_HALLUCINATION_THRESHOLD:
        factors_triggered.append("high_hallucination")

    # Factor 3: No evidence (no quote matches)
    quote_matches = verified_response.verification_metadata.quote_matches
    if all(len(matches) == 0 for matches in quote_matches.values()):
        factors_triggered.append("no_evidence")

    # Factor 4: Verification failed
    if verified_response.verification_metadata.status == "failed":
        factors_triggered.append("verification_failed")

    # Decision
    if factors_triggered:
        return AbstentionDecision(
            should_abstain=True,
            reason=_categorize_reason(factors_triggered),
            factors=factors_triggered,
            confidence=_calculate_abstention_confidence(factors_triggered)
        )
    else:
        return AbstentionDecision(should_abstain=False)
```

**2. Granular Confidence Calculation Algorithm:**

```python
def calculate_proposition_confidence(prop, quote_matches, verification, citations):
    """
    Complexity: O(C + Q) where C = citations (~2-5), Q = quote matches (~1-3)
    Time: ~5-10ms per proposition

    Weighted 4-factor algorithm:
    confidence = w1*passage_rel + w2*quote_qual + w3*verif_agree + w4*cite_count

    Default weights: [0.40, 0.35, 0.15, 0.10]
    """
    # Factor 1: Passage relevance (40%)
    passage_scores = [c.relevance_score for c in citations if c.proposition_id == prop.id]
    passage_relevance = max(passage_scores) if passage_scores else 0.0

    # Factor 2: Quote match quality (35%)
    quote_scores = [q.similarity_score for q in quote_matches]
    quote_quality = max(quote_scores) if quote_scores else 0.0

    # Factor 3: Verification agreement (15%)
    if verification and verification.answer:
        verif_agree = _compute_agreement(prop.content, verification.answer)
    else:
        verif_agree = 0.5  # Neutral if no verification

    # Factor 4: Citation count (10%)
    cite_count_score = min(1.0, len(citations) / 3.0)  # Capped at 3 citations

    # Weighted sum
    raw_confidence = (
        0.40 * passage_relevance +
        0.35 * quote_quality +
        0.15 * verif_agree +
        0.10 * cite_count_score
    )

    # Apply hallucination penalty
    hallucination_prob = verified_response.verification_metadata.hallucination_probability
    final_confidence = raw_confidence * (1 - hallucination_prob)

    return PropConfidence(
        proposition_id=prop.id,
        confidence=round(final_confidence, 3),
        breakdown={
            "passage_relevance": round(passage_relevance, 3),
            "quote_quality": round(quote_quality, 3),
            "verification_agreement": round(verif_agree, 3),
            "citation_count": round(cite_count_score, 3)
        }
    )
```

**3. Citation Quality Scoring Algorithm:**

```python
def calculate_citation_quality(citation, quote_matches):
    """
    Complexity: O(Q) where Q = quote matches for this citation (~1-3)
    Time: <5ms

    Quality levels:
    - STRONG: Best quote match >= 0.95 (exact/near-exact)
    - MEDIUM: Best quote match >= 0.85 and < 0.95 (paraphrased)
    - WEAK: Citation exists but no quote matches (indirect support)
    """
    # Find best quote match for this citation
    citation_quotes = [
        qm for qm in quote_matches
        if qm.passage_id == citation.passage_id
    ]

    if not citation_quotes:
        return CitationQuality.WEAK

    best_similarity = max(q.similarity_score for q in citation_quotes)

    if best_similarity >= 0.95:
        return CitationQuality.STRONG
    elif best_similarity >= 0.85:
        return CitationQuality.MEDIUM
    else:
        return CitationQuality.WEAK
```

---

## 3. SECURITY & VALIDATION

### Input Sanitization Approach

**Confidence Score Validation**:
- All confidence scores must be in range [0.0, 1.0]
- Reject responses with confidence scores outside range (data corruption)
- Validate factor weights sum to 1.0 in ConfidenceCalculator

**Citation Number Validation**:
```python
@validator('answer_text')
def validate_citation_numbers(cls, v, values):
    """Ensure all [N] citations have corresponding citation entries."""
    citation_pattern = r'\[(\d+)\]'
    cited_numbers = set(int(m) for m in re.findall(citation_pattern, v))

    if 'citations' in values:
        available_numbers = set(c.citation_number for c in values['citations'])
        missing = cited_numbers - available_numbers
        if missing:
            raise ValueError(f"Citations referenced but not found: {missing}")

    return v
```

**HTML Injection Prevention**:
- Sanitize matched text before highlighting to prevent XSS
- Use HTML escaping for passage_text in EnrichedCitation
- Allow only `<mark>` tags for highlighting (whitelist approach)

```python
def highlight_matched_text(passage_text: str, quote_match: QuoteMatch) -> str:
    """Safely highlight text preventing XSS."""
    # Escape HTML in passage text
    safe_passage = html.escape(passage_text)

    # Apply highlighting with safe tags
    start, end = quote_match.start_pos, quote_match.end_pos
    highlighted = (
        safe_passage[:start] +
        f"<mark>{safe_passage[start:end]}</mark>" +
        safe_passage[end:]
    )

    return highlighted
```

### Authentication/Authorization Checks

**API Key Authentication**:
- All endpoints require same authentication as Step 11.2
- Uses existing `verify_api_key()` dependency
- Rate limiting: Inherits from Step 11.2 (5 verified answers per minute)

**Document Access Control**:
- Verify user has access to all documents in citations
- Log citation access for audit trail
- Redact citations for documents user lacks permission to view

### Rate Limiting

**No Additional Limits**:
- Citation & confidence enhancement adds minimal latency (~100-200ms)
- Inherits rate limits from Step 11.2 verification endpoint
- CPU-bound operations (not LLM calls) so less resource-intensive

### Data Protection Considerations

**PII Handling**:
- Never log full proposition text or citation content (only hashes)
- Redact PII from confidence logs
- Store confidence metadata with 30-day retention (configurable)

**Security Logging**:
```python
logger.info(
    "Citation & confidence enhancement completed",
    extra={
        "request_id": request_id,
        "abstained": abstention_decision.should_abstain,
        "abstention_reason_hash": hashlib.sha256(reason.encode()).hexdigest()[:16],
        "avg_confidence": round(avg_confidence, 2),
        "strong_citations_count": strong_count,
        "user_id": get_user_id_from_context(),
    }
)
```

---

## 4. PERFORMANCE DECISIONS

### Caching Strategy

**Single-Level Caching**:

```python
# L1 Cache: Enhanced Answer Results (Redis, 1-hour TTL)
cache_key = f"enhanced_answer:{query_hash}:{document_ids_hash}"
# Caches entire EnhancedAnswerResponse
# Invalidate on: Document updates, verification settings changes
```

**Cache Hit Rate Target**: 30-40% (same as Step 11.2 verification cache)

**Rationale for Single-Level**:
- Citation & confidence is final step - caching intermediate results not beneficial
- Enhancement is CPU-bound (~100-200ms), not I/O-bound
- Aggressive caching at this level reduces entire pipeline cost

### Query Optimization Choices

**No Database Queries During Enhancement**:
- All data needed is in VerifiedAnswerResponse (in-memory)
- Database writes are asynchronous (confidence logs)
- No blocking on database operations

**Batch Processing**:
```python
# Process all propositions in parallel
prop_confidence_tasks = [
    self.confidence_calculator.calculate_proposition_confidence(prop, ...)
    for prop in propositions
]
prop_confidences = await asyncio.gather(*prop_confidence_tasks)
```

**Index Strategy**:
```sql
-- Enable fast confidence log queries
CREATE INDEX idx_confidence_logs_answer_id ON answer_confidence_logs(answer_id);
CREATE INDEX idx_confidence_logs_abstained ON answer_confidence_logs(abstained);

-- Partial index for low-confidence analysis
CREATE INDEX idx_low_confidence ON answer_confidence_logs(verified_confidence)
WHERE verified_confidence < 0.5;
```

### Async vs Sync Trade-offs

**Synchronous Operations** (CPU-bound, no async benefit):
- Confidence calculation (pure math)
- Citation quality scoring
- Text highlighting
- Citation validation

**Asynchronous Operations** (I/O-bound):
- Database confidence log writes (background task)
- Cache reads/writes

**No Parallel Execution Needed**:
- Enhancement is fast (<200ms total)
- Sequential processing is clear and maintainable
- Premature optimization avoided

**Performance Profile**:
- Confidence calculation: ~50-80ms (3-5 propositions × 10ms each)
- Citation enrichment: ~30-50ms (5-10 citations × 5ms each)
- Metadata assembly: ~10-20ms (pure data structure building)
- **Total: ~100-150ms** (negligible vs Step 11.2's 4-5s verification)

### Resource Limits

**Memory Limits**:
- Maximum propositions: 10 (from Step 11.2)
- Maximum citations: 20 (typical 5-10 from Step 10.3)
- Maximum enriched metadata size: ~50KB per response
- Total memory per enhancement: ~5-10 MB (minimal)

**Computational Limits**:
- No LLM calls (all local computation)
- CPU usage: <100ms per enhancement
- Max concurrent enhancements: Unlimited (CPU-bound, no external dependencies)

**No Token Budget** (no LLM usage in this step)

---

## 5. ERROR HANDLING

### Failure Scenarios Covered

**1. Confidence Calculation Failures**:
```python
try:
    prop_confidence = await calculator.calculate_proposition_confidence(prop, ...)
except Exception as e:
    logger.error(f"Confidence calculation failed for proposition {prop.id}: {e}")
    # Fallback: Use baseline confidence or 0.5 (neutral)
    prop_confidence = PropConfidence(
        proposition_id=prop.id,
        confidence=0.5,  # Neutral confidence
        is_fallback=True
    )
```

**2. Citation Enrichment Failures**:
```python
try:
    enriched_citations = await enricher.enrich_citations(citations, ...)
except Exception as e:
    logger.error(f"Citation enrichment failed: {e}")
    # Fallback: Return basic citations without enrichment
    enriched_citations = [EnrichedCitation.from_citation(c) for c in citations]
```

**3. Citation Validation Failures**:
- If validation finds errors (missing citation numbers), log warnings but don't fail
- Set `citation_validation_errors` in metadata for debugging
- Continue with response (degraded but functional)

**4. Abstention Decision Failures**:
- Conservative fallback: If abstention logic fails, ABSTAIN (safer than returning wrong answer)
- Set abstention_reason = "error" for monitoring

### Retry Logic Implementation

**No Retries Needed**:
- All operations are deterministic (no external calls)
- Failures are handled with fallbacks, not retries
- Database writes use background tasks with built-in retry

### Rollback Procedures

**No Database Rollback Needed**:
- Confidence logs are write-only (no updates)
- If confidence log write fails, answer is still returned to user
- Log write failures tracked separately for manual recovery

**Cache Invalidation**:
```python
async def handle_enhancement_failure(cache_key: str):
    """Remove cache entry on enhancement failure."""
    await redis.delete(cache_key)
    logger.info(f"Invalidated cache after enhancement failure: {cache_key}")
```

### Logging Strategy

**Structured Logging with Log Levels**:

```python
# INFO: Normal operation metrics
logger.info(
    "Citation & confidence enhancement completed",
    extra={
        "stage": "enhancement_complete",
        "abstained": False,
        "avg_confidence": 0.87,
        "strong_citations": 3,
        "latency_ms": 145,
    }
)

# WARNING: Potential issues
logger.warning(
    "Low confidence answer",
    extra={
        "stage": "confidence_calculation",
        "verified_confidence": 0.25,
        "abstention_triggered": True,
        "reason": "low_confidence",
    }
)

# ERROR: Failures requiring attention
logger.error(
    "Citation validation errors found",
    extra={
        "stage": "citation_enrichment",
        "errors": validation_errors,
        "action": "returning_with_warnings",
    }
)
```

**Log Retention**:
- INFO logs: 7 days (high volume)
- WARNING logs: 30 days (for trend analysis)
- ERROR logs: 90 days (for debugging)

---

## 6. CONFIGURATION

### Environment Variables

```bash
# Abstention Configuration
ABSTENTION_ENABLED=true                     # Enable abstention logic
LOW_CONFIDENCE_THRESHOLD=0.3                # Abstain if confidence below this
HIGH_HALLUCINATION_THRESHOLD=0.7            # Abstain if hallucination above this
ABSTENTION_REQUIRE_ALL_FACTORS=false        # Require all factors or any one

# Confidence Calculation Weights
CONFIDENCE_WEIGHT_PASSAGE_RELEVANCE=0.40    # Passage rerank score weight
CONFIDENCE_WEIGHT_QUOTE_QUALITY=0.35        # Quote similarity weight
CONFIDENCE_WEIGHT_VERIFICATION=0.15         # Verification agreement weight
CONFIDENCE_WEIGHT_CITATION_COUNT=0.10       # Citation count weight

# Citation Quality Thresholds
CITATION_STRONG_THRESHOLD=0.95              # Strong quality (exact quote)
CITATION_MEDIUM_THRESHOLD=0.85              # Medium quality (paraphrased)

# Citation Formatting
CITATION_INLINE_FORMAT=simple               # 'simple' ([1]) or 'detailed' ([1: doc, p.5])
CITATION_HIGHLIGHT_ENABLED=true             # Enable matched text highlighting
CITATION_VALIDATION_STRICT=false            # Fail on validation errors (vs warn)

# Performance
CONFIDENCE_CALCULATION_TIMEOUT_MS=200       # Timeout per enhancement
CONFIDENCE_LOG_ASYNC_WRITE=true             # Write logs asynchronously

# Caching
ENHANCED_ANSWER_CACHE_TTL_SECONDS=3600      # 1 hour
```

### Default Values and Rationale

**Low Confidence Threshold (0.3)**:
- **Rationale**: Conservative threshold for abstention
- Lower than 0.3: Very uncertain, better to abstain
- Allows some uncertainty (0.3-0.5) but flags clearly
- Empirically validated in RAG systems

**Confidence Weight Distribution**:
- **Passage Relevance (40%)**: Strongest signal - reranked passages already filtered
- **Quote Quality (35%)**: Second strongest - direct evidence in text
- **Verification Agreement (15%)**: Supportive but can have false negatives
- **Citation Count (10%)**: Weak signal - multiple sources good but not critical
- **Rationale**: Prioritize direct evidence (quotes + passages) over indirect (verification count)

**Citation Strong Threshold (0.95)**:
- **Rationale**: High bar for "exact quote"
- 95%+ similarity is near-exact match
- Lower threshold would dilute "strong" quality indicator
- 85-95% range is paraphrased (medium quality)

### Feature Flags

**Runtime Toggle**:
```python
class CitationConfidenceConfig(BaseSettings):
    """Configuration with feature flags."""

    # Master switches
    ABSTENTION_ENABLED: bool = True
    CONFIDENCE_CALCULATION_ENABLED: bool = True
    CITATION_ENRICHMENT_ENABLED: bool = True

    # Abstention modes
    ABSTENTION_STRICT_MODE: bool = False  # Require all factors vs any one
    ABSTENTION_ALWAYS_EXPLAIN: bool = True  # Always provide reason

    # Confidence features
    CONFIDENCE_PER_PROPOSITION: bool = True
    CONFIDENCE_BREAKDOWN_ENABLED: bool = True  # Expose factor breakdown

    # Citation features
    CITATION_QUALITY_INDICATORS: bool = True
    CITATION_HIGHLIGHTING_ENABLED: bool = True
    CITATION_VALIDATION_ENABLED: bool = True

    # Experimental features
    ENABLE_ADAPTIVE_WEIGHTS: bool = False  # Future: Learn weights from feedback
    ENABLE_CONFIDENCE_CALIBRATION: bool = False  # Future: Calibrate scores
```

**Usage**:
```python
# Client can override via API request
POST /api/v1/answer
{
    "query": "What is the capital of France?",
    "document_ids": [...],
    "citation_config": {
        "inline_format": "detailed",  # [1: doc_name, p.5]
        "highlight_enabled": true,
        "quality_indicators": true
    },
    "abstention_config": {
        "strict_mode": false,
        "low_confidence_threshold": 0.3
    }
}
```

### Resource Limits

**Concurrency Limits**:
- `MAX_CONCURRENT_ENHANCEMENTS = unlimited` (CPU-bound, no external dependencies)
- No Redis/LLM bottlenecks in this step

**Memory Limits**:
- `MAX_ENHANCED_RESPONSE_SIZE_KB = 200` (per response)
- `MAX_PROPOSITION_DETAILS_COUNT = 10` (matches proposition limit)

**Database Limits**:
- `MAX_CONFIDENCE_LOG_SIZE_KB = 50` (JSONB fields)
- Truncate overly large logs before insertion

---

## 7. INTEGRATION DETAILS

### How It Connects to Existing Services

**Integration with Step 11.2 (Verification Service)**:

```python
# CitationConfidenceService wraps VerificationService
class CitationConfidenceService:
    def __init__(self, verification_service: VerificationService, ...):
        self.verification_service = verification_service

    async def generate_enhanced_answer(self, request: AnswerRequest) -> EnhancedAnswerResponse:
        # Get verified answer from Step 11.2
        verified_response = await self.verification_service.verify_answer(request)

        # Enhance with citation & confidence (Step 11.3)
        enhanced_response = await self.enhance(verified_response)

        return enhanced_response
```

**Integration with Step 10.3 (Citation Extraction)**:
- Reuses Citation objects from Step 10.3
- Enriches with quote match info and quality indicators
- No re-extraction needed (citations already in verified_response)

**Data Flow**:
```
User Request → VerificationService (Step 11.2)
    → Returns VerifiedAnswerResponse
    → CitationConfidenceService.enhance() (Step 11.3)
    → Returns EnhancedAnswerResponse
    → API Response to User
```

### API Contracts

**Primary Endpoint: POST /api/v1/answer**

```python
@router.post("/answer", response_model=EnhancedAnswerResponse)
async def generate_answer(
    request: AnswerRequest,
    citation_confidence_service: CitationConfidenceService = Depends(get_citation_confidence_service),
    api_key: str = Depends(verify_api_key)
) -> EnhancedAnswerResponse:
    """
    Generate answer with verification, confidence, and rich citations.

    This is the production-ready endpoint combining:
    - Step 11.1: Baseline answer generation
    - Step 11.2: Chain-of-verification
    - Step 11.3: Citation & confidence enhancement

    Returns EnhancedAnswerResponse with:
    - Abstention handling (if can't answer reliably)
    - Per-proposition confidence scores
    - Enriched citations with quality indicators
    - Comprehensive metadata
    """
```

**Request Model**:

```python
class AnswerRequest(BaseModel):
    query: str  # 1-500 chars, prompt injection validated
    document_ids: Optional[List[UUID]]
    workspace_id: Optional[str]
    top_k: int = 5  # 1-20

    # Step 11.1 options
    temperature: float = 0.2  # 0.0-1.0
    include_citations: bool = True

    # Step 11.2 options
    enable_verification: bool = True

    # Step 11.3 options (NEW)
    citation_config: Optional[CitationConfig] = None
    abstention_config: Optional[AbstentionConfig] = None

class CitationConfig(BaseModel):
    inline_format: Literal["simple", "detailed"] = "simple"
    highlight_enabled: bool = True
    quality_indicators: bool = True

class AbstentionConfig(BaseModel):
    strict_mode: bool = False
    low_confidence_threshold: float = 0.3
```

**Response Model**:

```python
class EnhancedAnswerResponse(VerifiedAnswerResponse):
    """
    Production-ready answer response with full enhancement.

    Extends VerifiedAnswerResponse with:
    - Abstention handling
    - Per-proposition confidence
    - Enriched citations
    """

    # Abstention fields (NEW)
    abstained: bool = False
    abstention_reason: Optional[AbstentionReason] = None
    abstention_message: Optional[str] = None

    # Enhanced metadata (NEW)
    enhanced_metadata: EnhancedMetadata

    # Enriched citations (ENHANCED)
    enriched_citations: List[EnrichedCitation]

class EnhancedMetadata(VerificationMetadata):
    """
    Extends VerificationMetadata with confidence and citation details.
    """

    # Confidence breakdown (NEW)
    confidence_breakdown: ConfidenceBreakdown

    # Per-proposition details (NEW)
    proposition_details: List[PropositionDetail]

    # Abstention factors analysis (NEW)
    abstention_factors: Dict[str, bool]  # {low_confidence: True, high_hallucination: False, ...}

    # Citation validation (NEW)
    citation_validation_errors: List[str]
    total_citations: int
    strong_citations: int
    medium_citations: int
    weak_citations: int

class PropositionDetail(BaseModel):
    """Per-proposition metadata."""
    proposition_id: str
    text: str
    confidence: float  # 0-1
    confidence_breakdown: Dict[str, float]
    has_quote: bool
    quote_similarity: Optional[float]
    verified: bool
    citations: List[int]  # Citation numbers [1, 2, ...]
    quality_indicator: Optional[CitationQuality]

class EnrichedCitation(Citation):
    """Citation with quote match info and quality indicators."""

    # Quote match info (NEW)
    quote_match: Optional[QuoteMatchInfo]
    best_similarity: Optional[float]
    is_exact_quote: bool

    # Quality indicator (NEW)
    quality: CitationQuality  # STRONG, MEDIUM, WEAK

    # Highlighted text (NEW)
    highlighted_passage_text: Optional[str]

    # Inline formatted marker (NEW)
    inline_citation: str  # "[1]" or "[1: doc_name, p.5]"

    # Propositions citing this source (NEW)
    proposition_ids: List[str]

class QuoteMatchInfo(BaseModel):
    """Simplified quote match for API response."""
    matched_text: str
    similarity_score: float
    sentence_index: int
```

**Response Example (Successful Answer)**:

```json
{
    "success": true,
    "abstained": false,
    "answer": "Paris is the capital of France. [1] The city is located in the northern part of the country. [1][2]",
    "verified_answer": "Paris is the capital of France. [1] The city is located in the northern part of the country. [1][2]",
    "propositions": [
        {
            "text": "Paris is the capital of France",
            "index": 0,
            "confidence": 0.95
        },
        {
            "text": "The city is located in the northern part of the country",
            "index": 1,
            "confidence": 0.87
        }
    ],
    "enriched_citations": [
        {
            "citation_number": 1,
            "document_id": "uuid-1",
            "document_name": "France_Guide.pdf",
            "passage_text": "France's capital is Paris, located in the north.",
            "highlighted_passage_text": "France's capital is <mark>Paris</mark>, located in the <mark>north</mark>.",
            "page": 5,
            "relevance_score": 0.95,
            "quality": "STRONG",
            "is_exact_quote": true,
            "best_similarity": 0.97,
            "quote_match": {
                "matched_text": "Paris",
                "similarity_score": 0.97,
                "sentence_index": 0
            },
            "inline_citation": "[1]",
            "proposition_ids": ["p0", "p1"]
        }
    ],
    "confidence": 0.85,
    "verified_confidence": 0.91,
    "can_answer": true,
    "enhanced_metadata": {
        "status": "verified",
        "hallucination_probability": 0.05,
        "propositions_checked": 2,
        "propositions_verified": 2,
        "propositions_removed": 0,
        "confidence_breakdown": {
            "passage_relevance": 0.38,
            "quote_quality": 0.34,
            "verification_agreement": 0.14,
            "citation_count": 0.05
        },
        "proposition_details": [
            {
                "proposition_id": "p0",
                "text": "Paris is the capital of France",
                "confidence": 0.95,
                "confidence_breakdown": {
                    "passage_relevance": 0.95,
                    "quote_quality": 0.97,
                    "verification_agreement": 1.0,
                    "citation_count": 0.33
                },
                "has_quote": true,
                "quote_similarity": 0.97,
                "verified": true,
                "citations": [1],
                "quality_indicator": "STRONG"
            }
        ],
        "abstention_factors": {
            "low_confidence": false,
            "high_hallucination": false,
            "no_evidence": false,
            "verification_failed": false
        },
        "citation_validation_errors": [],
        "total_citations": 1,
        "strong_citations": 1,
        "medium_citations": 0,
        "weak_citations": 0,
        "verification_latency_ms": 4500
    },
    "processing_time_ms": 4750
}
```

**Response Example (Abstention)**:

```json
{
    "success": true,
    "abstained": true,
    "abstention_reason": "low_confidence",
    "abstention_message": "I cannot provide a reliable answer to this question based on the available documents. The information found has low confidence and may not be accurate.",
    "answer": null,
    "verified_answer": null,
    "propositions": [],
    "enriched_citations": [],
    "confidence": 0.15,
    "verified_confidence": 0.18,
    "can_answer": false,
    "enhanced_metadata": {
        "status": "partial",
        "hallucination_probability": 0.45,
        "abstention_factors": {
            "low_confidence": true,
            "high_hallucination": false,
            "no_evidence": true,
            "verification_failed": false
        },
        "confidence_breakdown": {
            "passage_relevance": 0.05,
            "quote_quality": 0.0,
            "verification_agreement": 0.10,
            "citation_count": 0.03
        },
        "total_citations": 0,
        "verification_latency_ms": 4200
    },
    "processing_time_ms": 4380
}
```

### Event Publishing/Consuming

**Event-Driven Architecture**:

```python
# Publish enhancement events for monitoring/analytics
async def _publish_enhancement_event(enhanced_response: EnhancedAnswerResponse):
    event = {
        "event_type": "citation_confidence_completed",
        "timestamp": datetime.utcnow().isoformat(),
        "abstained": enhanced_response.abstained,
        "abstention_reason": enhanced_response.abstention_reason,
        "verified_confidence": enhanced_response.verified_confidence,
        "strong_citations": enhanced_response.enhanced_metadata.strong_citations,
        "proposition_count": len(enhanced_response.propositions),
    }

    # Option 1: Publish to Redis pub/sub (lightweight)
    await redis.publish("enhancement_events", json.dumps(event))

    # Option 2: Future - Kafka for analytics pipeline
    # await kafka_producer.send("enhancement_events", event)
```

**Event Consumers**:
- Monitoring service: Track abstention rates in real-time
- Analytics service: Build confidence trend dashboards
- Alert service: Notify on high abstention rates
- Quality service: Collect low-confidence cases for improvement

### Database Transactions

**Transaction Boundaries**:

```python
async def enhance(self, verified_response: VerifiedAnswerResponse) -> EnhancedAnswerResponse:
    """Enhancement pipeline with transactional guarantees."""

    # No transaction needed for enhancement logic (read-only)
    enhanced_response = await self._enhance_internal(verified_response)

    # Asynchronous confidence log write (background task)
    asyncio.create_task(
        self._save_confidence_log_async(enhanced_response)
    )

    return enhanced_response

async def _save_confidence_log_async(self, enhanced_response: EnhancedAnswerResponse):
    """Background task to write confidence log."""
    async with db_session.begin():
        confidence_log = AnswerConfidenceLog(
            answer_id=enhanced_response.answer_id,
            verification_log_id=enhanced_response.verification_log_id,
            abstained=enhanced_response.abstained,
            abstention_reason=enhanced_response.abstention_reason,
            verified_confidence=enhanced_response.verified_confidence,
            confidence_breakdown=enhanced_response.enhanced_metadata.confidence_breakdown,
            proposition_details=enhanced_response.enhanced_metadata.proposition_details,
            total_citations=enhanced_response.enhanced_metadata.total_citations,
            strong_citations=enhanced_response.enhanced_metadata.strong_citations,
            medium_citations=enhanced_response.enhanced_metadata.medium_citations,
            weak_citations=enhanced_response.enhanced_metadata.weak_citations,
        )
        db_session.add(confidence_log)
        # Commit
```

**Isolation Level**:
- Use `READ COMMITTED` (PostgreSQL default)
- No concurrent updates risk (write-only logs)

---

## 8. TESTING APPROACH

### Unit Test Examples

**Test 1: Abstention Decision Logic**

```python
def test_abstention_low_confidence():
    """Test abstention when verified confidence too low."""
    abstention_service = AbstentionService()

    verified_response = VerifiedAnswerResponse(
        verified_confidence=0.2,  # Below threshold (0.3)
        verification_metadata=VerificationMetadata(
            hallucination_probability=0.1,
            status="verified"
        )
    )

    decision = await abstention_service.should_abstain(verified_response)

    assert decision.should_abstain is True
    assert decision.reason == AbstentionReason.LOW_CONFIDENCE
    assert "low_confidence" in decision.factors

def test_abstention_high_hallucination():
    """Test abstention when hallucination probability too high."""
    abstention_service = AbstentionService()

    verified_response = VerifiedAnswerResponse(
        verified_confidence=0.6,
        verification_metadata=VerificationMetadata(
            hallucination_probability=0.8,  # Above threshold (0.7)
            status="partial"
        )
    )

    decision = await abstention_service.should_abstain(verified_response)

    assert decision.should_abstain is True
    assert decision.reason == AbstentionReason.HIGH_HALLUCINATION

def test_abstention_no_evidence():
    """Test abstention when no quote matches found."""
    abstention_service = AbstentionService()

    verified_response = VerifiedAnswerResponse(
        verified_confidence=0.5,
        verification_metadata=VerificationMetadata(
            hallucination_probability=0.3,
            quote_matches={"p1": [], "p2": []},  # No quotes
            status="partial"
        )
    )

    decision = await abstention_service.should_abstain(verified_response)

    assert decision.should_abstain is True
    assert decision.reason == AbstentionReason.NO_EVIDENCE

def test_no_abstention_when_confident():
    """Test no abstention when all signals positive."""
    abstention_service = AbstentionService()

    verified_response = VerifiedAnswerResponse(
        verified_confidence=0.85,  # High
        verification_metadata=VerificationMetadata(
            hallucination_probability=0.05,  # Low
            quote_matches={"p1": [QuoteMatch(...)]},  # Has quotes
            status="verified"
        )
    )

    decision = await abstention_service.should_abstain(verified_response)

    assert decision.should_abstain is False
```

**Test 2: Confidence Calculation**

```python
@pytest.mark.asyncio
async def test_confidence_calculation_all_factors():
    """Test confidence calculation with all factors present."""
    calculator = ConfidenceCalculator()

    proposition = Proposition(id="p1", content="Paris is the capital of France")
    quote_matches = [
        QuoteMatch(similarity_score=0.95, passage_id="pass1")
    ]
    verification_answer = VerificationAnswer(
        answer="YES - Confirmed in document [1]",
        confidence=0.9
    )
    citations = [
        Citation(relevance_score=0.92, citation_number=1)
    ]

    prop_confidence = await calculator.calculate_proposition_confidence(
        proposition, quote_matches, verification_answer, citations
    )

    assert prop_confidence.confidence >= 0.8  # High confidence expected
    assert prop_confidence.breakdown["passage_relevance"] == 0.92
    assert prop_confidence.breakdown["quote_quality"] == 0.95
    assert prop_confidence.breakdown["verification_agreement"] >= 0.8

@pytest.mark.asyncio
async def test_confidence_calculation_no_quotes():
    """Test confidence calculation when no quote matches."""
    calculator = ConfidenceCalculator()

    proposition = Proposition(id="p1", content="Test claim")
    quote_matches = []  # No quotes
    verification_answer = None
    citations = [Citation(relevance_score=0.6)]

    prop_confidence = await calculator.calculate_proposition_confidence(
        proposition, quote_matches, verification_answer, citations
    )

    # Should be lower due to missing quote and verification
    assert prop_confidence.confidence < 0.5
    assert prop_confidence.breakdown["quote_quality"] == 0.0
```

**Test 3: Citation Quality Scoring**

```python
def test_citation_quality_strong():
    """Test strong quality for exact quote matches."""
    enricher = CitationEnricher()

    citation = Citation(passage_id="p1", relevance_score=0.9)
    quote_matches = [
        QuoteMatch(passage_id="p1", similarity_score=0.97)  # Exact
    ]

    quality = enricher._calculate_citation_quality(citation, quote_matches)

    assert quality == CitationQuality.STRONG

def test_citation_quality_medium():
    """Test medium quality for paraphrased quotes."""
    enricher = CitationEnricher()

    citation = Citation(passage_id="p1", relevance_score=0.8)
    quote_matches = [
        QuoteMatch(passage_id="p1", similarity_score=0.88)  # Paraphrased
    ]

    quality = enricher._calculate_citation_quality(citation, quote_matches)

    assert quality == CitationQuality.MEDIUM

def test_citation_quality_weak():
    """Test weak quality for citations without quotes."""
    enricher = CitationEnricher()

    citation = Citation(passage_id="p1", relevance_score=0.7)
    quote_matches = []  # No quote matches

    quality = enricher._calculate_citation_quality(citation, quote_matches)

    assert quality == CitationQuality.WEAK
```

### Integration Test Setup

**Test Scenario: End-to-End Citation & Confidence Enhancement**

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_enhancement_pipeline():
    """Test complete enhancement flow from verified response to enhanced response."""
    # Setup
    citation_confidence_service = create_citation_confidence_service()

    verified_response = create_sample_verified_response(
        verified_confidence=0.85,
        hallucination_probability=0.1,
        propositions_count=3,
        citations_count=5
    )

    # Execute
    enhanced_response = await citation_confidence_service.enhance(verified_response)

    # Assertions
    assert isinstance(enhanced_response, EnhancedAnswerResponse)
    assert enhanced_response.abstained is False  # Should not abstain with high confidence

    # Check confidence breakdown
    assert enhanced_response.enhanced_metadata.confidence_breakdown is not None
    assert "passage_relevance" in enhanced_response.enhanced_metadata.confidence_breakdown

    # Check proposition details
    assert len(enhanced_response.enhanced_metadata.proposition_details) == 3
    for prop_detail in enhanced_response.enhanced_metadata.proposition_details:
        assert 0.0 <= prop_detail.confidence <= 1.0
        assert prop_detail.confidence_breakdown is not None

    # Check enriched citations
    assert len(enhanced_response.enriched_citations) == 5
    for citation in enhanced_response.enriched_citations:
        assert citation.quality in [CitationQuality.STRONG, CitationQuality.MEDIUM, CitationQuality.WEAK]
        assert citation.inline_citation is not None

    # Check citation validation
    assert len(enhanced_response.enhanced_metadata.citation_validation_errors) == 0

@pytest.mark.integration
@pytest.mark.asyncio
async def test_abstention_integration():
    """Test abstention flow with low confidence response."""
    citation_confidence_service = create_citation_confidence_service()

    verified_response = create_sample_verified_response(
        verified_confidence=0.2,  # Low confidence
        hallucination_probability=0.6,
        propositions_count=1,
        citations_count=0
    )

    # Execute
    enhanced_response = await citation_confidence_service.enhance(verified_response)

    # Should abstain
    assert enhanced_response.abstained is True
    assert enhanced_response.abstention_reason is not None
    assert enhanced_response.abstention_message is not None
    assert enhanced_response.answer is None  # No answer provided

    # Check abstention factors
    assert enhanced_response.enhanced_metadata.abstention_factors["low_confidence"] is True
```

### Performance Benchmarks

**Benchmark Tests**:

```python
@pytest.mark.benchmark
def test_confidence_calculation_performance(benchmark):
    """Benchmark confidence calculation speed."""
    calculator = ConfidenceCalculator()
    proposition = create_sample_proposition()
    quote_matches = create_sample_quote_matches(count=3)
    verification = create_sample_verification_answer()
    citations = create_sample_citations(count=5)

    result = benchmark(
        calculator.calculate_proposition_confidence,
        proposition, quote_matches, verification, citations
    )

    assert benchmark.stats.mean < 0.015  # < 15ms average
    assert result.confidence is not None

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_full_enhancement_latency(benchmark):
    """Benchmark end-to-end enhancement latency."""
    service = create_citation_confidence_service()
    verified_response = create_sample_verified_response()

    result = await benchmark(service.enhance, verified_response)

    # Target: <200ms p95 latency
    assert result is not None
    # Note: benchmark.stats available after run
```

### Manual Verification Steps

**Test Dataset**: Golden test set with expected outcomes

```markdown
# Golden Test Cases for Manual Verification

1. **High Confidence Answer**
   - Verified confidence: 0.85
   - Expected: No abstention, all propositions have high confidence
   - Expected citations: All STRONG quality

2. **Medium Confidence Answer**
   - Verified confidence: 0.55
   - Expected: No abstention, mixed proposition confidences
   - Expected citations: Mix of MEDIUM and STRONG

3. **Low Confidence - Should Abstain**
   - Verified confidence: 0.25
   - Expected: Abstain with reason "low_confidence"
   - Expected: Clear abstention message

4. **High Hallucination - Should Abstain**
   - Verified confidence: 0.6, hallucination probability: 0.8
   - Expected: Abstain with reason "high_hallucination"

5. **No Evidence - Should Abstain**
   - Verified confidence: 0.5, no quote matches
   - Expected: Abstain with reason "no_evidence"

6. **Citation Validation Error**
   - Answer contains [3] but only 2 citations provided
   - Expected: Validation error in metadata, logged warning
```

**Manual Testing Checklist**:
- [ ] Verify abstention logic triggers correctly (test all 4 factors)
- [ ] Check per-proposition confidence scores are reasonable
- [ ] Confirm citation quality indicators match quote similarity
- [ ] Test highlighted text rendering (no XSS vulnerabilities)
- [ ] Validate inline citation formatting (simple vs detailed)
- [ ] Measure latency: Should be <200ms additional
- [ ] Test with edge cases: 0 citations, 0 propositions, all weak citations

---

## 9. MONITORING

### Metrics Collected

**Primary Metrics**:

```python
# Prometheus metrics
abstention_rate = Gauge(
    "abstention_rate",
    "Percentage of answers abstained",
    ["abstention_reason"]
)

avg_confidence_score = Histogram(
    "avg_confidence_score",
    "Average verified confidence distribution",
    buckets=[0, 0.2, 0.4, 0.6, 0.8, 1.0]
)

citation_quality_distribution = Counter(
    "citation_quality_total",
    "Count of citations by quality",
    ["quality"]  # STRONG, MEDIUM, WEAK
)

confidence_calculation_latency_ms = Histogram(
    "confidence_calculation_latency_ms",
    "Confidence calculation latency",
    buckets=[5, 10, 20, 50, 100, 200]
)

enhancement_requests_total = Counter(
    "enhancement_requests_total",
    "Total enhancement requests",
    ["abstained"]
)
```

**Secondary Metrics**:
- `proposition_avg_confidence`: Average per-proposition confidence
- `citation_validation_errors_total`: Count of validation errors
- `abstention_by_factor`: Breakdown of abstention reasons
- `strong_citations_ratio`: Percentage of STRONG quality citations

### Log Entries Added

**Structured Logs**:

```python
# Enhancement start
logger.info(
    "Starting citation & confidence enhancement",
    extra={
        "request_id": request_id,
        "verified_confidence": verified_response.verified_confidence,
        "hallucination_probability": verified_response.verification_metadata.hallucination_probability,
    }
)

# Abstention decision
logger.warning(
    "Abstention triggered",
    extra={
        "stage": "abstention_decision",
        "reason": abstention_decision.reason,
        "factors": abstention_decision.factors,
        "verified_confidence": verified_response.verified_confidence,
    }
)

# Enhancement completion
logger.info(
    "Citation & confidence enhancement completed",
    extra={
        "stage": "enhancement_complete",
        "abstained": enhanced_response.abstained,
        "avg_confidence": avg_confidence,
        "strong_citations": enhanced_metadata.strong_citations,
        "total_citations": enhanced_metadata.total_citations,
        "latency_ms": elapsed,
    }
)

# Citation validation errors
if validation_errors:
    logger.error(
        "Citation validation errors detected",
        extra={
            "stage": "citation_validation",
            "errors": validation_errors,
            "answer_id": enhanced_response.answer_id,
        }
    )
```

### Health Check Endpoints

**New Health Check**: `/api/v1/health/citation-confidence`

```python
@router.get("/health/citation-confidence")
async def citation_confidence_health_check(
    citation_confidence_service: CitationConfidenceService = Depends(get_citation_confidence_service)
) -> Dict[str, Any]:
    """
    Health check for citation & confidence service.

    Returns:
    {
        "status": "healthy" | "degraded" | "unhealthy",
        "components": {
            "abstention_service": "healthy",
            "confidence_calculator": "healthy",
            "citation_enricher": "healthy",
            "metadata_assembler": "healthy"
        },
        "metrics": {
            "abstention_rate": 0.12,
            "avg_confidence": 0.78,
            "avg_latency_ms": 145,
            "strong_citations_ratio": 0.65
        }
    }
    """
    health_status = {
        "status": "healthy",
        "components": {},
        "metrics": {}
    }

    # Check abstention service
    try:
        test_decision = await citation_confidence_service.abstention_service.health_check()
        health_status["components"]["abstention_service"] = "healthy"
    except Exception:
        health_status["components"]["abstention_service"] = "unhealthy"
        health_status["status"] = "degraded"

    # Retrieve metrics from Redis
    health_status["metrics"] = await get_enhancement_metrics()

    return health_status
```

### Alert Thresholds

**Critical Alerts** (PagerDuty/email):

```yaml
# alert_rules.yml
- alert: HighAbstentionRate
  expr: rate(abstention_rate[15m]) > 0.5
  for: 30m
  labels:
    severity: critical
  annotations:
    summary: "High abstention rate detected"
    description: ">50% of answers abstained in last 15 minutes"

- alert: CitationConfidenceServiceDown
  expr: up{job="citation_confidence_service"} == 0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Citation & confidence service is down"

- alert: VeryLowAverageConfidence
  expr: avg(avg_confidence_score) < 0.3
  for: 30m
  labels:
    severity: critical
  annotations:
    summary: "Average confidence very low (<0.3)"
```

**Warning Alerts** (Slack/dashboard):

```yaml
- alert: LowStrongCitationRatio
  expr: rate(citation_quality_total{quality="STRONG"}[15m]) / rate(citation_quality_total[15m]) < 0.3
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "Low ratio of strong citations (<30%)"

- alert: EnhancementLatencyHigh
  expr: histogram_quantile(0.95, confidence_calculation_latency_ms) > 300
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Enhancement p95 latency >300ms"

- alert: CitationValidationErrors
  expr: rate(citation_validation_errors_total[5m]) > 5
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High rate of citation validation errors"
```

---

## 10. CODE SNIPPETS

### Main Class Structure

```python
# backend/app/services/citation_confidence_service.py

from typing import Dict, List, Optional
import asyncio
from datetime import datetime

from app.services.citation_confidence.abstention_service import AbstentionService
from app.services.citation_confidence.confidence_calculator import ConfidenceCalculator
from app.services.citation_confidence.citation_enricher import CitationEnricher
from app.services.citation_confidence.metadata_assembler import MetadataAssembler
from app.schemas.verification import VerifiedAnswerResponse
from app.schemas.citation_confidence import (
    EnhancedAnswerResponse,
    AbstentionDecision,
    PropConfidence,
    EnrichedCitation,
    EnhancedMetadata
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CitationConfidenceService:
    """
    Citation & Confidence Enhancement Service.

    Implements a 4-stage pipeline:
    1. Abstention decision (should we answer?)
    2. Granular confidence calculation (how confident per claim?)
    3. Citation enrichment (link quotes to citations, quality indicators)
    4. Enhanced metadata assembly (comprehensive response metadata)

    Builds on Step 11.2 verification to provide production-ready answers.
    """

    def __init__(
        self,
        abstention_service: AbstentionService,
        confidence_calculator: ConfidenceCalculator,
        citation_enricher: CitationEnricher,
        metadata_assembler: MetadataAssembler,
        cache: Redis
    ):
        self.abstention_service = abstention_service
        self.confidence_calculator = confidence_calculator
        self.citation_enricher = citation_enricher
        self.metadata_assembler = metadata_assembler
        self.cache = cache

    async def enhance(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> EnhancedAnswerResponse:
        """
        Execute full citation & confidence enhancement pipeline.

        Args:
            verified_response: VerifiedAnswerResponse from Step 11.2

        Returns:
            EnhancedAnswerResponse with abstention, confidence, and rich citations

        Performance:
            - Latency: ~100-200ms (CPU-bound operations)
            - No LLM calls (all local computation)
            - Cacheable at response level
        """
        start_time = datetime.utcnow()
        request_id = verified_response.request_id

        logger.info(
            "Starting citation & confidence enhancement",
            extra={
                "request_id": request_id,
                "verified_confidence": verified_response.verified_confidence,
            }
        )

        # Check cache
        cache_key = self._generate_cache_key(verified_response)
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            logger.info("Enhancement cache hit", extra={"request_id": request_id})
            return cached_result

        try:
            # Stage 1: Abstention decision
            abstention_result = await self._process_abstention(verified_response)
            if abstention_result:
                # Should abstain - return early
                await self._save_to_cache(cache_key, abstention_result)
                return abstention_result

            # Stage 2: Calculate per-proposition confidence
            prop_confidences = await self._calculate_confidences(verified_response)

            # Stage 3: Enrich citations with quote matches and quality
            enriched_citations = await self._enrich_citations(
                verified_response,
                prop_confidences
            )

            # Stage 4: Build enhanced metadata
            enhanced_metadata = await self._build_enhanced_metadata(
                verified_response,
                prop_confidences,
                enriched_citations,
                abstention_decision=AbstentionDecision(should_abstain=False)
            )

            # Build final enhanced response
            enhanced_response = EnhancedAnswerResponse(
                **verified_response.dict(exclude={"verification_metadata"}),
                abstained=False,
                enriched_citations=enriched_citations,
                enhanced_metadata=enhanced_metadata
            )

            # Cache result
            await self._save_to_cache(cache_key, enhanced_response)

            # Async confidence log write
            asyncio.create_task(
                self._save_confidence_log_async(enhanced_response)
            )

            # Record metrics
            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._record_metrics(enhanced_response, elapsed_ms)

            logger.info(
                "Citation & confidence enhancement completed",
                extra={
                    "request_id": request_id,
                    "abstained": False,
                    "avg_confidence": enhanced_metadata.confidence_breakdown.overall,
                    "strong_citations": enhanced_metadata.strong_citations,
                    "latency_ms": elapsed_ms,
                }
            )

            return enhanced_response

        except Exception as e:
            logger.error(
                "Enhancement failed",
                extra={"request_id": request_id, "error": str(e)}
            )
            # Fallback: Return verified response without enhancement
            return self._fallback_to_verified(verified_response)

    async def _process_abstention(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> Optional[EnhancedAnswerResponse]:
        """
        Stage 1: Check if should abstain and return abstention response if yes.

        Returns:
            EnhancedAnswerResponse if should abstain, None otherwise
        """
        abstention_decision = await self.abstention_service.should_abstain(
            verified_response
        )

        if not abstention_decision.should_abstain:
            return None

        # Build abstention response
        logger.warning(
            "Abstention triggered",
            extra={
                "reason": abstention_decision.reason,
                "factors": abstention_decision.factors,
                "confidence": abstention_decision.confidence,
            }
        )

        abstention_message = self._build_abstention_message(abstention_decision)

        # Build minimal enhanced metadata for abstention
        enhanced_metadata = EnhancedMetadata(
            **verified_response.verification_metadata.dict(),
            abstention_factors={
                "low_confidence": "low_confidence" in abstention_decision.factors,
                "high_hallucination": "high_hallucination" in abstention_decision.factors,
                "no_evidence": "no_evidence" in abstention_decision.factors,
                "verification_failed": "verification_failed" in abstention_decision.factors,
            },
            confidence_breakdown={},
            proposition_details=[],
            total_citations=0,
            strong_citations=0,
            medium_citations=0,
            weak_citations=0,
        )

        return EnhancedAnswerResponse(
            **verified_response.dict(exclude={"answer", "verified_answer", "verification_metadata"}),
            abstained=True,
            abstention_reason=abstention_decision.reason,
            abstention_message=abstention_message,
            answer=None,
            verified_answer=None,
            enriched_citations=[],
            enhanced_metadata=enhanced_metadata
        )

    async def _calculate_confidences(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> Dict[str, PropConfidence]:
        """
        Stage 2: Calculate per-proposition confidence scores.

        Returns:
            Dict mapping proposition_id → PropConfidence
        """
        logger.debug("Calculating proposition confidences")

        prop_confidences = await self.confidence_calculator.calculate_all(
            verified_response
        )

        logger.debug(
            "Confidence calculation completed",
            extra={
                "propositions_count": len(prop_confidences),
                "avg_confidence": sum(pc.confidence for pc in prop_confidences.values()) / len(prop_confidences) if prop_confidences else 0,
            }
        )

        return prop_confidences

    async def _enrich_citations(
        self,
        verified_response: VerifiedAnswerResponse,
        prop_confidences: Dict[str, PropConfidence]
    ) -> List[EnrichedCitation]:
        """
        Stage 3: Enrich citations with quote matches and quality indicators.

        Returns:
            List of EnrichedCitation objects
        """
        logger.debug("Enriching citations")

        enriched_citations = await self.citation_enricher.enrich_citations(
            citations=verified_response.citations,
            quote_matches=verified_response.verification_metadata.quote_matches,
            propositions=verified_response.propositions
        )

        # Count citation quality distribution
        quality_counts = {
            "STRONG": sum(1 for c in enriched_citations if c.quality == CitationQuality.STRONG),
            "MEDIUM": sum(1 for c in enriched_citations if c.quality == CitationQuality.MEDIUM),
            "WEAK": sum(1 for c in enriched_citations if c.quality == CitationQuality.WEAK),
        }

        logger.debug(
            "Citation enrichment completed",
            extra={
                "total_citations": len(enriched_citations),
                **quality_counts,
            }
        )

        return enriched_citations

    async def _build_enhanced_metadata(
        self,
        verified_response: VerifiedAnswerResponse,
        prop_confidences: Dict[str, PropConfidence],
        enriched_citations: List[EnrichedCitation],
        abstention_decision: AbstentionDecision
    ) -> EnhancedMetadata:
        """
        Stage 4: Assemble comprehensive enhanced metadata.

        Returns:
            EnhancedMetadata with all enhancement details
        """
        logger.debug("Building enhanced metadata")

        enhanced_metadata = await self.metadata_assembler.build(
            verified_response=verified_response,
            prop_confidences=prop_confidences,
            enriched_citations=enriched_citations,
            abstention_decision=abstention_decision
        )

        return enhanced_metadata

    def _build_abstention_message(self, decision: AbstentionDecision) -> str:
        """Build user-facing abstention message."""
        messages = {
            AbstentionReason.LOW_CONFIDENCE: (
                "I cannot provide a reliable answer to this question based on the available documents. "
                "The information found has low confidence and may not be accurate."
            ),
            AbstentionReason.HIGH_HALLUCINATION: (
                "I cannot provide a reliable answer to this question. "
                "The information found shows signs of potential inaccuracies or hallucinations."
            ),
            AbstentionReason.NO_EVIDENCE: (
                "I cannot find sufficient evidence in the provided documents to answer this question reliably."
            ),
            AbstentionReason.VERIFICATION_FAILED: (
                "I cannot provide a reliable answer because the verification process encountered errors."
            ),
        }

        return messages.get(decision.reason, "I cannot provide a reliable answer to this question.")

    def _fallback_to_verified(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> EnhancedAnswerResponse:
        """Return verified response without enhancement on failure."""
        return EnhancedAnswerResponse(
            **verified_response.dict(),
            abstained=False,
            enriched_citations=[EnrichedCitation.from_citation(c) for c in verified_response.citations],
            enhanced_metadata=EnhancedMetadata(
                **verified_response.verification_metadata.dict(),
                confidence_breakdown={},
                proposition_details=[],
                abstention_factors={},
                total_citations=len(verified_response.citations),
                strong_citations=0,
                medium_citations=0,
                weak_citations=0,
            )
        )

    async def _save_confidence_log_async(
        self,
        enhanced_response: EnhancedAnswerResponse
    ):
        """Background task to write confidence log to database."""
        try:
            async with db_session.begin():
                confidence_log = AnswerConfidenceLog(
                    answer_id=enhanced_response.answer_id,
                    verification_log_id=enhanced_response.verification_log_id,
                    abstained=enhanced_response.abstained,
                    abstention_reason=enhanced_response.abstention_reason,
                    abstention_confidence=enhanced_response.enhanced_metadata.abstention_factors.get("confidence"),
                    verified_confidence=enhanced_response.verified_confidence,
                    confidence_breakdown=enhanced_response.enhanced_metadata.confidence_breakdown,
                    proposition_details=enhanced_response.enhanced_metadata.proposition_details,
                    total_citations=enhanced_response.enhanced_metadata.total_citations,
                    strong_citations=enhanced_response.enhanced_metadata.strong_citations,
                    medium_citations=enhanced_response.enhanced_metadata.medium_citations,
                    weak_citations=enhanced_response.enhanced_metadata.weak_citations,
                    citation_validation_errors=enhanced_response.enhanced_metadata.citation_validation_errors,
                )
                db_session.add(confidence_log)
                # Commit

            logger.debug("Confidence log saved successfully")

        except Exception as e:
            logger.error(f"Failed to save confidence log: {e}")
            # Non-blocking - don't fail request
```

### One Critical Function

```python
# backend/app/services/citation_confidence/confidence_calculator.py

from typing import Dict, List, Optional
from dataclasses import dataclass

from app.schemas.answer import Proposition, Citation
from app.schemas.verification import QuoteMatch, VerificationAnswer, VerifiedAnswerResponse
from app.schemas.citation_confidence import PropConfidence, ConfidenceBreakdown
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ConfidenceWeights:
    """Weights for confidence calculation factors."""
    passage_relevance: float = 0.40
    quote_quality: float = 0.35
    verification_agreement: float = 0.15
    citation_count: float = 0.10

    def __post_init__(self):
        """Validate weights sum to 1.0."""
        total = (
            self.passage_relevance +
            self.quote_quality +
            self.verification_agreement +
            self.citation_count
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


class ConfidenceCalculator:
    """
    Granular confidence calculator for propositions and overall answer.

    Implements weighted 4-factor algorithm:
    1. Passage relevance (40%): Best rerank score from Step 10.2
    2. Quote quality (35%): Best quote similarity score from quote matching
    3. Verification agreement (15%): Independent verification confirms claim
    4. Citation count (10%): Number of supporting sources (diversity)
    """

    def __init__(self, weights: Optional[ConfidenceWeights] = None):
        self.weights = weights or ConfidenceWeights()
        logger.info(
            "ConfidenceCalculator initialized",
            extra={"weights": self.weights}
        )

    async def calculate_all(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> Dict[str, PropConfidence]:
        """
        Calculate confidence for all propositions.

        Args:
            verified_response: VerifiedAnswerResponse from Step 11.2

        Returns:
            Dict mapping proposition_id → PropConfidence

        Complexity: O(P) where P = propositions (3-5 typically)
        Time: ~50-80ms for 3-5 propositions
        """
        logger.debug(
            "Calculating confidence for all propositions",
            extra={"propositions_count": len(verified_response.propositions)}
        )

        prop_confidences = {}

        for proposition in verified_response.propositions:
            # Get quote matches for this proposition
            quote_matches = verified_response.verification_metadata.quote_matches.get(
                proposition.id, []
            )

            # Get verification answer for this proposition (if available)
            verification_answer = self._find_verification_answer(
                proposition,
                verified_response.verification_metadata.verification_answers
            )

            # Get citations for this proposition
            citations = [
                c for c in verified_response.citations
                if proposition.id in getattr(c, 'proposition_ids', [])
            ]

            # Calculate confidence
            prop_confidence = await self.calculate_proposition_confidence(
                proposition=proposition,
                quote_matches=quote_matches,
                verification_answer=verification_answer,
                citations=citations,
                hallucination_probability=verified_response.verification_metadata.hallucination_probability
            )

            prop_confidences[proposition.id] = prop_confidence

        logger.debug(
            "Confidence calculation completed",
            extra={
                "avg_confidence": sum(pc.confidence for pc in prop_confidences.values()) / len(prop_confidences) if prop_confidences else 0
            }
        )

        return prop_confidences

    async def calculate_proposition_confidence(
        self,
        proposition: Proposition,
        quote_matches: List[QuoteMatch],
        verification_answer: Optional[VerificationAnswer],
        citations: List[Citation],
        hallucination_probability: float = 0.0
    ) -> PropConfidence:
        """
        Calculate confidence for a single proposition using 4-factor weighted algorithm.

        Algorithm:
        1. Passage Relevance (40%):
           - Use best (max) relevance score from citations
           - Range: [0, 1]
           - Rationale: Best passage indicates strongest evidence

        2. Quote Match Quality (35%):
           - Use best (max) similarity score from quote matches
           - Range: [0, 1]
           - Rationale: Exact quotes = strong evidence

        3. Verification Agreement (15%):
           - 1.0 if verification confirms (YES, agrees)
           - 0.5 if neutral (CANNOT DETERMINE)
           - 0.0 if verification denies (NO, disagrees)
           - Rationale: Independent verification validates claim

        4. Citation Count (10%):
           - Score = min(1.0, len(citations) / 3.0)
           - Range: [0, 1], capped at 3 citations
           - Rationale: Multiple sources increase confidence, but diminishing returns

        Final confidence = weighted_sum(factors) * (1 - hallucination_probability)

        Args:
            proposition: Proposition to score
            quote_matches: List of quote matches for this proposition
            verification_answer: Verification answer for this proposition (optional)
            citations: List of citations supporting this proposition
            hallucination_probability: Overall hallucination probability from Step 11.2

        Returns:
            PropConfidence with score and factor breakdown

        Complexity: O(C + Q) where C = citations, Q = quote matches
        Time: ~5-10ms per proposition
        """
        # Factor 1: Passage Relevance (40%)
        passage_relevance = self._calculate_passage_relevance_score(citations)

        # Factor 2: Quote Match Quality (35%)
        quote_quality = self._calculate_quote_match_score(quote_matches)

        # Factor 3: Verification Agreement (15%)
        verif_agreement = self._calculate_verification_agreement_score(
            proposition,
            verification_answer
        )

        # Factor 4: Citation Count (10%)
        cite_count_score = self._calculate_citation_count_score(citations)

        # Weighted sum
        raw_confidence = (
            self.weights.passage_relevance * passage_relevance +
            self.weights.quote_quality * quote_quality +
            self.weights.verification_agreement * verif_agreement +
            self.weights.citation_count * cite_count_score
        )

        # Apply hallucination penalty
        final_confidence = raw_confidence * (1 - hallucination_probability)

        # Build breakdown
        breakdown = {
            "passage_relevance": round(passage_relevance, 3),
            "quote_quality": round(quote_quality, 3),
            "verification_agreement": round(verif_agreement, 3),
            "citation_count": round(cite_count_score, 3),
        }

        logger.debug(
            "Proposition confidence calculated",
            extra={
                "proposition_id": proposition.id,
                "confidence": round(final_confidence, 3),
                **breakdown,
            }
        )

        return PropConfidence(
            proposition_id=proposition.id,
            confidence=round(final_confidence, 3),
            breakdown=breakdown
        )

    def _calculate_passage_relevance_score(self, citations: List[Citation]) -> float:
        """
        Factor 1: Passage relevance score.

        Use maximum relevance score from all citations.
        """
        if not citations:
            return 0.0

        relevance_scores = [c.relevance_score for c in citations if c.relevance_score]
        if not relevance_scores:
            return 0.0

        return max(relevance_scores)

    def _calculate_quote_match_score(self, quote_matches: List[QuoteMatch]) -> float:
        """
        Factor 2: Quote match quality score.

        Use maximum similarity score from all quote matches.
        """
        if not quote_matches:
            return 0.0

        similarity_scores = [qm.similarity_score for qm in quote_matches]
        if not similarity_scores:
            return 0.0

        return max(similarity_scores)

    def _calculate_verification_agreement_score(
        self,
        proposition: Proposition,
        verification_answer: Optional[VerificationAnswer]
    ) -> float:
        """
        Factor 3: Verification agreement score.

        Scoring:
        - 1.0: Verification confirms (contains "YES", "CORRECT", "TRUE")
        - 0.5: Neutral (contains "CANNOT DETERMINE", fallback answer)
        - 0.0: Verification denies (contains "NO", "INCORRECT", "FALSE")
        """
        if not verification_answer or not verification_answer.answer:
            return 0.5  # Neutral if no verification

        answer_lower = verification_answer.answer.lower()

        # Check for confirmation
        if any(keyword in answer_lower for keyword in ["yes", "correct", "true", "confirmed"]):
            return 1.0

        # Check for denial
        if any(keyword in answer_lower for keyword in ["no", "incorrect", "false", "not mentioned"]):
            return 0.0

        # Check for neutral/uncertain
        if any(keyword in answer_lower for keyword in ["cannot determine", "unsure", "unclear"]):
            return 0.5

        # Default: Use word overlap as proxy for agreement
        prop_words = set(proposition.content.lower().split())
        verif_words = set(answer_lower.split())
        overlap = len(prop_words & verif_words) / len(prop_words) if prop_words else 0

        # Scale overlap to [0, 1]
        return min(1.0, overlap * 2)  # Generous scaling

    def _calculate_citation_count_score(self, citations: List[Citation]) -> float:
        """
        Factor 4: Citation count score.

        Score = min(1.0, len(citations) / 3.0)

        Rationale:
        - 1 citation: 0.33
        - 2 citations: 0.67
        - 3+ citations: 1.0 (capped)

        Diminishing returns after 3 sources.
        """
        return min(1.0, len(citations) / 3.0)

    def _find_verification_answer(
        self,
        proposition: Proposition,
        verification_answers: List[VerificationAnswer]
    ) -> Optional[VerificationAnswer]:
        """Find verification answer corresponding to proposition."""
        # Match by target_proposition_id from verification question
        for verif_answer in verification_answers:
            if verif_answer.question.target_proposition_id == proposition.id:
                return verif_answer

        return None

    def aggregate_to_overall_confidence(
        self,
        prop_confidences: Dict[str, PropConfidence]
    ) -> float:
        """
        Aggregate per-proposition confidences to overall verified confidence.

        Strategy: Weighted average (default)

        Alternative strategies:
        - Minimum (conservative): Use lowest proposition confidence
        - Probabilistic: 1 - product(1 - conf_i) for all i

        Returns:
            Overall confidence score [0, 1]
        """
        if not prop_confidences:
            return 0.0

        # Weighted average (all props equal weight)
        avg_confidence = sum(pc.confidence for pc in prop_confidences.values()) / len(prop_confidences)

        return round(avg_confidence, 3)
```

### Error Handling Pattern

```python
# backend/app/services/citation_confidence/abstention_service.py

from typing import List
from enum import Enum

from app.schemas.verification import VerifiedAnswerResponse
from app.schemas.citation_confidence import AbstentionDecision, AbstentionReason
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AbstentionService:
    """
    Multi-factor abstention decision engine.

    Decides whether to abstain from answering based on:
    1. Low confidence
    2. High hallucination probability
    3. No supporting evidence (quote matches)
    4. Verification failed

    Abstention philosophy: Better to say "I don't know" than provide wrong answer.
    """

    def __init__(self):
        self.low_confidence_threshold = settings.LOW_CONFIDENCE_THRESHOLD
        self.high_hallucination_threshold = settings.HIGH_HALLUCINATION_THRESHOLD
        logger.info(
            "AbstentionService initialized",
            extra={
                "low_confidence_threshold": self.low_confidence_threshold,
                "high_hallucination_threshold": self.high_hallucination_threshold,
            }
        )

    async def should_abstain(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> AbstentionDecision:
        """
        Multi-factor abstention decision.

        Decision Logic:
        - If ANY critical factor triggered → ABSTAIN
        - Categorize primary reason
        - Calculate abstention confidence (how sure we can't answer)

        Args:
            verified_response: VerifiedAnswerResponse from Step 11.2

        Returns:
            AbstentionDecision with should_abstain, reason, factors

        Complexity: O(P) where P = propositions
        Time: <10ms
        """
        factors_triggered = []

        # Factor 1: Low confidence check
        try:
            if self._check_low_confidence(verified_response):
                factors_triggered.append("low_confidence")
                logger.debug(
                    "Low confidence factor triggered",
                    extra={"verified_confidence": verified_response.verified_confidence}
                )
        except Exception as e:
            logger.error(f"Low confidence check failed: {e}")
            # Conservative: Treat error as triggered
            factors_triggered.append("low_confidence")

        # Factor 2: High hallucination check
        try:
            if self._check_high_hallucination(verified_response):
                factors_triggered.append("high_hallucination")
                logger.debug(
                    "High hallucination factor triggered",
                    extra={"hallucination_probability": verified_response.verification_metadata.hallucination_probability}
                )
        except Exception as e:
            logger.error(f"High hallucination check failed: {e}")
            factors_triggered.append("high_hallucination")

        # Factor 3: No evidence check
        try:
            if self._check_no_quotes(verified_response):
                factors_triggered.append("no_evidence")
                logger.debug("No evidence factor triggered")
        except Exception as e:
            logger.error(f"No evidence check failed: {e}")
            factors_triggered.append("no_evidence")

        # Factor 4: Verification failed check
        try:
            if self._check_verification_failed(verified_response):
                factors_triggered.append("verification_failed")
                logger.debug("Verification failed factor triggered")
        except Exception as e:
            logger.error(f"Verification failed check failed: {e}")
            factors_triggered.append("verification_failed")

        # Decision
        if factors_triggered:
            reason = self._categorize_reason(factors_triggered)
            confidence = self._calculate_abstention_confidence(factors_triggered)

            logger.info(
                "Abstention decision: ABSTAIN",
                extra={
                    "reason": reason,
                    "factors": factors_triggered,
                    "confidence": confidence,
                }
            )

            return AbstentionDecision(
                should_abstain=True,
                reason=reason,
                factors=factors_triggered,
                confidence=confidence
            )
        else:
            logger.debug("Abstention decision: ANSWER")
            return AbstentionDecision(should_abstain=False)

    def _check_low_confidence(self, verified_response: VerifiedAnswerResponse) -> bool:
        """Check if verified confidence below threshold."""
        return (
            verified_response.verified_confidence is not None and
            verified_response.verified_confidence < self.low_confidence_threshold
        )

    def _check_high_hallucination(self, verified_response: VerifiedAnswerResponse) -> bool:
        """Check if hallucination probability above threshold."""
        return (
            verified_response.verification_metadata.hallucination_probability is not None and
            verified_response.verification_metadata.hallucination_probability > self.high_hallucination_threshold
        )

    def _check_no_quotes(self, verified_response: VerifiedAnswerResponse) -> bool:
        """Check if all propositions lack quote matches."""
        quote_matches = verified_response.verification_metadata.quote_matches
        if not quote_matches:
            return True

        # Check if all propositions have empty quote lists
        return all(len(matches) == 0 for matches in quote_matches.values())

    def _check_verification_failed(self, verified_response: VerifiedAnswerResponse) -> bool:
        """Check if verification process failed."""
        return verified_response.verification_metadata.status == "failed"

    def _categorize_reason(self, factors_triggered: List[str]) -> AbstentionReason:
        """
        Categorize abstention reason from triggered factors.

        Priority order:
        1. verification_failed (most critical)
        2. high_hallucination
        3. low_confidence
        4. no_evidence
        """
        if "verification_failed" in factors_triggered:
            return AbstentionReason.VERIFICATION_FAILED
        elif "high_hallucination" in factors_triggered:
            return AbstentionReason.HIGH_HALLUCINATION
        elif "low_confidence" in factors_triggered:
            return AbstentionReason.LOW_CONFIDENCE
        elif "no_evidence" in factors_triggered:
            return AbstentionReason.NO_EVIDENCE
        else:
            # Should not reach here
            return AbstentionReason.LOW_CONFIDENCE

    def _calculate_abstention_confidence(self, factors_triggered: List[str]) -> float:
        """
        Calculate confidence in abstention decision.

        More factors triggered = higher confidence in abstention.

        Score:
        - 1 factor: 0.6
        - 2 factors: 0.8
        - 3+ factors: 1.0
        """
        count = len(factors_triggered)
        if count >= 3:
            return 1.0
        elif count == 2:
            return 0.8
        elif count == 1:
            return 0.6
        else:
            return 0.0  # No abstention
```

### Test Example

```python
# backend/tests/unit/services/test_citation_confidence_service.py

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from app.services.citation_confidence_service import CitationConfidenceService
from app.services.citation_confidence.abstention_service import AbstentionService
from app.services.citation_confidence.confidence_calculator import ConfidenceCalculator
from app.services.citation_confidence.citation_enricher import CitationEnricher
from app.services.citation_confidence.metadata_assembler import MetadataAssembler
from app.schemas.verification import VerifiedAnswerResponse, VerificationMetadata
from app.schemas.citation_confidence import (
    EnhancedAnswerResponse,
    AbstentionDecision,
    AbstentionReason,
    CitationQuality
)


class TestCitationConfidenceService:
    """Test suite for citation & confidence enhancement service."""

    @pytest.fixture
    def mock_abstention_service(self):
        """Mock abstention service."""
        mock = AsyncMock()
        mock.should_abstain.return_value = AbstentionDecision(should_abstain=False)
        return mock

    @pytest.fixture
    def mock_confidence_calculator(self):
        """Mock confidence calculator."""
        mock = AsyncMock()
        mock.calculate_all.return_value = {
            "p1": PropConfidence(
                proposition_id="p1",
                confidence=0.92,
                breakdown={
                    "passage_relevance": 0.95,
                    "quote_quality": 0.97,
                    "verification_agreement": 1.0,
                    "citation_count": 0.33,
                }
            )
        }
        return mock

    @pytest.fixture
    def mock_citation_enricher(self):
        """Mock citation enricher."""
        mock = AsyncMock()
        mock.enrich_citations.return_value = [
            EnrichedCitation(
                citation_number=1,
                document_name="test.pdf",
                quality=CitationQuality.STRONG,
                is_exact_quote=True,
                best_similarity=0.97,
            )
        ]
        return mock

    @pytest.fixture
    def mock_metadata_assembler(self):
        """Mock metadata assembler."""
        mock = AsyncMock()
        mock.build.return_value = EnhancedMetadata(
            status="verified",
            confidence_breakdown={"overall": 0.92},
            proposition_details=[],
            abstention_factors={},
            total_citations=1,
            strong_citations=1,
            medium_citations=0,
            weak_citations=0,
        )
        return mock

    @pytest.fixture
    def citation_confidence_service(
        self,
        mock_abstention_service,
        mock_confidence_calculator,
        mock_citation_enricher,
        mock_metadata_assembler
    ):
        """Create citation confidence service with mocked dependencies."""
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None  # No cache hits

        return CitationConfidenceService(
            abstention_service=mock_abstention_service,
            confidence_calculator=mock_confidence_calculator,
            citation_enricher=mock_citation_enricher,
            metadata_assembler=mock_metadata_assembler,
            cache=mock_cache
        )

    @pytest.mark.asyncio
    async def test_enhance_success(self, citation_confidence_service):
        """Test successful enhancement pipeline."""
        verified_response = create_sample_verified_response(
            verified_confidence=0.85,
            hallucination_probability=0.1
        )

        result = await citation_confidence_service.enhance(verified_response)

        # Assertions
        assert isinstance(result, EnhancedAnswerResponse)
        assert result.abstained is False
        assert result.enriched_citations is not None
        assert result.enhanced_metadata is not None
        assert result.enhanced_metadata.confidence_breakdown is not None

    @pytest.mark.asyncio
    async def test_enhance_with_abstention(
        self,
        citation_confidence_service,
        mock_abstention_service
    ):
        """Test enhancement with abstention triggered."""
        # Mock abstention decision
        mock_abstention_service.should_abstain.return_value = AbstentionDecision(
            should_abstain=True,
            reason=AbstentionReason.LOW_CONFIDENCE,
            factors=["low_confidence"],
            confidence=0.8
        )

        verified_response = create_sample_verified_response(
            verified_confidence=0.2  # Low confidence
        )

        result = await citation_confidence_service.enhance(verified_response)

        # Should abstain
        assert result.abstained is True
        assert result.abstention_reason == AbstentionReason.LOW_CONFIDENCE
        assert result.abstention_message is not None
        assert result.answer is None

    @pytest.mark.parametrize("verified_conf,expected_abstain", [
        (0.85, False),  # High confidence - no abstention
        (0.5, False),   # Medium confidence - no abstention
        (0.25, True),   # Low confidence - abstain
    ])
    @pytest.mark.asyncio
    async def test_abstention_based_on_confidence(
        self,
        citation_confidence_service,
        verified_conf,
        expected_abstain
    ):
        """Test abstention decision based on confidence threshold."""
        # Use real abstention service for this test
        real_abstention_service = AbstentionService()
        citation_confidence_service.abstention_service = real_abstention_service

        verified_response = create_sample_verified_response(
            verified_confidence=verified_conf
        )

        result = await citation_confidence_service.enhance(verified_response)

        assert result.abstained == expected_abstain
```

---

## 11. IMPORTANT DECISIONS

### Why This Approach Over Alternatives

**Decision 1: Multi-Factor Abstention Over Simple Threshold**

**Alternatives Considered**:
- **Single Threshold**: Abstain if confidence < 0.3 only
- **Binary Hallucination Check**: Abstain if hallucination_probability > 0.7 only
- **Multi-Factor (Our Choice)**: Consider confidence, hallucination, evidence, and verification status

**Why Multi-Factor?**
- **Robustness**: Single factor can have false positives/negatives
- **User Trust**: Abstaining when appropriate builds trust more than wrong answers
- **Research-Backed**: CoVe paper emphasizes conservative abstention in RAG
- **Flexibility**: Can tune thresholds independently per deployment

**Trade-off Accepted**: May abstain more frequently than simpler approaches, but prioritizes accuracy over coverage

---

**Decision 2: Weighted 4-Factor Confidence Over Simple Average**

**Alternatives Considered**:
- **LLM-Based Confidence**: Ask LLM "How confident are you?" (unreliable)
- **Citation Count Only**: More citations = higher confidence (too simplistic)
- **Weighted Multi-Factor (Our Choice)**: 40% passage, 35% quote, 15% verification, 10% count

**Why Weighted Multi-Factor?**
- **Interpretable**: Users understand "confidence based on evidence quality"
- **Tuneable**: Can adjust weights based on domain/deployment
- **Research-Aligned**: Similar to citation quality scoring in academic systems
- **Transparent**: Factor breakdown in metadata explains confidence

**Trade-off Accepted**: More complex than simple averaging, but provides actionable insights

---

**Decision 3: Citation Quality Indicators (Strong/Medium/Weak) Over Binary**

**Alternatives Considered**:
- **Binary**: Has citation or doesn't
- **Numeric Score**: Show raw similarity score (0.87)
- **Quality Levels (Our Choice)**: STRONG (>0.95), MEDIUM (0.85-0.95), WEAK (<0.85)

**Why Quality Levels?**
- **User-Friendly**: "Strong evidence" clearer than "0.95 similarity"
- **Actionable**: Users can filter by citation quality
- **Aligned with Academic Practice**: Similar to "primary source" vs "secondary source"
- **Calibrated to Thresholds**: Matches quote matching threshold (0.85)

**Trade-off Accepted**: Loses precision of exact score, but gains clarity

---

**Decision 4: Per-Proposition Confidence Over Overall Only**

**Alternatives Considered**:
- **Overall Only**: Single confidence score for entire answer
- **Per-Sentence**: Confidence for every sentence (too granular)
- **Per-Proposition (Our Choice)**: Confidence for each atomic claim (3-5 per answer)

**Why Per-Proposition?**
- **Transparency**: Users see which claims are uncertain
- **Actionable**: Can challenge/verify specific claims
- **Aligned with Verification**: Propositions are unit of verification in Step 11.2
- **Balanced Granularity**: Not too coarse (overall) or too fine (sentence)

**Trade-off Accepted**: More metadata to return, but enables claim-level trust

---

### Trade-offs Accepted

**1. Abstention Rate vs Coverage**
- **Conservative Abstention**: May abstain on answerable questions
- **Justification**: False negatives (abstaining when could answer) less harmful than false positives (wrong answers)
- **Mitigation**: Track abstention rate, tune thresholds if >30%

**2. Complexity vs Interpretability**
- **4-Factor Weighted Confidence**: More complex than simple average
- **Justification**: Weighted approach reflects actual evidence quality
- **Mitigation**: Provide confidence_breakdown in metadata for transparency

**3. Response Size vs Detail**
- **Rich Metadata**: EnhancedAnswerResponse larger (~50KB vs 20KB)
- **Justification**: Citation transparency is core value proposition
- **Mitigation**: Compress metadata for API, allow clients to opt-in to details

**4. CPU Usage vs Zero Additional Latency**
- **Enhancement Adds ~100-200ms**: Not zero overhead
- **Justification**: CPU-bound operations fast compared to LLM calls (4-5s)
- **Mitigation**: Aggressive caching, async database writes

---

### Technical Debt Incurred

**1. Confidence Weight Learning**
- **Debt**: Static weights (0.40, 0.35, 0.15, 0.10), not learned from data
- **Impact**: May not be optimal for all domains/deployments
- **Payoff Plan**: Collect user feedback (thumbs up/down), learn optimal weights via ML (Step 13+)

**2. Abstention Message Templates**
- **Debt**: Generic abstention messages, not context-specific
- **Impact**: Users see "I cannot answer" without detailed explanation
- **Payoff Plan**: Add structured abstention explanations (which documents checked, what was missing)

**3. Citation Validation Errors**
- **Debt**: Validation errors logged but not auto-fixed
- **Impact**: Users may see citation number mismatches
- **Payoff Plan**: Implement auto-repair (renumber citations, remove invalid references)

**4. Confidence Calibration**
- **Debt**: Raw confidence scores not calibrated against actual accuracy
- **Impact**: Confidence=0.8 may not actually mean 80% correct
- **Payoff Plan**: Calibrate scores using historical accuracy data (Step 13.1)

**5. HTML Highlighting Security**
- **Debt**: Basic HTML escaping, not comprehensive XSS prevention
- **Impact**: Potential XSS if passage text contains malicious content
- **Payoff Plan**: Use proper HTML sanitization library (bleach, html-sanitizer)

---

### Future Improvements

**Short-Term (Post-MVP)**:
1. **Adaptive Confidence Weights**: Learn weights from user feedback per domain
2. **Structured Abstention Explanations**: "I checked 5 documents but found no mention of X"
3. **Citation Auto-Repair**: Fix validation errors automatically
4. **Confidence Calibration**: Calibrate scores against ground truth accuracy

**Long-Term**:
1. **Interactive Citation Verification**: Allow users to verify/challenge citations
2. **Citation Recommendation**: Suggest additional sources to improve confidence
3. **Multi-Language Citation**: Support non-English documents with translated citations
4. **Visual Citation Explorer**: Interactive UI to explore citation graph

---

## Summary

**Step 11.3: Citation & Confidence** completes the answer generation pipeline by adding:

1. **Intelligent Abstention** (4-factor decision)
2. **Granular Confidence Scoring** (per-proposition with breakdown)
3. **Rich Citation Enrichment** (quality indicators, highlighted quotes, inline formatting)
4. **Comprehensive Metadata** (proposition details, abstention factors, validation)

**Key Benefits**:
- **User Trust**: Abstain when uncertain rather than hallucinate
- **Transparency**: Per-claim confidence and evidence quality visible
- **Actionable Insights**: Users can verify specific claims via citations
- **Production-Ready**: Fully validated responses with comprehensive metadata

**Performance Targets**:
- Latency: <200ms additional (vs Step 11.2's 4-5s)
- Abstention Rate: 10-20% (configurable via thresholds)
- Citation Quality: >60% STRONG citations (exact/near-exact quotes)

**Deliverable Achieved**: POST /api/v1/answer endpoint with verified citations, abstention logic, and granular confidence scoring - ready for production deployment.

---

**Document Version**: 1.0
**Last Updated**: 2025-10-30
**Author**: QueryboxCore Team
**Review Status**: Ready for Implementation
