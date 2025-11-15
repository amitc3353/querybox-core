"""
Answer Generation Service for Step 11.1 - Ollama LLM Integration

Orchestrates retrieval, context assembly, and answer generation.
Implements caching, proposition extraction, and citation management.
"""
import re
import time
import hashlib
import logging
import tiktoken
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from fastapi import HTTPException, status as http_status
from redis import Redis

from app.services.llm.factory import get_llm_provider
from app.services.llm.base import LLMProvider
from app.schemas.answer import (
    AnswerRequest,
    AnswerResponse,
    Proposition,
    Citation
)

logger = logging.getLogger(__name__)


# ============================================================================
# PROMPT TEMPLATE
# ============================================================================

ANSWER_PROMPT_TEMPLATE = """You are a helpful assistant that answers questions using ONLY the provided document passages.

CONTEXT PASSAGES:
{context}

RULES:
1. Answer the question using ONLY information from the passages above
2. Cite sources using [1], [2], etc. matching the passage numbers shown
3. Provide a complete, detailed answer - don't be brief
4. Use direct quotes from passages when possible
5. If the answer is not in the passages, say: "I cannot answer this based on the provided documents."
6. DO NOT make up information or use external knowledge

QUESTION: {query}

Please provide a detailed answer to the question above using the context passages. Remember to cite your sources with [1], [2], etc.

ANSWER:"""


# ============================================================================
# HELPER CLASSES
# ============================================================================

class Passage:
    """Represents a retrieved passage for context"""
    def __init__(
        self,
        text: str,
        document_id: str,
        document_name: str,
        rerank_score: float = 0.0,
        page: Optional[int] = None,
        section: Optional[str] = None,
        chunk_index: Optional[int] = None
    ):
        self.text = text
        self.document_id = document_id
        self.document_name = document_name
        self.rerank_score = rerank_score
        self.page = page
        self.section = section
        self.chunk_index = chunk_index


# ============================================================================
# ANSWER SERVICE
# ============================================================================

class AnswerService:
    """
    Service for generating answers from documents using Ollama

    Workflow:
    1. Validate query
    2. Retrieve relevant passages (via search service)
    3. Fit passages into context window
    4. Build prompt with citations template
    5. Generate answer via Ollama
    6. Extract propositions
    7. Build citations
    8. Cache result
    """

    # Context management
    MAX_CONTEXT_TOKENS = 6000
    MAX_COMPLETION_TOKENS = 3000  # Increased for more detailed answers

    # Caching
    CACHE_TTL_SECONDS = 3600  # 1 hour

    def __init__(self, redis_client: Optional[Redis] = None, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize Answer Service

        Args:
            redis_client: Redis client for caching (optional)
            llm_provider: Optional LLM provider. If None, uses factory to get default provider.
        """
        self.llm_provider = llm_provider
        self.redis_client = redis_client
        self.encoder = tiktoken.get_encoding("cl100k_base")

        logger.info("AnswerService initialized")

    def _get_llm_provider(self) -> LLMProvider:
        """Get or initialize LLM provider"""
        if self.llm_provider is None:
            self.llm_provider = get_llm_provider()
            logger.info(f"Initialized LLM provider: {type(self.llm_provider).__name__}")
        return self.llm_provider

    async def generate_answer(
        self,
        request: AnswerRequest
    ) -> AnswerResponse:
        """
        Generate answer for user query

        Args:
            request: Answer request with query and filters

        Returns:
            AnswerResponse with answer, citations, and metadata

        Raises:
            HTTPException: On validation or generation errors
        """
        start_time = time.perf_counter()

        logger.info(
            f"Generating answer: query_length={len(request.query)}, "
            f"top_k={request.top_k}, document_ids={len(request.document_ids or [])}"
        )

        try:
            # Step 1: Check cache
            cache_key = self._get_cache_key(request)
            if self.redis_client:
                cached = await self._get_cached_answer(cache_key)
                if cached:
                    logger.info(f"Cache hit for query hash: {cache_key}")
                    return cached

            # Step 2: Retrieve passages
            passages = await self._retrieve_passages(request)

            if not passages:
                logger.warning("No passages retrieved for query")
                return self._abstention_response(
                    request.query,
                    "No relevant documents found",
                    int((time.perf_counter() - start_time) * 1000)
                )

            # Step 3: Fit passages to context window
            selected_passages = self._fit_passages_to_context(
                passages,
                max_tokens=self.MAX_CONTEXT_TOKENS
            )

            logger.info(
                f"Context assembly: {len(selected_passages)}/{len(passages)} passages selected"
            )

            # Step 4: Build prompt
            prompt = self._build_prompt(request.query, selected_passages)

            # Step 5: Generate answer via LLM provider
            try:
                llm_provider = self._get_llm_provider()

                # Use async if available, otherwise sync
                if hasattr(llm_provider, 'generate_async'):
                    llm_response = await llm_provider.generate_async(
                        prompt=prompt,
                        temperature=request.temperature,
                        max_tokens=self.MAX_COMPLETION_TOKENS
                    )
                else:
                    llm_response = llm_provider.generate(
                        prompt=prompt,
                        temperature=request.temperature,
                        max_tokens=self.MAX_COMPLETION_TOKENS
                    )

                answer_text = llm_response.text.strip()
                metadata = {
                    "model": llm_response.model,
                    "tokens_input": llm_response.tokens_input,
                    "tokens_output": llm_response.tokens_output,
                    "latency_ms": llm_response.latency_ms
                }

            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
                raise HTTPException(
                    status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Answer generation service unavailable: {e}"
                )

            # Step 6: Check for abstention
            if "cannot answer" in answer_text.lower():
                logger.info("LLM abstained from answering")
                return self._abstention_response(
                    request.query,
                    answer_text,
                    int((time.perf_counter() - start_time) * 1000)
                )

            # Step 7: Extract propositions
            propositions = self._extract_propositions(answer_text)

            # Step 8: Build citations
            citations = []
            if request.include_citations:
                citations = self._build_citations(selected_passages)

            # Step 9: Calculate confidence
            confidence = self._calculate_confidence(
                answer_text,
                selected_passages,
                propositions
            )

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            response = AnswerResponse(
                success=True,
                answer=answer_text,
                propositions=propositions,
                citations=citations,
                confidence=confidence,
                can_answer=True,
                abstention_reason=None,
                processing_time_ms=elapsed_ms,
                passages_used=len(selected_passages),
                model_used=metadata.get("model", "qwen2:7b"),
                cache_hit=False
            )

            # Step 10: Cache result
            if self.redis_client:
                await self._cache_answer(cache_key, response)

            logger.info(
                f"Answer generated successfully: "
                f"confidence={confidence:.2f}, "
                f"propositions={len(propositions)}, "
                f"citations={len(citations)}, "
                f"time={elapsed_ms}ms"
            )

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating answer: {e}", exc_info=True)
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    # ========================================================================
    # RETRIEVAL
    # ========================================================================

    async def _retrieve_passages(
        self,
        request: AnswerRequest
    ) -> List[Passage]:
        """
        Retrieve relevant passages using hybrid search service

        Args:
            request: Answer request

        Returns:
            List of Passage objects sorted by relevance
        """
        from app.db.database import get_db
        from app.services.search.hybrid_search_service import get_hybrid_search_service
        from app.services.search.bm25_search_service import get_bm25_search_service
        from app.services.search.vector_search_service import get_vector_search_service
        from app.services.search.rrf_ranker import get_rrf_ranker
        from app.services.search.reranking_pipeline import get_reranking_pipeline
        from app.services.embeddings import get_embedding_service
        from app.schemas.search import SearchFilters

        # Get database session
        db = next(get_db())

        try:
            # Build filters from document_ids if provided
            filters = None
            if request.document_ids:
                filters = SearchFilters(document_ids=request.document_ids)

            # Initialize search services
            embedding_service = get_embedding_service()
            bm25_service = get_bm25_search_service(db)
            vector_service = get_vector_search_service(db, embedding_service)
            rrf_ranker = get_rrf_ranker()
            reranking_pipeline = get_reranking_pipeline()

            # Create hybrid search service
            hybrid_search = get_hybrid_search_service(
                db=db,
                bm25_service=bm25_service,
                vector_service=vector_service,
                rrf_ranker=rrf_ranker,
                reranking_pipeline=reranking_pipeline
            )

            # Execute hybrid search with reranking
            search_response = hybrid_search.search(
                query=request.query,
                filters=filters,
                limit=request.top_k * 4,  # Get more candidates for context window fitting
                offset=0,
                enable_reranking=True,
                rerank_top_k=request.top_k * 2
            )

            # Convert search results to Passage objects
            passages = []
            for result in search_response.results:
                passages.append(
                    Passage(
                        text=result.snippet,
                        document_id=str(result.document_id),
                        document_name=result.document_name,
                        rerank_score=result.relevance_score,
                        page=result.page_number,
                        section=result.section,
                        chunk_index=result.chunk_index
                    )
                )

            logger.info(
                f"Retrieved {len(passages)} passages via hybrid search for query: {request.query[:50]}..."
            )

            return passages

        finally:
            db.close()

    # ========================================================================
    # CONTEXT MANAGEMENT
    # ========================================================================

    def _fit_passages_to_context(
        self,
        passages: List[Passage],
        max_tokens: int
    ) -> List[Passage]:
        """
        Select passages that fit within token budget

        Algorithm:
        1. Sort by rerank_score descending
        2. Greedily add passages until budget exhausted
        3. Truncate final passage at sentence boundary if needed

        Args:
            passages: List of passages
            max_tokens: Maximum tokens allowed

        Returns:
            List of selected passages
        """
        selected = []
        current_tokens = 0

        # Sort by relevance score
        sorted_passages = sorted(
            passages,
            key=lambda p: p.rerank_score,
            reverse=True
        )

        for passage in sorted_passages:
            passage_tokens = len(self.encoder.encode(passage.text))

            if current_tokens + passage_tokens <= max_tokens:
                selected.append(passage)
                current_tokens += passage_tokens
            else:
                # Try to fit truncated passage
                remaining = max_tokens - current_tokens
                if remaining > 100:  # Only if meaningful space left
                    truncated = self._truncate_at_sentence(
                        passage.text,
                        remaining
                    )
                    if truncated:
                        passage.text = truncated
                        selected.append(passage)
                break

        logger.debug(
            f"Context fitting: selected {len(selected)}/{len(passages)} passages, "
            f"tokens={current_tokens}/{max_tokens}"
        )

        return selected

    def _truncate_at_sentence(
        self,
        text: str,
        max_tokens: int
    ) -> Optional[str]:
        """
        Truncate text at sentence boundary within token limit

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens

        Returns:
            Truncated text or None if cannot fit meaningful content
        """
        sentences = re.split(r'(?<=[.!?])\s+', text)
        result = []
        current_tokens = 0

        for sent in sentences:
            sent_tokens = len(self.encoder.encode(sent))
            if current_tokens + sent_tokens <= max_tokens:
                result.append(sent)
                current_tokens += sent_tokens
            else:
                break

        if not result:
            return None

        return " ".join(result)

    # ========================================================================
    # PROMPT BUILDING
    # ========================================================================

    def _build_prompt(
        self,
        query: str,
        passages: List[Passage]
    ) -> str:
        """
        Build prompt with passages and query

        Args:
            query: User question
            passages: Selected passages

        Returns:
            Formatted prompt string
        """
        context_parts = []

        for i, passage in enumerate(passages, start=1):
            source_info = f"Source: {passage.document_name}"
            if passage.page:
                source_info += f", Page {passage.page}"
            if passage.section:
                source_info += f", Section: {passage.section}"

            context_parts.append(
                f"[{i}] {passage.text}\n{source_info}"
            )

        context = "\n\n".join(context_parts)

        prompt = ANSWER_PROMPT_TEMPLATE.format(
            context=context,
            query=query
        )

        return prompt

    # ========================================================================
    # PROPOSITION EXTRACTION
    # ========================================================================

    def _extract_propositions(self, answer: str) -> List[Proposition]:
        """
        Extract atomic propositions from answer

        Strategy:
        - Split on sentence boundaries
        - Merge very short sentences (<5 words)
        - Split long sentences (>40 words) at conjunctions
        - Limit to 5 key claims

        Args:
            answer: Generated answer text

        Returns:
            List of Proposition objects
        """
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', answer.strip())

        propositions = []
        for sent in sentences:
            words = sent.split()

            if len(words) < 5 and propositions:
                # Merge very short sentence with previous (e.g., "Yes.", "No.")
                propositions[-1] = propositions[-1] + " " + sent
            elif len(words) > 40:
                # Split long sentences at conjunctions
                sub_sents = re.split(r'\s+(and|but|however)\s+', sent, flags=re.IGNORECASE)
                # Filter out conjunctions themselves
                sub_sents = [s for s in sub_sents if s.lower() not in ['and', 'but', 'however']]
                propositions.extend(sub_sents)
            else:
                propositions.append(sent)

        # Limit to 5 propositions
        propositions = propositions[:5]

        # Convert to Proposition objects
        result = [
            Proposition(text=text.strip(), index=i, confidence=None)
            for i, text in enumerate(propositions)
            if text.strip()
        ]

        logger.debug(f"Extracted {len(result)} propositions from answer")

        return result

    # ========================================================================
    # CITATION BUILDING
    # ========================================================================

    def _build_citations(self, passages: List[Passage]) -> List[Citation]:
        """
        Build citation list from passages, filtering out very weak citations

        Strategy:
        - Always include STRONG citations (score >= 0.8)
        - Include MEDIUM citations (score >= 0.6)
        - Include WEAK citations (score >= 0.4) only if we have < 3 citations
        - Filter out very weak citations (score < 0.4) unless it's the only result

        Args:
            passages: Passages used for answer

        Returns:
            List of Citation objects (filtered for quality)
        """
        citations = []
        STRONG_THRESHOLD = 0.8
        MEDIUM_THRESHOLD = 0.6
        WEAK_THRESHOLD = 0.4
        MIN_CITATIONS = 3  # Always show at least 3 if available

        for i, passage in enumerate(passages):
            # Generate chunk_id from document_id and chunk_index
            chunk_index = passage.chunk_index if passage.chunk_index is not None else i
            chunk_id = f"chunk_{passage.document_id}_{chunk_index}"

            # Determine citation quality based on relevance score
            if passage.rerank_score >= STRONG_THRESHOLD:
                quality = "STRONG"
            elif passage.rerank_score >= MEDIUM_THRESHOLD:
                quality = "MEDIUM"
            else:
                quality = "WEAK"

            # Extract file extension from document name
            file_type = "unknown"
            if "." in passage.document_name:
                file_type = passage.document_name.split(".")[-1].lower()

            citation = Citation(
                chunk_id=chunk_id,
                document_id=passage.document_id,
                document_filename=passage.document_name,
                content=passage.text[:1000],  # Limit to 1000 chars
                page_number=passage.page,
                chunk_index=chunk_index,
                relevance_score=passage.rerank_score,
                quality=quality,
                citation_number=i + 1,  # Add citation number (1-indexed)
                metadata={
                    "file_type": file_type,
                    "upload_date": datetime.now().isoformat()
                }
            )

            citations.append(citation)

        # Filter citations by quality
        # Strategy: Keep high-quality citations, limit low-quality ones
        strong_citations = [c for c in citations if c.quality == "STRONG"]
        medium_citations = [c for c in citations if c.quality == "MEDIUM"]
        weak_citations = [c for c in citations if c.quality == "WEAK"]

        # Build final citation list
        filtered_citations = []

        # Always include STRONG citations
        filtered_citations.extend(strong_citations)

        # Add MEDIUM citations if we need more
        if len(filtered_citations) < MIN_CITATIONS:
            filtered_citations.extend(medium_citations)

        # Only add WEAK citations if we're still below minimum
        # and only add the best weak ones (score >= 0.4)
        if len(filtered_citations) < MIN_CITATIONS:
            high_weak = [c for c in weak_citations if c.relevance_score >= WEAK_THRESHOLD]
            needed = MIN_CITATIONS - len(filtered_citations)
            filtered_citations.extend(high_weak[:needed])

        # If we still have nothing, include at least the top result
        if not filtered_citations and citations:
            filtered_citations = [citations[0]]

        # Renumber citations sequentially
        for i, citation in enumerate(filtered_citations):
            citation.citation_number = i + 1

        logger.info(
            f"Citations filtered: {len(citations)} -> {len(filtered_citations)} "
            f"(STRONG: {len(strong_citations)}, MEDIUM: {len(medium_citations)}, "
            f"WEAK kept: {len([c for c in filtered_citations if c.quality == 'WEAK'])})"
        )

        return filtered_citations

    # ========================================================================
    # CONFIDENCE SCORING
    # ========================================================================

    def _calculate_confidence(
        self,
        answer: str,
        passages: List[Passage],
        propositions: List[Proposition]
    ) -> float:
        """
        Calculate confidence score for answer

        Factors:
        - Number of citations in answer (weighted by passage relevance)
        - Average passage relevance score
        - Length and completeness of answer

        Args:
            answer: Generated answer
            passages: Source passages
            propositions: Extracted propositions

        Returns:
            Confidence score (0.0-1.0)
        """
        # Factor 1: Passage relevance (0.0-0.5) - most important factor
        if passages:
            avg_relevance = sum(p.rerank_score for p in passages) / len(passages)
            relevance_score = avg_relevance * 0.5
        else:
            avg_relevance = 0.0
            relevance_score = 0.0

        # Factor 2: Citation presence (0.0-0.3), scaled by passage relevance
        citation_matches = re.findall(r'\[\d+\]', answer)
        citation_ratio = min(len(citation_matches) / max(len(propositions), 1), 1.0)
        # Citations are only valuable if passages are relevant
        citation_score = citation_ratio * 0.3 * (0.5 + 0.5 * avg_relevance)

        # Factor 3: Answer completeness (0.0-0.2)
        word_count = len(answer.split())
        if word_count >= 50:
            completeness_score = 0.2
        elif word_count >= 20:
            completeness_score = 0.15
        else:
            completeness_score = 0.1

        confidence = citation_score + relevance_score + completeness_score

        return round(min(confidence, 1.0), 2)

    # ========================================================================
    # CACHING
    # ========================================================================

    def _get_cache_key(self, request: AnswerRequest) -> str:
        """
        Generate cache key from request

        Args:
            request: Answer request

        Returns:
            SHA256 hash as cache key
        """
        # Combine query and sorted document IDs
        doc_ids = sorted(request.document_ids or [])
        cache_input = f"{request.query}:{':'.join(doc_ids)}:{request.top_k}"

        return hashlib.sha256(cache_input.encode()).hexdigest()

    async def _get_cached_answer(self, cache_key: str) -> Optional[AnswerResponse]:
        """
        Get cached answer if exists

        Args:
            cache_key: Cache key

        Returns:
            AnswerResponse or None
        """
        try:
            import json
            cached_json = await self.redis_client.get(f"answer:{cache_key}")

            if cached_json:
                data = json.loads(cached_json)
                data["cache_hit"] = True
                return AnswerResponse(**data)

            return None

        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    async def _cache_answer(self, cache_key: str, response: AnswerResponse):
        """
        Cache answer response

        Args:
            cache_key: Cache key
            response: Answer response
        """
        try:
            import json
            cache_data = response.model_dump()
            await self.redis_client.setex(
                f"answer:{cache_key}",
                self.CACHE_TTL_SECONDS,
                json.dumps(cache_data)
            )
            logger.debug(f"Cached answer with key: {cache_key}")

        except Exception as e:
            logger.warning(f"Cache set error: {e}")

    # ========================================================================
    # ABSTENTION
    # ========================================================================

    def _abstention_response(
        self,
        query: str,
        reason: str,
        processing_time_ms: int
    ) -> AnswerResponse:
        """
        Build abstention response when cannot answer

        Args:
            query: Original query
            reason: Reason for abstention
            processing_time_ms: Processing time

        Returns:
            AnswerResponse with abstention
        """
        return AnswerResponse(
            success=True,
            answer="I cannot answer this based on the provided documents.",
            propositions=[],
            citations=[],
            confidence=0.0,
            can_answer=False,
            abstention_reason=reason,
            processing_time_ms=processing_time_ms,
            passages_used=0,
            model_used="qwen2:7b",
            cache_hit=False
        )


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

async def get_answer_service() -> AnswerService:
    """
    Get AnswerService instance for dependency injection

    Returns:
        AnswerService instance with Redis client if available
    """
    redis_client = None
    try:
        from app.core.redis import get_redis
        redis_client = await get_redis()
    except Exception as e:
        logger.warning(f"Redis client not available for AnswerService: {e}")

    return AnswerService(redis_client=redis_client)
