# QueryBox Core - Conversation & Memory System Analysis

**Status**: Complete analysis of current conversation/session handling
**Date**: 2025-11-15
**Finding**: NO conversation/session management infrastructure exists

---

## Quick Summary Table

| Aspect | Current State | Location |
|--------|--------------|----------|
| **Conversation Tables** | ❌ None | N/A |
| **Message Storage** | ❌ None | N/A |
| **Session Management** | ❌ None | N/A |
| **Multi-turn Support** | ❌ No | N/A |
| **Answer Caching** | ✅ Yes (1hr) | `/app/core/redis.py` |
| **Workspace Isolation** | ✅ Yes (tenant) | `/app/schemas/answer.py` |
| **Request Statefulness** | ❌ Stateless | All endpoints |

---

## Critical File Locations

### Schema Definitions
- **Answer Requests**: `/home/user/querybox-core/backend/app/schemas/answer.py` (Lines 11-43)
- **Search Queries**: `/home/user/querybox-core/backend/app/schemas/search.py` (Lines 56-95)

### API Endpoints
- **Answer API**: `/home/user/querybox-core/backend/app/api/v1/endpoints/answer.py`
  - POST `/answer` (Lines 59-131)
  - POST `/answer/verified` (Lines 138-263)
  - POST `/answer/enhanced` (Lines 270-455)
  
- **Search API**: `/home/user/querybox-core/backend/app/api/v1/endpoints/search.py`
  - POST `/search/` (Lines 36-172)
  - POST `/search/semantic` (Lines 174-327)
  - POST `/search/hybrid` (Lines 436-673)
  - POST `/search/unified` (Lines 676-933)

### Services
- **Answer Service**: `/home/user/querybox-core/backend/app/services/answer_service.py`
  - Context: 6000 tokens max (document passages only)
  - Caching: 1-hour TTL per answer
  
- **Search Service**: `/home/user/querybox-core/backend/app/services/search/search_service.py`
  - Strategies: keyword, vector, hybrid
  - No conversation handling

### Database
- **Schema**: `/home/user/querybox-core/backend/alembic/versions/20251105_1527_initial_schema.py`
  - Tables: documents, document_texts, document_versions, embeddings, processing_queue, processing_status
  - **Missing**: conversations, messages, sessions

- **ORM Models**: `/home/user/querybox-core/backend/app/models/`
  - Available: Document, DocumentVersion, DocumentText, Embedding, ProcessingQueue, ProcessingStatus
  - **Missing**: Conversation, Message, ChatSession

### Infrastructure
- **Redis**: `/home/user/querybox-core/backend/app/core/redis.py` (answer caching only)
- **FastAPI App**: `/home/user/querybox-core/backend/app/main.py`

---

## Request/Response Flow

### Current (Single-Turn) Flow
```
Client Query
    ↓
AnswerRequest/SearchQuery (workspace_id, query, filters)
    ↓
Service Layer (no conversation loading)
    ├─ Check cache (answer only, 1hr)
    ├─ Retrieve document passages (6000 tokens context)
    ├─ Generate response
    └─ Cache result
    ↓
Response (no history persisted)
    ↓
[Conversation ends]
```

### What's Missing for Multi-Turn
1. Load conversation history from DB
2. Build conversation context for LLM prompt
3. Include previous messages in context window
4. Persist new user message + response
5. Manage conversation lifecycle

---

## Key Code Snippets

### Answer Request (No conversation fields)
```python
# /app/schemas/answer.py, Lines 11-43
class AnswerRequest(BaseModel):
    query: str                          # User question only
    document_ids: Optional[List[str]]   # Filter docs
    workspace_id: Optional[str]         # Tenant isolation (NOT conversation)
    top_k: int = 5                      # Passage count
    temperature: Optional[float] = 0.2  # LLM parameter
    include_citations: bool = True      # Citation flag
    # ❌ NO: conversation_id, session_id, history, previous_messages
```

### Answer Service Context
```python
# /app/services/answer_service.py, Lines 94-99
MAX_CONTEXT_TOKENS = 6000              # For document passages
MAX_COMPLETION_TOKENS = 2000           # LLM output
CACHE_TTL_SECONDS = 3600               # 1-hour cache
```

### Redis Cache (Answer-only)
```python
# /app/core/redis.py, Lines 62-72
async def set_with_expiry(key: str, value: str, expiry: int = 3600):
    """Set with default 1-hour expiry - for answers only"""
    client = await get_redis()
    await client.setex(key, expiry, value)
    
# Cache key in answer_service.py: hash(query, document_ids, workspace_id)
# No conversation ID component
```

### API Endpoints (All Stateless)
```python
# /app/api/v1/endpoints/answer.py, Lines 114-121
logger.info(
    f"Answer request received: query_length={len(request.query)}, "
    f"document_ids={len(request.document_ids or [])}"
)
# ❌ No conversation_id logging
# ❌ No history reference
```

---

## Database Schema Gap

### Current Tables (6 total)
```sql
documents              -- Document metadata
document_texts        -- Full extracted text
document_versions     -- Document version history
embeddings           -- Vector embeddings for search
processing_queue     -- Async task queue
processing_status    -- Per-stage processing state
```

### Missing for Conversations
```sql
conversations        -- Conversation metadata (id, user_id, created_at)
messages            -- Individual messages (id, conversation_id, role, content, created_at)
conversation_context -- Stored context per conversation (id, conversation_id, context_data)
```

---

## Important Notes

### What DOES Work
- Single-turn answer generation ✅
- Document retrieval & search ✅
- Citation extraction ✅
- Verification (hallucination detection) ✅
- Multi-tenant isolation (workspace_id) ✅
- Answer caching (1 hour) ✅
- Performance tracking ✅

### What DOESN'T Work
- Multi-turn conversations ❌
- Message persistence ❌
- Conversation history ❌
- Session management ❌
- Context accumulation ❌
- User interaction tracking ❌

### Design Philosophy
- **Single-turn RAG**: Query → Retrieve → Answer
- **Stateless**: Each request fully independent
- **Fast & Scalable**: Minimal state management
- **Document-focused**: Sources > conversation history

---

## For Implementation of Conversation Support

You would need to:

1. **Create Database Tables**
   - Alembic migration: create conversations, messages, context tables

2. **Create ORM Models**
   - `/app/models/conversation.py` - Conversation entity
   - `/app/models/message.py` - Message entity

3. **Extend Schemas**
   - Add `conversation_id` field
   - Add `is_continuation` flag
   - Create response schemas for history

4. **Modify Services**
   - Load conversation history before generating answer
   - Build context from previous messages
   - Persist new messages after generation

5. **Add API Endpoints**
   - POST `/conversations` - create
   - GET `/conversations/{id}` - get history
   - POST `/conversations/{id}/messages` - add message
   - DELETE `/conversations/{id}` - archive

---

**Full detailed analysis**: See `/CONVERSATION_MEMORY_ANALYSIS.md` (this file)

