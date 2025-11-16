# QueryBox Backend RAG Optimization - Strategic Plan

## Vision & Goals

Transform QueryBox from "functional prototype" to "production-ready, high-accuracy RAG system" within 2 days.

### Primary Objectives
1. **99% Accuracy**: Measured via RAGAs metrics (faithfulness, answer relevancy, context precision/recall)
2. **<2s Latency**: p95 response time under 2 seconds for typical queries
3. **Sustainable Architecture**: Modular, swappable components with clear upgrade paths
4. **Cost-Effective**: <$100 for demo, <$30-50/month in production

### Success Metrics
- **RAGAs Faithfulness**: >0.90 (no hallucinations)
- **RAGAs Answer Relevancy**: >0.90 (answers the question)
- **RAGAs Context Precision**: >0.80 (retrieved chunks are relevant)
- **RAGAs Context Recall**: >0.85 (all relevant info retrieved)
- **p50 Latency**: <1.5s
- **p95 Latency**: <3s
- **Citation Accuracy**: >95% verifiable
- **Cost per Query**: <$0.05

---

## Strategic Approach

### Philosophy: Build Modular, Migrate Gradually

Rather than rip-and-replace, we're building a **modular architecture** where every component is swappable:

```
┌─────────────────────────────────────────┐
│         Modular Architecture            │
├─────────────────────────────────────────┤
│ Parser:    [Docling|MinerU|Unstructured]│
│ Embedder:  [OpenAI|BGE-M3|Cohere]       │
│ Vector DB: [Qdrant|pgvector|LanceDB]    │
│ LLM:       [OpenRouter|Ollama|Claude]   │
│ Retrieval: [MultiQuery|HyDE|Standard]   │
└─────────────────────────────────────────┘
              ↓
        Config-Driven (.env)
```

**Key Principle**: Start with managed services (speed to demo), migrate to self-hosted (cost optimization) as we scale.

---

## Technology Choices & Rationale

### 1. Parsing: Docling + MinerU + GPT-4o-mini Vision

**Current State**: Docling only (97.9% table accuracy, good OCR)

**Enhancement Strategy**:
- **Keep Docling** as primary parser (excellent, open-source, proven)
- **Add MinerU** for table-heavy documents (SOTA on FinTabNet benchmark)
- **Add GPT-4o-mini Vision** for charts/graphs/infographics

**Rationale**:
- Docling handles 90% of content excellently (text, structure, tables)
- MinerU specializes in complex tables (financial reports, data sheets)
- Vision model covers the final 10% (visual charts, diagrams)
- All three are **modular** - route based on document type

**Cost**: Free (Docling, MinerU) + ~$0.001 per chart image (GPT-4o-mini vision)

**Sustainability**: Open-source foundation, vision API only for edge cases

---

### 2. LLM: OpenRouter (Multi-Provider Access)

**Current State**: Ollama tinyllama (fast but low quality)

**New Approach**: OpenRouter with GPT-4o-mini default

**Rationale**:
- **Quality**: GPT-4o-mini is 10x better than tinyllama for RAG
- **Flexibility**: OpenRouter provides access to 100+ models (GPT, Claude, Gemini, Llama)
- **Simplicity**: One API key, same interface as OpenAI
- **Fallback**: Automatic retry with alternative models
- **A/B Testing**: Easy to compare GPT-4o-mini vs Claude-3-Haiku vs Gemini-2.0-Flash
- **No Lock-in**: Can switch to direct API later (just change base_url)

**Cost**: $0.15/1M input tokens, $0.60/1M output tokens (GPT-4o-mini)
- ~$0.005 per query (3K in, 500 out)
- ~$5-10 per 1,000 queries

**Long-Term Path**:
1. **Demo (Weeks 1-4)**: OpenRouter GPT-4o-mini (quality + speed)
2. **Production (Months 2-6)**: Fine-tuned Qwen2:7b (80%) + OpenRouter (20% complex)
3. **Scale (6+ months)**: Self-hosted vLLM cluster + OpenRouter fallback

**Sustainability**: Start managed, move to self-hosted, keep API as safety net

---

### 3. Embeddings: OpenAI text-embedding-3-large

**Current State**: BGE-M3 on CPU (slow, 100-500ms per batch)

**New Approach**: OpenAI embeddings API for queries, BGE-M3 GPU batch for documents

**Rationale**:
- **Speed**: OpenAI API is fast (<100ms), no GPU management needed
- **Quality**: text-embedding-3-large (3072-dim) is excellent for RAG
- **Cost**: $0.13/1M tokens - cheap for queries (only embedding query text, not all chunks)
- **Hybrid**: Use OpenAI for queries, BGE-M3 for document embedding (one-time cost)
- **Modular**: Abstract interface allows swapping to Cohere, Voyage, or self-hosted

**Cost**: ~$0.0001 per query (avg 100 tokens) = $0.10 per 1,000 queries

**Long-Term Path**:
- **Queries**: Keep OpenAI (cheap, fast, managed)
- **Documents**: Batch embed with BGE-M3 on GPU (one-time $5-10)
- **Future**: Fine-tune BGE-M3 on domain data for better accuracy

**Sustainability**: Queries are cheap enough to stay on API, documents embedded once

---

### 4. Vector Store: Qdrant (Parallel with PostgreSQL)

**Current State**: PostgreSQL + pgvector (works, but slower at scale)

**New Approach**: **Augment, don't replace** - Run Qdrant in parallel

**Architecture**:
```
PostgreSQL (Source of Truth)
    ↓ sync
Qdrant (Fast Vector Search)
```

**Rationale**:
- **Keep PostgreSQL**: Source of truth for documents, chunks, metadata, relations
- **Add Qdrant**: 10x faster vector search (50ms vs 500ms), better metadata filtering
- **No migration risk**: Postgres stays untouched, Qdrant is additive
- **A/B testable**: Compare performance, can rollback to pgvector anytime
- **Scalability**: Qdrant handles 10M+ vectors easily

**Cost**:
- Free tier: 1GB (300K vectors) - perfect for demo
- Self-hosted: $10-20/month VPS (Docker)
- Cloud paid: $25/month for 4GB

**Long-Term Path**:
1. **Demo**: Qdrant Cloud free tier
2. **Production (<300K vectors)**: Stay on free tier
3. **Scale (>300K vectors)**: Self-host Qdrant in Docker ($10-20/month)

**Sustainability**: Can drop Qdrant anytime, rebuild from Postgres if needed

---

### 5. Advanced Retrieval: Multi-Query RAG

**Current State**: Standard hybrid search (BM25 + vector + RRF + reranking)

**Enhancement**: Add Multi-Query RAG layer

**Rationale**:
- **15-25% accuracy gain**: Proven in benchmarks
- **Handles ambiguity**: Multiple query phrasings capture different aspects
- **Non-invasive**: Sits on top of existing search, no changes to core logic
- **Modular**: Can toggle on/off via config
- **Fast**: Parallel searches, minimal latency impact (<200ms)

**How it Works**:
1. User query: "What is France's capital?"
2. Generate variations: "Which city is France's capital?", "France capital city name"
3. Search with all 3 queries
4. Merge results with deduplication
5. Return top-k

**Alternative Considered**: HyDE (Hypothetical Document Embeddings)
- Also 10-15% gain
- Complementary to Multi-Query
- Can enable both or choose one via config

**Cost**: 3x embeddings per query = ~$0.0003 per query (negligible)

**Sustainability**: Technique-based, not vendor-dependent

---

### 6. Chunking: Semantic Boundaries + Better Overlap

**Current State**: 512 target tokens, 50 token overlap, paragraph boundaries

**New Approach**: 700 target tokens, 150 token overlap, semantic splitting

**Rationale**:
- **More context**: 700 tokens provides richer context for embeddings
- **Better overlap**: 150 tokens (20%) ensures no information lost at boundaries
- **Semantic splits**: Don't split mid-topic, respect document structure
- **Optimal for OpenAI**: text-embedding-3-large handles longer chunks well (8K max)

**Changes**:
```python
CHUNKING_TARGET_TOKENS = 700  # From 512
CHUNKING_MAX_TOKENS = 850      # From 600
CHUNKING_MIN_TOKENS = 150      # From 100
CHUNKING_OVERLAP_TOKENS = 150  # From 50
ENABLE_SEMANTIC_SPLITTING = True
```

**Impact**: 5-10% better citation accuracy, improved context coherence

**Sustainability**: Configuration change, not architectural

---

## Implementation Phases (2 Days)

### Day 1: Foundation + Core Upgrades

**Phase 1: Modular Architecture (3-4 hours)**
- Abstract base classes for all components
- Factory pattern for component instantiation
- Config-driven selection (.env)
- **Outcome**: Future-proof architecture

**Phase 2: Parsing Optimization (2-3 hours)**
- Docling parameter tuning (GPU, batch size, preload)
- MinerU integration + document type router
- GPT-4o-mini vision for charts
- **Outcome**: 99% parsing accuracy across all document types

**Phase 3: LLM & Embeddings (3-4 hours)**
- OpenRouter integration
- OpenAI embeddings for queries
- Side-by-side testing vs current setup
- **Outcome**: 70% accuracy improvement (biggest single win)

### Day 2: Advanced Retrieval + Optimization

**Phase 4: Vector Store (3-4 hours)**
- Qdrant client setup (local or cloud)
- Migration script (Postgres → Qdrant)
- Parallel operation + performance comparison
- **Outcome**: 10x faster vector search

**Phase 5: Advanced Retrieval (2-3 hours)**
- Multi-Query RAG implementation
- HyDE implementation (optional)
- Integration with existing hybrid search
- **Outcome**: 15-25% retrieval improvement

**Phase 6: Testing & Tuning (4-5 hours)**
- Improved chunking strategy
- RAGAs evaluation framework
- Hyperparameter tuning (RRF weights, reranking, confidence thresholds)
- End-to-end performance testing
- **Outcome**: Validated 99% accuracy, <2s latency

---

## Risk Mitigation

### Risk 1: OpenAI API Rate Limits
**Mitigation**:
- Start with tier 1 ($5 credit), sufficient for demo
- Implement exponential backoff + retry logic
- OpenRouter provides automatic fallback to other models
**Fallback**: Keep Ollama running, switch back via config if needed

### Risk 2: Qdrant Migration Issues
**Mitigation**:
- Run Postgres + Qdrant in parallel (no replacement)
- A/B test with feature flag
- Migration script is idempotent (can re-run)
**Fallback**: Disable Qdrant via config, use pgvector

### Risk 3: MinerU Installation/GPU Issues
**Mitigation**:
- Install early (Day 1 Phase 2)
- Test on sample documents immediately
- CPU fallback available
**Fallback**: Use Docling for all docs, MinerU is optional enhancement

### Risk 4: Time Overruns
**Mitigation**:
- Each phase is independently valuable
- Can stop after any phase and still have improvements
- Phase 3 (LLM upgrade) is the biggest win - prioritize if tight on time
**Minimum Viable**: Just Phase 1 + Phase 3 = 60-70% improvement in 6-7 hours

### Risk 5: Cost Overruns
**Mitigation**:
- Set OpenRouter spending limits ($50)
- Cache query embeddings (Redis, 30min TTL)
- Monitor costs in real-time via OpenRouter dashboard
**Fallback**: Switch to cheaper models (Claude-3-Haiku, Gemini-2.0-Flash)

---

## Cost Analysis

### Demo (2 Days, 500 Queries)
| Component | Cost | Notes |
|-----------|------|-------|
| OpenRouter (GPT-4o-mini) | $3-5 | 500 queries × $0.005 |
| OpenAI Embeddings | $0.50-1 | Queries only, docs done once |
| GPT-4o-mini Vision | $0.50-2 | ~10-20 chart images |
| Qdrant Cloud | $0 | Free tier (1GB) |
| MinerU/Docling | $0 | Open-source |
| **Total** | **$4-8** | **Well under budget** |

### Production (Month 1, 2,000 Queries)
| Component | Cost | Notes |
|-----------|------|-------|
| OpenRouter | $10-20 | 2K queries × $0.005 |
| OpenAI Embeddings | $2-5 | Queries + some new docs |
| Vision API | $2-5 | ~50-100 images |
| Qdrant | $0-25 | Free tier or self-hosted |
| **Total** | **$14-55** | **Sustainable** |

### Scale (Month 6+, 10K Queries/Month)
| Component | Cost | Optimization |
|-----------|------|--------------|
| LLM | $20-40 | 70% fine-tuned Qwen2:7b (free) + 30% OpenRouter |
| Embeddings | $5-10 | BGE-M3 GPU for docs, OpenAI for queries |
| Vector Store | $10-20 | Self-hosted Qdrant |
| GPU (Qwen2) | $50-100 | RunPod/Modal serverless |
| **Total** | **$85-170** | **Still reasonable, fully optimized** |

### Break-Even Analysis
- **OpenAI Embeddings vs BGE-M3 GPU**: Break-even at ~500K queries/month
- **OpenRouter vs Self-Hosted LLM**: Break-even at ~10K queries/month
- **Strategy**: Start managed (fast), optimize costs as we scale

---

## Long-Term Sustainability

### Upgrade Path (No Lock-In)

**Tier 1: Demo/MVP (Weeks 1-4)**
```
Parsing: Docling + MinerU (free)
Embeddings: OpenAI (managed, $5-10/month)
Vector Store: Qdrant Cloud (free tier)
LLM: OpenRouter GPT-4o-mini ($20-50/month)
```
**Focus**: Speed to demo, prove concept, measure baselines

**Tier 2: Production (Months 2-6)**
```
Parsing: Docling + MinerU + Vision API (as needed)
Embeddings: OpenAI (queries), BGE-M3 GPU batch (docs)
Vector Store: Self-hosted Qdrant ($10-20/month)
LLM: Fine-tuned Qwen2:7b (80%) + OpenRouter (20%)
```
**Focus**: Cost optimization, maintain quality, scale to 1K-10K queries/month

**Tier 3: Scale (6+ Months)**
```
Parsing: Docling + MinerU (GPU batch processing)
Embeddings: Fine-tuned BGE-M3 (domain-specific)
Vector Store: Qdrant cluster (HA)
LLM: vLLM cluster (Llama-3-70B) + OpenRouter fallback
Monitoring: Prometheus + Grafana
```
**Focus**: Maximum cost efficiency, enterprise reliability, 100K+ queries/month

### Architectural Benefits

1. **Swappable Components**: Change any component without rewriting others
2. **A/B Testing**: Run multiple providers in parallel, compare metrics
3. **Gradual Migration**: Move from managed to self-hosted component-by-component
4. **No Vendor Lock-In**: Can always switch providers or revert to previous setup
5. **Cost Optimization**: Start expensive (speed), optimize later (cost)
6. **Risk Mitigation**: Always have fallback options (Ollama, pgvector, BGE-M3)

---

## Success Criteria (Demo Day)

### Accuracy Targets
- ✅ RAGAs Faithfulness: >0.90
- ✅ RAGAs Answer Relevancy: >0.90
- ✅ RAGAs Context Precision: >0.80
- ✅ RAGAs Context Recall: >0.85
- ✅ Citation Accuracy: >95%
- ✅ Zero hallucinations on test dataset

### Performance Targets
- ✅ p50 Latency: <1.5s
- ✅ p95 Latency: <3s
- ✅ Parsing: <2s per document (PDF, mixed content)
- ✅ Embedding: <200ms per query
- ✅ Vector Search: <100ms (Qdrant) vs 500ms (pgvector)

### Cost Targets
- ✅ Demo total: <$20
- ✅ Per-query: <$0.01
- ✅ First month: <$50

### Architecture Targets
- ✅ All components swappable via config
- ✅ No breaking changes to existing API
- ✅ Backward compatible (can revert to Ollama/pgvector)
- ✅ Clear metrics dashboards (RAGAs, latency, cost)

---

## Key Decisions

### Decision 1: Augment, Don't Replace
- Keep PostgreSQL as source of truth
- Add Qdrant for speed, not replacement
- Keep Ollama as fallback option
- **Rationale**: De-risk migration, enable A/B testing, allow rollback

### Decision 2: Start Managed, Optimize Later
- Use OpenRouter/OpenAI APIs for demo (speed)
- Migrate to self-hosted as we scale (cost)
- **Rationale**: 2-day timeline favors managed services, can optimize after demo

### Decision 3: Modular Architecture First
- Build abstractions before implementations
- Config-driven component selection
- **Rationale**: Future-proofs codebase, aligns with Step 15 vision, enables experimentation

### Decision 4: Multi-Query over HyDE
- Multi-Query is simpler, proven, non-invasive
- HyDE available as optional enhancement
- **Rationale**: Lower risk, easier to implement, can add HyDE later if needed

### Decision 5: Keep Docling, Add MinerU + Vision
- Docling handles 90% excellently (no need to replace)
- MinerU for tables (10% edge cases)
- Vision API for charts/graphs (final 5%)
- **Rationale**: Incremental improvement, not risky replacement

---

## Next Steps

1. **Review this plan** - Ensure alignment on goals, approach, tech choices
2. **Read context.md** - Understand current codebase, files to modify
3. **Start with tasks.md** - Follow checklist, Phase 1 → Phase 6
4. **Begin Phase 1** - Modular architecture (3-4 hours)
   - Creates foundation for all subsequent work
   - Most important phase for long-term sustainability

**Estimated Total Time**: 16-20 hours over 2 days
**Expected Outcome**: 95-99% accuracy, <2s latency, <$100 cost, modular architecture

---

## Questions or Concerns?

Before starting implementation, ensure:
- [ ] OpenAI/OpenRouter API keys available
- [ ] Budget approved (~$50-100 for demo)
- [ ] Test dataset ready (10-20 Q&A pairs for evaluation)
- [ ] Sample documents representing production use cases
- [ ] Clear success criteria agreed upon

Ready to build! 🚀
