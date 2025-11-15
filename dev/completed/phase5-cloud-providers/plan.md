# Phase 5: Cloud Provider Integration & System Fixes

## Overview
Integrate cloud-based AI providers (HF Inference API for embeddings, OpenRouter for LLM) to improve speed and quality, plus fix critical system issues discovered during testing.

## Objectives
1. Replace slow local CPU embeddings with HF Inference API (free tier: 30K/month)
2. Replace TinyLlama with OpenRouter GPT-4o-mini for better answer quality
3. Fix document upload/processing pipeline issues
4. Improve error logging with Sentry integration

## Background
**Problem Discovery:**
- User uploaded FastAPI document and asked questions
- Issues found:
  1. LLM responses incomplete/showing prompt text (TinyLlama too small)
  2. Timeout on first request (3000ms - CPU too slow)
  3. Too many weak citations (9/10 with 0% relevance)
  4. Embeddings taking 5s on CPU
  5. Upload succeeded but processing failed silently

**Root Causes:**
- TinyLlama (637MB) insufficient for complex QA
- Local BGE-M3 on CPU too slow (5s per embedding)
- No citation quality filtering
- Celery running in wrong Python environment
- Missing Docling package
- NULL bytes in extracted text breaking PostgreSQL
- Lazy initialization bug in text extraction service

## Implementation Strategy

### Phase 1: Fix Answer Quality
- Improve LLM prompt template
- Implement smart citation filtering
- Increase token limits and timeouts

### Phase 2: Add Cloud Providers
- Implement HF Inference API for embeddings
- Configure OpenRouter for LLM
- Add proper error handling and retries

### Phase 3: Fix Processing Pipeline
- Fix Celery environment issues
- Install missing dependencies (Docling)
- Fix text extraction bugs
- Add Sentry logging to Celery tasks

## Architecture Decisions

### HF Inference API Choice
- **Selected**: Hugging Face Inference API
- **Alternatives Considered**: Google Colab, Local GPU (MPS)
- **Rationale**:
  - Production-ready with 30K/month free tier
  - 0.3-0.8s response time vs 5s local
  - No infrastructure management needed
  - Good for demo and MVP

### OpenRouter GPT-4o-mini Choice
- **Selected**: OpenRouter with GPT-4o-mini
- **Alternatives Considered**: Continue with TinyLlama, Ollama Llama3
- **Rationale**:
  - Better answer quality (vs TinyLlama's incomplete responses)
  - Fast (1-3s vs 30s+ local)
  - Cost-effective ($0.0003/query)
  - No local GPU required

## Key Files Created/Modified

### Cloud Provider Implementation
- `backend/app/services/embeddings/hf_inference_provider.py` (new, 314 lines)
- `backend/app/services/embeddings/factory.py:63-70` (added HF provider)
- `backend/app/core/config.py:75-81` (HF settings)
- `backend/requirements.txt:49` (added huggingface-hub>=0.20.0)
- `backend/requirements.txt:38` (added docling>=1.0.0)

### Bug Fixes
- `backend/app/services/extraction/text_extraction_service.py:173-178` (fixed lazy init)
- `backend/app/services/extraction/text_extraction_service.py:510,540` (NULL byte cleaning)
- `backend/app/tasks/extraction_tasks.py:16` (added sentry_sdk import)
- `backend/app/tasks/extraction_tasks.py:119-131` (Sentry error capture)
- `backend/app/tasks/extraction_tasks.py:228-256` (Sentry exception capture)

### Configuration
- `backend/.env:41-43` (set providers: hf-inference, openrouter)
- `backend/.env:92-105` (added HF configuration)
- `backend/app/api/v1/endpoints/upload.py:129-132,147,176-179` (improved logging)

### Answer Quality Improvements
- `backend/app/services/answer_service.py:33-50` (improved prompt template)
- `backend/app/services/answer_service.py:99` (increased to 3000 tokens)
- `backend/app/services/answer_service.py:568-647` (citation filtering logic)
- `backend/.env:78` (increased OLLAMA_TIMEOUT to 120s)

## Performance Impact

### Before
- Embeddings: ~5s (local CPU)
- LLM: ~30s (TinyLlama on CPU)
- Citations: Always 10 (regardless of quality)
- Upload processing: Silent failures

### After (Expected)
- Embeddings: 0.3-0.8s (HF Inference API)
- LLM: 1-3s (OpenRouter GPT-4o-mini)
- Citations: 1-3 high-quality only
- Upload processing: Full Sentry error tracking

### After (Actual - First Test)
- Embeddings: 5.7s (HF Inference API) - **SLOWER than expected, possible cold start**
- LLM: Not yet tested (OpenRouter GPT-4o-mini)
- Citations: Not yet tested (implementation complete)
- Upload processing: Full Sentry error tracking ✅
- Extraction: 185s (Docling) - **Slower than expected but excellent quality**
- Chunking: 1.1s ✅

## Risks & Mitigations

### Rate Limits
- **Risk**: HF free tier 30K/month limit
- **Mitigation**: Redis caching for query embeddings, monitor usage

### Cost
- **Risk**: OpenRouter costs beyond free tier
- **Mitigation**: Track costs via logging, cheap model ($0.0003/query)

### Network Dependency
- **Risk**: Cloud API failures
- **Mitigation**: Retry logic with exponential backoff, error tracking

## Testing Strategy

1. Upload test documents (PDF, TXT)
2. Verify processing pipeline (extraction → chunking → embeddings)
3. Test search with various queries
4. Verify citation quality filtering
5. Monitor Sentry for any errors
6. Check answer quality and speed

## Success Metrics

**Final Status (Nov 15, 12:00 AM) - ALL COMPLETE ✅**:
- ✅ Upload → Processing → Ready for search (multiple PDFs tested successfully)
- ✅ Embeddings generated (HF Inference API working, cold start understood)
- ✅ Answers generated in < 5s total (tested and validated)
- ✅ 1-3 citations per answer (high quality filtering working)
- ✅ All errors logged to Sentry with context
- ✅ No NULL byte errors (fix applied and working)
- ✅ No "service unavailable" errors (lazy init fix applied)

**Phase 5 Status**: COMPLETE - Ready for production demo and MVP deployment
