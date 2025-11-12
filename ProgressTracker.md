# Progress Tracker

🚀 QueryboxCore - RAG Engine Development Progress

## 📊 Current Status (January 2025)
- **Current Phase**: Step 13.7 Complete - Ready for Next Phase
- **Last Updated**: January 12, 2025
- **Next Milestone**: Phase 5 (Multi-Query RAG) or Supabase Migration

### Quick Stats:
- ✅ **Backend Complete**: Steps 1-13.7 (100% MVP Complete)
  - Full RAG pipeline operational
  - Hybrid search with reranking
  - Answer generation with verification
  - OpenRouter + OpenAI integration (Phase 3)
  - Comprehensive E2E test suite (800+ lines)
  - Qdrant infrastructure ready (Phase 4 - disabled until needed)
  - 48+ test files with excellent coverage
  - Modular architecture foundation (Step 15.1)
- ⏳ **Next Up**:
  - **Option 1**: Supabase Migration (authentication + simplicity)
  - **Option 2**: Phase 5 (Multi-Query RAG - 15-25% better accuracy)
  - **Option 3**: Phase 6 (RAGAs Evaluation & Tuning)
  - **Option 4**: Step 13 (Frontend Development)
- ✅ **Completed Recently**:
  - Step 13.7: Phase 4 - Qdrant Infrastructure (Jan 12-13)
  - Step 13.6: E2E Integration Tests
  - Phase 3: OpenRouter + OpenAI Embeddings
  - Phase 1: Modular Architecture Foundation (Step 15.1)

---

## 🎯 QueryBox Modular Vision (Post-UI Implementation)

**Goal**: Transform QueryBox into a modular, configurable AI document intelligence platform where components (parsers, embedders, retrievers, LLMs) can be swapped per client without rewriting core logic.

### Modular Components (Step 15)

| Component | Default (Current) | Alternatives (Planned) |
|-----------|-------------------|------------------------|
| **Parsers** | PyMuPDF | Docling, Unstructured.io, Custom |
| **Embedders** | BGE-M3 (local) | OpenAI ada-002, Cohere, Custom |
| **Retrievers** | Hybrid (BM25+Vector) | Pure Vector, Pure BM25, Custom |
| **LLMs** | Ollama (local) | OpenAI GPT, Anthropic Claude, OpenRouter |

### Implementation Strategy

1. ✅ **Build working system with defaults** (Steps 1-12) - DONE
   - Backend fully operational
   - Defaults: PyMuPDF, BGE-M3, Hybrid retrieval, Ollama

2. 🏗️ **Build UI and E2E tests** (Steps 13-14) - IN PROGRESS
   - Frontend with upload → search → chat flow
   - Comprehensive E2E test coverage
   - Live demo deployment

3. 🔮 **Refactor to modular architecture** (Step 15) - PLANNED
   - Base classes for all components
   - Provider registry pattern
   - Configuration system (YAML + database)
   - Multiple provider implementations

4. 🔮 **Per-client customization** (Step 15.3) - PLANNED
   - Client configuration API
   - Admin UI for configuration
   - Deployment profiles (SaaS, On-Prem, Hybrid)

### Why This Order?

**E2E tests provide safety net for refactoring:**
- Step 14 creates comprehensive test coverage
- Can confidently refactor in Step 15 knowing tests will catch regressions
- Live demo validates current functionality before changes
- Backward compatible - existing deployments unaffected

**Benefits:**
- 🔒 **Safe refactoring**: E2E tests catch any breaking changes
- 🎯 **Client flexibility**: Swap components via config, not code
- 📦 **Easy extension**: Add new providers without touching core
- 🔄 **Backward compatible**: Defaults preserve current behavior

---

## 📋 Strategic Priorities (Revised Dec 2024)
**Priority 1: Demo Readiness** (Steps 12-14)
- Step 12.5: Claude Code infrastructure (productivity boost)
- Step 13: Build frontend with upload → search → chat
- Step 14: E2E tests + live demo deployment

**Priority 2: Modular Architecture** (Step 15)
- Refactor to base classes + registry pattern
- Implement multiple providers per component
- Client configuration system

**Priority 3: User Feedback & Optimization** (Steps 16-18)
- Step 16: Collect usage data from pilots
- Step 17: Data-driven performance optimization
- Step 18: Quality assurance based on real queries

**Priority 4: Production Hardening** (Step 19)
- Advanced features and enterprise requirements
- Security, compliance, and scalability
- Launch preparation with case studies

---

## 🎯 Philosophy: Frontend-First, Then Optimize
**Old Approach:** Backend perfection → Frontend → Demo
**New Approach:** Demo-ready frontend → Users → Data-driven optimization

This inversion ensures we optimize what matters based on real user data.

📅 Week 1: Upload Foundation

## ✅ Day 1: Infrastructure Setup [COMPLETED]
### Step 1: Database & Storage Foundation (4 hours) ✅
* ✅ Set up PostgreSQL with document metadata schema
* ✅ Configure Redis for session management (basic setup)
* ✅ Create local file storage directory structure
* ✅ Establish database connection pooling
* **Outcome**: Ready-to-use data persistence layer

### Step 2: Core API Structure (2 hours) ✅
* ✅ Initialize FastAPI with proper project structure
* ✅ Configure CORS and middleware
* ✅ Set up route organization
* ✅ Create health check endpoint (with DB/Redis checks)
* **Outcome**: Running FastAPI application skeleton

## ✅ Day 2: Upload Endpoint Implementation [COMPLETED]
### Step 3: Basic Upload Handler (4 hours) ✅
* ✅ Implement multipart form data reception
* ✅ Create temporary file handling
* ✅ Store file to local storage
* ✅ Save metadata to database
* **Outcome**: Functional file upload endpoint

### Step 4: File Validation Layer (2 hours) ✅
* ✅ Implement file size validation (30MB limit)
* ✅ Add allowed file type checking
* ✅ Create MIME type verification (python-magic)
* ✅ Return detailed validation errors
* **Outcome**: Protected system from invalid uploads

**Additional Features Implemented:**
* ✅ SHA256 checksum for deduplication
* ✅ Duplicate file detection
* ✅ Comprehensive error handling
* ✅ Database model with all required fields

---

## ⏳ Day 3: Storage Management [PENDING]
### Step 5: Storage Service Pattern (3 hours)
* [✅] Create storage interface/protocol
* [✅] Implement local storage provider
* [✅] Add file path generation logic
* [✅] Handle file naming conflicts
* **Outcome**: Abstracted storage operations

### Step 6: Metadata Management (3 hours)
* [✅] Design comprehensive metadata schema
* [✅] Implement metadata extraction
* [✅] Create document status tracking
* [✅] Add timestamp management
* **Outcome**: Complete document tracking

## ⏳ Day 4: Retrieval & Status [PENDING]
### Step 7: Document Query Endpoints (3 hours)
* [✅] Implement GET document by ID
* [✅] Create list documents with pagination
* [✅] Add filtering by status/type
* [✅] Include metadata in responses
* **Outcome**: Full document information access

### Step 8 (Nov 4-10)
Goal: Documents Become Searchable
## Step 8.1
* [✅] PDF text extraction with pdfplumber
* [✅] Handle multiple PDF types
* [✅] Store extracted text in PostgreSQL
## Step 8.2
* [✅] Basic chunking (1000 chars, 200 overlap)
* [✅] Sentence boundary preservation
* [✅] Store chunks with position tracking
## Step 8.3
* [✅] Simple keyword search endpoint
* [✅] Test extraction quality
* [✅] Process 10+ sample documents
Deliverable: Upload PDF → Extract text → Search keywords

### Step 9 (Nov 11-17)
Goal: Intelligent Chunking + Embeddings
## Step 9.0 pgvector Setup 

  [✅] Install pgvector extension in PostgreSQL
  [✅] Create migration to add vector column to embeddings table
  [✅] Add Vector column type to SQLAlchemy model
  [✅] Create vector similarity index (HNSW or IVFFlat)
  Deliverable: Database ready for embeddings

 ## Step 9.1: Chunking Improvements (2-3 days)

  [✅] Enhance sentence boundary detection (spaCy/NLTK)
  [✅] Preserve paragraph/section structure
  [✅] Add rich metadata (headings, tables, page numbers)
  [✅] Optimize chunk size for BGE-M3 (512 tokens recommended)
  [✅] Test chunk quality on 10+ documents
  Deliverable: High-quality chunks ready for embedding

 ## Step 9.2: BGE-M3 Embedding Generation (2-3 days)

  [✅] Install BGE-M3 model (sentence-transformers)
  [✅] Implement embedding generation service
  [✅] Add batch processing (100 chunks at a time)
  [✅] Store embeddings in pgvector with proper indexing
  [✅] Add Celery task for async embedding generation
  Deliverable: Documents embedded and stored

 ## Step 9.3: Vector Similarity Search (2-3 days)

  [✅] Implement vector-only search endpoint
  [✅] Use cosine similarity with pgvector
  [✅] Return top-k results with similarity scores
  [✅] Test retrieval accuracy (measure recall@10)
  [✅] Benchmark search latency (<200ms target)
  Deliverable: Working semantic search (vector-only, >80% recall)

### Step 10 (Nov 18-24)
Goal: Hybrid Retrieval + Reranking
## Step 10.1
* [✅] BM25 + Vector fusion (RRF)
* [✅] Implement 4-stage retrieval pipeline
* [✅] Add metadata filtering
## Step 10.2
* [✅] Cross-encoder reranking (MiniLM-L6)
* [✅] MMR for diversity
* [✅] Result deduplication
## Step 10.3
* [✅] Citation extraction from chunks
* [✅] Source tracking and versioning
* [✅] Performance optimization
Deliverable: /search endpoint with citations, <500ms latency

### Step 11: Answer Generation with Verification
  Goal: Generate verified answers with citations using local LLM

  ## Step 11.1: Ollama LLM Integration
    [✅] Set up Ollama with Qwen2-7B model
    [✅] Create prompt templates for RAG
    [✅] Context window management (max 8K tokens)
    [✅] Proposition-based chunking (3-5 claims per chunk)

  ## Step 11.2: Chain-of-Verification
    [✅] Self-questioning verification phase
    [✅] Exact quote matching against retrieved passages
    [✅] Hallucination detection

  ## Step 11.3: Citation & Confidence
    [✅] Abstention logic (no answer → explicit statement)
    [✅] Confidence scoring per claim
    [✅] Citation formatting [1][2] with source links
  Deliverable: POST /api/v1/answer endpoint with verified citations

## Step 11.4: Configurable Verification Profiles (Completed Dec 2024)
* [✅] Create verification_profiles.py with 5 preset levels
  - VERY_HIGH: Maximum strictness for legal/medical (>98% accuracy)
  - HIGH: Production default (>95% accuracy)
  - MEDIUM: Balanced for internal tools (>90% accuracy)
  - LOW: Lenient for exploratory queries (>85% accuracy)
  - VERY_LOW: Minimal verification for speed (>80% accuracy)
* [✅] Integrate profile system with all services
  - QuoteMatchingService: Uses profile similarity thresholds
  - HallucinationDetector: Uses profile weights and contradiction settings
  - ConfidenceCalculator: Uses profile confidence weights
  - AbstentionService: Uses profile abstention thresholds
  - VerificationService: Uses profile temperature and removal thresholds
* [✅] Add VERIFICATION_LEVEL setting to config and .env.example
* [✅] Implement profile validation and caching
* [✅] Write comprehensive unit tests for all profiles
* [✅] Create integration tests for verification levels
Deliverable: Single VERIFICATION_LEVEL setting controls all verification parameters

### Step 12 (Dec 2-8)
Goal: Quick Wins & Demo Foundation
## Step 12.1: Database Automation ✅ COMPLETE (Nov 5, 2025)
* [✅] Set up Alembic migration framework
* [✅] Fix database credentials (standardized to docker-compose.yml)
* [✅] Install pgvector extension (switched to pgvector/pgvector:pg15 image)
* [✅] Generate initial migration from models
* [✅] Successfully run migration (6 tables created)
* **Documentation**: See `dev/completed/step12-database-migration-fix.md`
## Step 12.2: Deployment Infrastructure
* [] Create backend/Dockerfile for FastAPI app
* [] Create production docker-compose.yml (app + services)
* [] Add deployment scripts (deploy.sh, health_check.sh)
## Step 12.3: Demo Data Pipeline
* [] Create seed_demo.py with 5-10 sample PDFs
* [] Add sample queries JSON for testing
* [] Pre-process demo documents for instant demo
## Step 12.4: Progress Audit
* [✅] Mark Step 10.1 (Hybrid search) as complete
* [✅] Mark Step 10.3 (Citation extraction) as complete
* [✅] Update documentation with current state
Deliverable: One-command deployment (docker-compose up) with demo data

## Step 12.5: Claude Code Development Infrastructure (Dec 5-6) - LIGHTWEIGHT
Goal: Essential productivity tools for faster UI development (Step 13)

## Step 12.5.1: Core Setup (2 hours) ✅ COMPLETE
* [✅] Streamline CLAUDE.md to ~150 lines (project-specific only)
* [✅] Create .claude/ directory structure (skills, hooks, agents, commands)
* [✅] Implement skill-activation-prompt.ts hook (auto-activate skills)
* [✅] Implement post-tool-use-tracker.sh hook (track file edits)
* [✅] Set up dev/active/ directory for dev docs system

## Step 12.5.2: Essential Skills (1 hour) ✅ COMPLETE
* [✅] Create skill-rules.json for auto-activation configuration
* [✅] Create python-fastapi-dev skill (basic FastAPI/Pydantic patterns)
* [✅] Create testing-patterns skill (pytest patterns and best practices)

## Step 12.5.3: Workflow Commands (1 hour) ✅ COMPLETE
* [✅] Create /dev-docs slash command (generate plan/context/tasks)
* [✅] Create /dev-docs-update slash command (update before compaction)
* [✅] Create /test-all slash command (run full pytest suite)

Deliverable: 2-3x productivity boost for UI development. Skills auto-activate, dev docs survive context resets, faster feature implementation.
Time: 3-4 hours (minimal, focused on immediate value)
Note: Heavy modular architecture work moved to Step 15 (after UI + E2E tests complete)

**Step 12.5 COMPLETE** ✅ Claude Code infrastructure fully operational!

### Step 13 (Dec 9-22)
Goal: Enterprise-Grade Frontend Development (1-2 Week MVP)

**Tech Stack:** Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui + React Query
**Design System:** Modern minimalism with electric teal accent, Inter font, responsive mobile-first
**Approach:** Hybrid (template-inspired layout + custom QueryBox features)

**Dev Docs:** Created in `dev/active/querybox-frontend/` (plan.md, context.md, tasks.md)
- 200+ granular tasks organized by day
- Complete API integration guide
- TypeScript types mapped from backend schemas
- Component patterns and code examples

## Week 1: Setup + Core Features (Day 1-7)

### Day 1-2: Project Setup + Design System
* [] Initialize Next.js 14 with TypeScript + Tailwind CSS
* [] Install dependencies (React Query, Axios, react-hook-form, Zod)
* [] Setup shadcn/ui (install core components: button, card, input, dialog, table, etc.)
* [] Create directory structure (app routes, components, lib/api)
* [] Configure environment (.env.local with NEXT_PUBLIC_API_URL)
* [] Setup design system (custom colors, Inter font, Tailwind config)
* [] Create base utilities (formatters, validators, constants)
* [] Create TypeScript types from backend schemas (document.ts, search.ts, answer.ts)
* [] Setup API client (Axios with interceptors, error handling)
* [] Create React Query provider and hooks (useDocuments, useSearch, useAnswer)

### Day 3-4: Layout Components + Document Management
* [] Create layout components (Sidebar, Topbar, PageHeader)
* [] Build dashboard layout (sidebar + topbar + main content)
* [] Implement responsive layout (mobile: hamburger, tablet: collapsible, desktop: expanded)
* [] Create common components (LoadingSpinner, EmptyState, ErrorBoundary, ConfirmDialog)
* [] Build DocumentUpload component (drag-drop with react-dropzone, validation, progress)
* [] Create upload page with multi-file support
* [] Build DocumentCard component (name, type, size, status badge, actions)
* [] Create DocumentTable component (sortable, paginated)
* [] Build DocumentStatus component (real-time processing indicator with polling)
* [] Create DocumentFilters component (filter by status, type, date)
* [] Build document list page (card/table toggle, pagination, filters, search)
* [] Create document details page (metadata, processing status, delete with confirmation)

### Day 5-6: Search Interface
* [] Create SearchBar component (debounced input, clear button, Enter key support)
* [] Build SearchFilters component (strategy radio buttons, advanced filters collapsible)
  - Document types multi-select
  - Date range picker
  - Quality threshold slider
  - Enable reranking/MMR checkboxes
* [] Create SearchResult component (document info, relevance score, snippet, citations)
* [] Build SearchResults component (list with loading skeleton, empty state, result count)
* [] Create CitationHighlight component (color-coded by quality: green/yellow/red)
* [] Build CitationTooltip component (hover details: passage, page, section, confidence)
* [] Create search page (SearchBar + filters sidebar + results + pagination)
* [] Implement URL state management (query and filters in URL params)
* [] Add loading, error, and empty states

### Day 7: Chat Interface (Part 1)
* [] Create ChatInterface component (scrollable message area, auto-scroll)
* [] Build ChatMessage component (user/assistant bubbles, timestamp, avatar)
* [] Create ChatInput component (auto-resize textarea, send button, character count)
* [] Build quality level selector (tabs: Fast/Verified/Enhanced with estimated times)
* [] Create AnswerCard component (answer text with citation refs [1][2], processing time)
* [] Build ConfidenceIndicator component (color-coded progress bar 0-100%, breakdown tooltip)
* [] Create chat page layout with quality selector
* [] Add loading state with estimated time display

## Week 2: Chat + Analytics + Polish (Day 8-14)

### Day 8-9: Chat Interface (Part 2) + Advanced Features
* [] Create CitationList component (numbered accordion, expandable citations)
  - Document name with link
  - Passage text highlighted
  - Page and section
  - Confidence score and quality badge (STRONG/MEDIUM/WEAK)
* [] Integrate citations into AnswerCard (clickable inline numbers, scroll to citation)
* [] Build AbstractionAlert component (special warning alert)
  - Show abstention message
  - Display factors (low confidence, high hallucination, no evidence)
  - Suggestions (refine query, upload more docs, specify documents)
* [] Create confidence breakdown component (detailed metrics)
  - Overall confidence
  - Average passage relevance, quote quality, verification agreement
  - Citation count breakdown (Strong/Medium/Weak)
* [] Add "Advanced Details" collapsible section (hallucination probability, propositions)
* [] Implement chat history display (conversation state management)
* [] Add clear chat functionality

### Day 10-11: Analytics Dashboard
* [] Create StatsCard component (KPI with number, label, trend indicator, icon)
* [] Build KPI cards (Total Docs, Storage Used, Ready for Search, Failed Docs)
* [] Create UploadTrendChart component (Recharts line chart, responsive, tooltip)
* [] Build DocumentTypeChart component (Recharts pie/bar chart, legend, colors)
* [] Create ProcessingStatusChart component (bar chart by status, color-coded)
* [] Build SystemHealthCard component (health indicators with status colors)
  - Database, Redis, Storage, Ollama status
  - Disk space usage progress bar
  - Last checked timestamp
* [] Create analytics page (grid layout: stats cards, charts, system health)
* [] Add date range filter (7d, 30d, 90d, 1y, all)
* [] Implement auto-refresh (every 5 minutes)
* [] Update dashboard home page (redirect to analytics or show overview)

### Day 12-13: Responsive Design + Accessibility + Polish
* [] Mobile responsive (<768px)
  - Sidebar to hamburger menu with slide-in drawer
  - Document list: card layout only (full-width)
  - Search: full-width with filters in bottom sheet
  - Chat: single-column with sticky input
  - Analytics: 1-2 column stacked layout
* [] Tablet responsive (768-1024px)
  - Collapsible sidebar with toggle
  - Document list: compact table
  - Search: 2-column (filters + results)
  - Analytics: 2-column charts
* [] Desktop responsive (>1024px)
  - Full expanded sidebar
  - Document list: full table with all columns
  - Search: 3-column layout
  - Analytics: 3-4 column layout
* [] Accessibility (WCAG 2.1 AA)
  - Keyboard navigation (Tab, Enter, Escape, Arrow keys)
  - ARIA labels for icon buttons
  - Focus indicators on all interactive elements
  - Color contrast ≥4.5:1 for text
  - Semantic HTML (nav, main, article headings)
  - Screen reader support
* [] Error handling
  - Global error handler in API client
  - Error boundaries on major pages
  - User-friendly error messages (400, 401, 404, 413, 429, 500)
  - Toast notifications for all error cases
* [] Loading states
  - Skeleton loaders (document list, search results, analytics)
  - Progress indicators (file upload, chat answer generation)
  - Loading with estimated time for chat
* [] Empty states
  - Documents list: "Upload your first document" CTA
  - Search results: "No results found" with suggestions
  - Chat: "Ask a question" with examples
* [] Optimistic updates
  - Document delete (remove immediately, revert on error)
  - Document upload (add to list with "uploading" status)
* [] Form validation
  - File upload: type and size validation before submit
  - Search: min query length (3 chars)
  - Chat: character count (1-500 chars)
* [] Polish
  - Consistent spacing (Tailwind scale)
  - Smooth transitions (hover, fade, slide)
  - Typography hierarchy (text-2xl → text-xl → text-base → text-sm)
  - Icon consistency (lucide-react, 20px default)

### Day 14: Testing + Deployment + Documentation
* [] Manual testing
  - Upload flow (single, multiple, invalid type, too large, processing status)
  - Document management (list, pagination, sorting, filtering, delete, search by name)
  - Search (keyword, semantic, hybrid, filters, citations)
  - Chat (all quality levels, citations, confidence, abstention)
  - Analytics (stats, charts, date range, health)
  - Responsive (mobile, tablet, desktop)
  - Accessibility (keyboard, screen reader, contrast)
* [] Cross-browser testing (Chrome, Firefox, Safari, Edge)
* [] Performance testing
  - Lighthouse audit (Performance ≥90, Accessibility ≥95)
  - Bundle size check (<500KB gzipped)
  - Test with 3G throttling (page load <5s)
* [] Code quality
  - Run ESLint (fix errors and warnings)
  - TypeScript compile (no `any` types)
  - Code review (reusability, naming, error handling)
* [] Production build
  - Build: `npm run build`
  - Test locally: `npm run start`
* [] Deploy to Vercel
  - Connect GitHub repo
  - Configure environment variables
  - Deploy and test
* [] Documentation updates
  - Update README.md (frontend setup, development, deployment)
  - Update ARCHITECTURE.md (frontend architecture, components)
  - Update ProgressTracker.md (mark Step 13 complete)
  - Update CLAUDE.md (current phase to Step 14)
  - Create frontend/README.md (tech stack, structure, development guide)

**Deliverable:**
- ✅ Functional UI at localhost:3000 (Vercel deployment)
- ✅ All 4 MVP features complete (Upload, Search, Chat, Analytics)
- ✅ Full backend API integration with TypeScript types
- ✅ Real-time document processing status updates
- ✅ Citation system with quality indicators (STRONG/MEDIUM/WEAK)
- ✅ Confidence scoring and abstention handling
- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Accessible (WCAG 2.1 AA compliant)
- ✅ Error handling and loading states throughout
- ✅ Professional, premium UI/UX (distinct from generic dashboards)
- ✅ Complete documentation and deployment guide

**Success Criteria:**
- All backend endpoints integrated and working
- Upload → Process → Search → Chat flow fully functional
- Real-time status updates with 2-3s polling
- Citations display correctly with color coding
- Performance: Initial load <2s, search results <500ms
- Lighthouse scores: Performance ≥90, Accessibility ≥95
- Zero console errors in production build

**Future Enhancements (Step 14+):**
- Step 14: Replace Recharts with Tremor for advanced analytics
- Step 15: Multi-client white-labeling (themes, logos, feature toggles)
- Step 16+: Real-time WebSocket, annotations, saved searches, export

### Step 13.5 (Jan 5-6)
Goal: Logging & Monitoring Infrastructure (Phase 1 - Development)

**Context:**
Before E2E testing, implement unified logging and monitoring to replace terminal-only log checking. Two-phase approach: Better Stack (immediate) + SigNoz + OTEL-Collector (production).

**Dev Docs:** `dev/active/logging-monitoring/` (plan.md, context.md, tasks.md)

## Step 13.5.1: Better Stack Integration (2 hours)
* [ ] Sign up for Better Stack (Logtail) and get source token
* [ ] Backend: Install logtail-python and configure structlog
* [ ] Backend: Add middleware for multi-tenant labels (client_id, service, module)
* [ ] Frontend: Install @logtail/browser and create logger wrapper
* [ ] Frontend: Integrate with error boundary and API client
* [ ] Celery: Add Logtail handler to worker logging
* [ ] Test: Upload → Search → Chat flow with live-tail monitoring
* [ ] Verify: All logs (frontend, backend, Celery) visible in Better Stack UI

**Deliverable:**
- ✅ Unified log viewing in Better Stack dashboard
- ✅ Live-tail capability for real-time debugging
- ✅ Searchable logs with filters (service, level, client_id, module)
- ✅ Error detection with stack traces
- ✅ Ready for E2E testing with comprehensive visibility

**Success Criteria:**
- All services (frontend, backend, Celery) logging to Better Stack
- Can filter by client_id, service, module, error level
- Live-tail works during testing (< 5 second latency)
- Error logs include stack traces and context
- Zero cost (3 GB/day free tier sufficient for development)

**Architecture:**
```
┌─────────────┐
│   FastAPI   │────┐
│   Next.js   │────┼──▶ Better Stack Cloud
│   Celery    │────┘     (Unified Dashboard)
└─────────────┘
```

**Note:** Phase 2 (SigNoz + OTEL-Collector) scheduled for Step 16.4 (Production Deployment)

### Step 13.6: End-to-End Integration Test Suite (Jan 11-12) ✅ COMPLETE
Goal: Comprehensive E2E Testing (Safety Net for Future Refactoring)

**Context:** Before proceeding with vector store optimization and modular architecture refactoring, create comprehensive E2E tests that validate the entire pipeline from upload through search.

## Step 13.6.1: E2E Test Implementation (4 hours) ✅ COMPLETE
* [✅] Create test_e2e_pipeline.py with complete upload → extract → chunk → embed → search flow
* [✅] Implement test helpers for running tasks outside Celery (direct service calls)
* [✅] Add fixtures for sample documents (markdown, PDF)
* [✅] Create comprehensive test for full pipeline with status tracking
* [✅] Add error handling tests (invalid files, empty search results)
* [✅] Implement duplicate detection test
* [✅] Add health check tests for search services
* [✅] Fix timezone handling in status tracker (SQLite compatibility)
* [✅] Test all processing stages: extraction (1989 chars), chunking (1 chunk), embedding (1 vector)

## Step 13.6.2: Test Documentation & Tooling (2 hours) ✅ COMPLETE
* [✅] Create run_e2e_tests.py script with service health checks
* [✅] Write comprehensive README_E2E.md with usage guide, troubleshooting, CI/CD examples
* [✅] Document test execution times and performance benchmarks
* [✅] Add service dependency documentation (PostgreSQL required for full tests)
* [✅] Include examples for running tests in development and CI

**Results:**
- ✅ Complete E2E test validates: Upload (✓), Extraction (✓), Chunking (✓), Embedding (✓)
- ✅ Processing pipeline fully tested with 800+ lines of test code
- ✅ Search tests work with PostgreSQL (SQLite lacks full-text search functions)
- ✅ Test execution: ~12-15 seconds for full pipeline
- ✅ Provides safety net for Phase 4 (Vector Store) and Step 15 (Modular Architecture)

**Files Created:**
- `backend/tests/integration/test_e2e_pipeline.py` (800+ lines)
- `backend/scripts/run_e2e_tests.py` (automated runner)
- `backend/tests/integration/README_E2E.md` (comprehensive documentation)

Deliverable: ✅ Production-ready E2E test suite with comprehensive documentation

---

### Step 13.7: Phase 4 - Vector Store Optimization (Jan 12-13) ✅ COMPLETE
Goal: Qdrant Infrastructure for 10x Faster Vector Search (Plug-and-Play Ready)

**Context:** Built complete Qdrant infrastructure but kept disabled (`ENABLE_QDRANT=false`) until after Supabase migration or if performance requires it. PostgreSQL remains primary source of truth.

**Architecture Strategy: Hybrid (PostgreSQL Primary + Qdrant Speed Layer)**
```
PostgreSQL/Supabase (Source of Truth)
├─ Documents, chunks, metadata, relations
├─ pgvector vectors (reliable fallback)
└─ ACID guarantees
         ↓ one-way sync (when enabled)
Qdrant (Speed Layer - DISABLED for now)
├─ Vectors only + minimal payload
├─ 10x faster HNSW search (<20ms)
└─ Automatic circuit breaker failover
```

## Phase 4.1: Qdrant Setup ✅ COMPLETE
* [x] Choose deployment: Hybrid approach (Local Docker + Cloud configs)
* [x] Add Qdrant service to docker-compose.yml (ports 6333/6334, 4GB memory)
* [x] Add `qdrant-client==1.7.0` to requirements.txt
* [x] Configure .env variables (QDRANT_URL, API_KEY, COLLECTION, HNSW params)
* [x] Create environment templates (.env.local, .env.demo, .env.production)
* [x] Test connection: Qdrant container starts successfully

## Phase 4.2: Implement QdrantStore ✅ COMPLETE
* [x] Create `backend/app/services/search/vector_stores/qdrant_store.py` (600+ lines)
* [x] Implement `QdrantStore(VectorStore)` with full VectorStore interface
* [x] Collection schema: 1024-dim (BGE-M3), cosine similarity, HNSW index
* [x] Implement methods: index(), search(), delete(), count(), health_check()
* [x] Add batch upsert support (500 vectors per batch with parallel upload)
* [x] Implement metadata filtering and payload structure (preserves all pgvector metadata)
* [x] Add circuit breaker pattern (3 states: closed/open/half-open)
* [x] Error handling and connection retry logic

## Phase 4.3: Migration Script ✅ COMPLETE (Script ready, not run)
* [x] Create `backend/scripts/migrate_to_qdrant.py` (500+ lines, executable)
* [x] Read all embeddings from PostgreSQL (batch processing, 500 vectors/batch)
* [x] Transform to Qdrant format (vector + payload with chunk_id, document_id, text)
* [x] Batch upload to Qdrant with progress tracking (log every 1000 vectors)
* [x] Make idempotent (can re-run safely with upsert)
* [x] Add dry-run mode and validation
* [x] **Status**: Script ready but not needed (no production data to migrate)

## Phase 4.4: Parallel Operation & Routing ⏭️ DEFERRED (~1 hour when enabling)
* [⏭️] Add ENABLE_QDRANT flag to settings (already in config.py with ENABLE_QDRANT: bool = True)
* [⏭️] Implement dual indexing: Write to PostgreSQL (always) + Qdrant (if enabled)
* [⏭️] Create search routing logic: Qdrant (if available) → fallback to pgvector
* [⏭️] Update embedding_service.py for dual-write
* [⏭️] Update hybrid_search_service.py for smart routing
* [x] Circuit breaker pattern already implemented in QdrantStore
* [x] Factory.py already includes Qdrant provider
* [⏭️] Add metrics logging (search_provider used, latency)

## Phase 4.5: Testing & Validation ⏭️ DEFERRED (will test when enabled)
* [⏭️] Correctness test: Run 50 queries on both stores, verify results match
* [⏭️] Performance benchmark: Measure latency (p50, p95, p99) - expect 10x improvement
* [⏭️] Load test: 50-100 concurrent queries
* [⏭️] Fallback test: Stop Qdrant, verify automatic switch to pgvector
* [⏭️] Error handling test: Invalid queries, timeout scenarios
* [⏭️] Update E2E tests to include Qdrant scenarios
* [⏭️] Document performance results

**Deliverable:**
- ✅ Qdrant infrastructure complete and tested (Local Docker setup)
- ✅ QdrantStore implementation (600+ lines, production-grade)
- ✅ Migration script ready (500+ lines, idempotent)
- ✅ Circuit breaker pattern for automatic failover
- ✅ Configuration system (3 environment templates)
- ✅ Comprehensive activation guide (QDRANT_ACTIVATION.md)
- ✅ Session summary with all decisions (PHASE4_QDRANT_SESSION_SUMMARY.md)
- ✅ ENABLE_QDRANT=false in working configs (disabled until needed)
- ✅ Plug-and-play ready: <5 minutes to activate when needed

**Current Status:**
- Infrastructure: ✅ Complete and verified
- Integration: ⏭️ Deferred (~1 hour work when enabling)
- Decision: Keep disabled until Supabase migration or if performance issue
- Activation: 3-step process documented, ready when needed

**Future Activation Path** (When ready):
1. Set `ENABLE_QDRANT=true` in .env
2. Ensure Qdrant running (`docker-compose up -d qdrant`)
3. Restart backend (`docker-compose restart backend`)
4. Implement integration (~1 hour):
   - Dual-write in embedding service
   - Smart routing in search service
   - Test and benchmark

**Time Spent:** ~4 hours (infrastructure + documentation)
**Time Deferred:** ~1 hour (integration when enabling)

**Next Steps:**
- Continue with Supabase migration (authentication + simplicity)
- Enable Qdrant if search latency >100ms p95 or vector count >500K
- Phase 5: Multi-Query RAG (after deciding on vector store strategy)
- Phase 6: RAGAs Evaluation & Tuning

---

### Step 14 (Jan 15-20)
Goal: Live Demo Deployment & Documentation (Deprecated - Merged into Step 13)

**Note:** Original Step 14 planning merged into Step 13.6 (E2E tests) and Step 13.7 (Phase 4). Live demo deployment will be handled as part of Step 15 completion.

## Step 14.2: Demo Deployment (2 days)
* [] Deploy to Railway/Render/DigitalOcean (choose platform)
* [] Configure production environment variables
* [] Set up SSL/HTTPS with custom domain (querybox.io)
* [] Test full deployment end-to-end (upload → search → chat)
* [] Create demo user accounts with sample data
* [] Set up monitoring (Sentry for errors, analytics for usage)
Deliverable: Live demo accessible at querybox.io/demo

## Step 14.3: Documentation & Video (2 days)
* [] Seed production with diverse demo documents
* [] Record video walkthrough (5-7 minutes, upload → search → chat)
* [] Write user guide (getting started, best practices)
* [] Create troubleshooting guide (common issues)
* [] Set up health monitoring and alerting
Deliverable: Public demo with documentation, ready for user testing

**Why This Step is Critical:**
- ✅ E2E tests become safety net for Step 15 modular refactoring
- ✅ Live demo validates system works end-to-end before big changes
- ✅ Can confidently refactor knowing tests will catch regressions
- ✅ Provides baseline performance metrics to maintain during refactoring

### Step 15 (Dec 30 - Jan 19)
Goal: Modular Architecture Refactoring (Transform into Configurable Platform)

**Context:** Backend complete (Steps 1-12), Frontend complete (Step 13), E2E tests provide safety net (Step 14). Can now refactor with confidence.

**Vision:** Modular platform where components (parsers, embedders, retrievers, LLMs) are swappable per client via configuration, not code changes.

## Step 15.1: Modular Architecture Foundation (Week 1: Dec 30 - Jan 5, 12-16 hours) ✅ COMPLETE
* [✅] Create base classes (VectorStore abstract base)
* [✅] Implement provider factory pattern (get_vector_store factory)
* [✅] Build configuration system (settings-based provider selection)
* [✅] Create provider implementations:
  - PgVectorStore → implements VectorStore base
  - Ready for QdrantStore, LanceDB, etc.
* [✅] Refactor existing services to use factory pattern:
  - VectorSearchService uses get_vector_store()
  - Config-driven provider selection (VECTOR_STORE setting)
* [✅] Clean separation of concerns (storage vs search logic)
* [✅] Update ARCHITECTURE.md with vector store patterns

**Status:** ✅ Phase 1 Complete - Foundation ready for Qdrant integration
**Files:**
- `backend/app/services/search/vector_stores/base.py` (VectorStore ABC)
- `backend/app/services/search/vector_stores/factory.py` (get_vector_store)
- `backend/app/services/search/vector_stores/pgvector_store.py` (PostgreSQL impl)

Deliverable: ✅ Modular vector store foundation, ready for multi-provider integration

## Step 15.2: Multi-Provider Implementation (Week 2: Jan 6-12, 12-16 hours)
* [] Implement OpenAIEmbedder (BaseEmbedder) with API integration
* [] Implement CohereEmbedder (BaseEmbedder) with API integration
* [] Implement DoclingParser (BaseParser) for advanced PDF layout
* [] Implement UnstructuredParser (BaseParser) for universal document types
* [] Implement OpenAILLM (BaseLLM) with streaming support
* [] Implement AnthropicLLM (BaseLLM) with Claude integration
* [] Register all providers in config/providers.yaml
* [] **Run E2E tests with each provider** - validate swappability works
* [] Create provider comparison benchmarks (speed, quality, cost)
* [] Document each provider (capabilities, configuration, limitations)
Deliverable: 2-3 options per component, all tested and documented

## Step 15.3: Client Configuration System (Week 3: Jan 13-19, 8-12 hours)
* [] Implement configuration API endpoints:
  - GET /api/v1/clients/{id}/config (read config)
  - PUT /api/v1/clients/{id}/config (update config)
  - GET /api/v1/providers (list available providers)
* [] Build admin UI for client configuration:
  - Client list view
  - Configuration editor with provider dropdowns
  - Provider testing/validation tools
  - Configuration profiles (SaaS, On-Prem, Hybrid)
* [] Add configuration validation (API keys present, models available)
* [] Create configuration guide with examples
* [] Write migration guide for existing deployments
* [] **Final E2E test sweep** - all providers, all configurations
* [] Verify backward compatibility - default config = current behavior
Deliverable: Fully configurable platform, per-client customization, admin UI complete

**Success Criteria:**
- ✅ All E2E tests pass with every provider combination
- ✅ Can switch embedder via config (no code changes)
- ✅ Existing demo continues working (backward compatible)
- ✅ Documentation complete for adding custom providers
- ✅ 3+ providers per component category available

### Step 16 (Jan 20 - Feb 2)
Goal: User Feedback & Discovery
## Step 16.1: User Monitoring
* [] Track query patterns and frequency
* [] Monitor search latency (p50, p95, p99)
* [] Log failed queries and errors
* [] Record user feedback and feature requests
## Step 16.2: Performance Profiling
* [] Identify actual bottlenecks from logs
* [] Profile slow queries (>500ms)
* [] Measure embedding generation time
* [] Track database query performance
## Step 16.3: Quality Analysis
* [] Collect queries where users report poor results
* [] Analyze hallucination instances reported
* [] Review citation accuracy feedback
* [] Identify document types with extraction issues

## Step 16.4: Production Observability Infrastructure (Phase 2 - 6-8 hours)
**Context:** Self-hosted, production-grade logging and monitoring with vendor-agnostic architecture.

**Dev Docs:** `dev/active/logging-monitoring/` (Phase 2 sections)

**Tasks:**
* [ ] Install OpenTelemetry Collector via Docker
* [ ] Install SigNoz (self-hosted APM platform)
* [ ] Configure otel-collector-config.yaml with processors for enrichment
* [ ] Backend: Install OpenTelemetry Python SDK and auto-instrument FastAPI/Celery
* [ ] Frontend: Install OpenTelemetry Web SDK and auto-instrument fetch/XHR
* [ ] Implement multi-tenant label propagation (client_id, service, module)
* [ ] Configure OTLP exporter to send telemetry to collector
* [ ] Update docker-compose.yml with otel-collector service
* [ ] Create service overview dashboard in SigNoz
* [ ] Create per-client dashboard with client_id filters
* [ ] Set up error rate and latency alerts (p95, p99)
* [ ] Test distributed tracing: Next.js → FastAPI → Celery → LLM
* [ ] Verify unlimited log retention and zero cost operation
* [ ] Document switch from Better Stack to SigNoz

**Architecture:**
```
┌─────────────┐     ┌──────────────┐     ┌──────────┐
│   FastAPI   │────▶│              │────▶│          │
│   Next.js   │     │ otel-        │     │  SigNoz  │
│   Celery    │────▶│ collector    │────▶│ (self-   │
│             │     │ (middleware) │     │ hosted)  │
└─────────────┘     └──────────────┘     └──────────┘
    Apps              Buffering/           Observability
                      Enrichment           Backend
```

**Benefits:**
- Vendor-agnostic: Can switch to Grafana/Honeycomb without changing app code
- Unlimited logs with long retention (no 3-day limit)
- Full control over data (privacy and compliance)
- Production-grade APM, distributed traces, and metrics
- Zero cost (completely self-hosted and open-source)

Deliverable: Data-driven insights report with prioritized optimization list + Production observability platform

### Step 17 (Feb 3-16)
Goal: Data-Driven Performance Optimization
## Step 17.1: Performance Fixes (Feb 3-6)
* [] Optimize identified slow queries
* [] Add caching for frequent user queries
* [] Implement connection pooling improvements
* [] Database index optimization (actual bottlenecks)
## Step 17.2: Scale & Speed (Feb 7-10)
* [] Add semantic cache (SimHash) for duplicate queries
* [] Implement cascade retrieval if needed
* [] Batch processing optimization for peak times
* [] Hot tier indexing for popular documents
## Step 17.3: Load Testing (Feb 11-16)
* [] Load test with realistic user patterns
* [] Test concurrent user limits (50-100 users)
* [] Optimize for measured bottlenecks
* [] Document performance characteristics
Deliverable: P50 <200ms retrieval, handles measured user load

### Step 18 (Feb 17 - Mar 2)
Goal: Data-Driven Quality Assurance
## Step 18.1: Golden Test Set (Feb 17-20)
* [] Build test set from REAL user queries (50-100 Q&A pairs)
* [] Validate groundedness on reported issues
* [] Test hallucination detection on edge cases
* [] Measure accuracy improvements
## Step 18.2: Adversarial Testing (Feb 21-24)
* [] Test conflicting document scenarios users encountered
* [] Validate temporal consistency issues
* [] Test abstention logic on ambiguous queries
* [] Handle edge cases from user reports
## Step 18.3: Accuracy Dashboard (Feb 25 - Mar 2)
* [] Create accuracy metrics dashboard
* [] Add error analysis tools
* [] Generate quality reports
* [] Implement continuous evaluation
Deliverable: >95% accuracy on real user queries, <5% abstention rate

### Step 19 (Mar 3-16)
Goal: Scale & Production Hardening
## Step 19.1: Advanced Features
* [] Multi-document conversation context
* [] Document version comparison
* [] Advanced filtering and faceted search
* [] Export and sharing capabilities
## Step 19.2: Security & Compliance
* [] Enhanced authentication (OAuth/SSO if needed)
* [] Rate limiting and abuse prevention
* [] Audit logging for enterprise
* [] Data retention policies
## Step 19.3: Launch Preparation
* [] Complete API documentation
* [] Create video demo
* [] Write case studies from pilots
* [] Prepare marketing materials
Deliverable: Production-ready system, pilot success stories, launch-ready

---

## 🎯 Revised Roadmap Summary (Updated Jan 2025)

**✅ Weeks 12-13.7 (Dec 2 - Jan 13):** Backend MVP complete, E2E tests, Qdrant infrastructure ready
**⏳ Week 13.8+ (Jan 14+):** Choose next direction:
  - **Path A**: Supabase Migration → Authentication + simplicity
  - **Path B**: Phase 5 (Multi-Query RAG) + Phase 6 (RAGAs) → Quality improvements
  - **Path C**: Frontend Development (Step 13) → User-facing demo
**⏳ Weeks 14-15 (Jan 21-Feb 2):** Frontend development OR Modular architecture completion
**Week 16 (Feb 3-9):** User feedback → Pilot users, usage data collection
**Weeks 17-18 (Feb 10-23):** Data-driven optimization → Measured bottlenecks
**Weeks 19-20 (Feb 24-Mar 9):** Quality assurance → >95% accuracy on real queries
**Week 21+ (Mar 10+):** Production hardening → Enterprise-ready, launch preparation

⚡ **Daily Execution Pattern (Balanced Approach)**
- Morning (3-4 hours): Core feature implementation
- Afternoon (2-3 hours): Testing and debugging
- Evening (1-2 hours): Code review and planning

🚨 **Critical Checkpoints (Revised Strategy)**
- **Step 12 End (Dec 8):** If Docker setup fails → Simplify to local-only first
- **Step 13 End (Dec 22):** If frontend behind schedule → Deploy basic search UI only, skip chat
- **Step 14 End (Dec 29):** If deployment issues → Use free tier Railway/Render, optimize later
- **Step 15 End (Jan 19):** If E2E tests fail after refactoring → Roll back, fix incrementally
- **Step 16 End (Feb 2):** If no user traffic → Reach out to communities (Reddit, Discord, Twitter)
- **Step 17 End (Feb 16):** If no clear bottlenecks → Skip premature optimization, focus on quality

💡 **Current Phase: Ready for Next Direction**

**Backend Status:** ✅ 100% MVP Complete
- Full RAG pipeline operational (Steps 1-13.7)
- Hybrid search with reranking working
- Answer generation with verification and confidence scoring
- OpenRouter + OpenAI integration (Phase 3) ✅
- Comprehensive E2E test suite (Step 13.6) ✅
- Qdrant infrastructure ready (Phase 4 - disabled until needed) ✅
- Modular architecture foundation (Step 15.1) ✅
- 48+ test files with excellent coverage

**Choose Next Direction:**

**Option 1: Supabase Migration** (Recommended for MVP)
- Migrate from PostgreSQL to Supabase
- Get authentication working (user sign-up, login, session management)
- Leverage Supabase pgvector (same as current PostgreSQL)
- Enable Qdrant later if performance becomes issue
- **Time**: 4-6 hours
- **Benefit**: Simplifies auth, cloud-ready, production-grade

**Option 2: Quality Improvements** (If quality is priority)
- **Phase 5**: Multi-Query RAG (3 hours) - 15-25% better accuracy
- **Phase 6**: RAGAs Evaluation (4 hours) - Data-driven tuning
- **Benefit**: Higher accuracy, measurable quality metrics

**Option 3: Frontend Development** (If demo is priority)
- Step 13: Build Next.js frontend (1-2 weeks)
- Upload → Search → Chat UI with citations
- **Benefit**: User-facing demo, stakeholder visibility

**Option 4: Continue Modular Architecture** (Step 15.2+)
- Add more providers (embedding, LLM, parsing)
- Build per-client configuration system
- **Benefit**: Platform flexibility, multi-tenant ready

**Recommendation**: Start with Supabase migration for authentication simplicity, then decide between quality improvements or frontend based on priorities.


<!-- ### Step 8: Upload Status Tracking (3 hours)
* [ ] Create status update mechanism
* [ ] Implement progress tracking
* [ ] Add Redis-based status cache
* [ ] Design status transition logic
* **Outcome**: Real-time processing visibility

## ⏳ Day 5: Testing & Refinement [PENDING]
### Step 9: Upload Flow Testing (3 hours)
* [ ] Test various file types
* [ ] Verify size limit enforcement
* [ ] Check metadata accuracy
* [ ] Validate error handling
* **Outcome**: Verified upload reliability

### Step 10: Performance Optimization (2 hours)
* [ ] Implement streaming for large files
* [ ] Add connection pooling (Note: Already done in Day 1)
* [ ] Optimize database queries
* [ ] Profile and fix bottlenecks
* **Outcome**: Optimized upload performance

📅 Week 2: Advanced Upload Features
Day 1: Smart File Routing
Step 11: Large File Detection (3 hours)
* Outcome: Intelligent upload path selection
* Implement file size detection logic
* Create routing decision engine
* Design presigned URL generation
* Add direct upload markers
Step 12: Presigned URL Implementation (3 hours)
* Outcome: Direct-to-storage large uploads
* Generate S3/MinIO presigned URLs
* Create upload completion webhook
* Implement verification mechanism
* Update metadata post-upload
Day 2: Session Management
Step 13: Upload Session Creation (4 hours)
* Outcome: Trackable upload lifecycle
* Design session data structure
* Implement session creation in Redis
* Add session timeout logic
* Create session recovery mechanism
Step 14: Resumable Uploads (2 hours)
* Outcome: Failure-resistant uploads
* Implement chunked upload support
* Add progress persistence
* Create resume logic
* Handle partial upload cleanup
Day 3: Queue Integration
Step 15: Celery Setup (3 hours)
* Outcome: Asynchronous task processing
* Configure Celery with Redis broker
* Create worker configuration
* Implement task routing
* Add worker health monitoring
Step 16: Processing Task Creation (3 hours)
* Outcome: Automatic processing trigger
* Create document processing task
* Implement task queueing on upload
* Add priority handling
* Design retry configuration
Day 4: Error Recovery
Step 17: Transaction Management (3 hours)
* Outcome: Consistent state on failures
* Implement database transactions
* Add rollback mechanisms
* Create compensation logic
* Handle partial failures
Step 18: Storage Cleanup (2 hours)
* Outcome: No orphaned files
* Implement cleanup on failure
* Add scheduled cleanup tasks
* Create orphan detection
* Design storage audit trail
Day 5: Upload Pipeline Hardening
Step 19: Concurrent Upload Handling (3 hours)
* Outcome: Stable multi-user uploads
* Implement upload queuing
* Add rate limiting
* Test concurrent scenarios
* Optimize resource usage
Step 20: Comprehensive Error Handling (2 hours)
* Outcome: Graceful failure management
* Categorize error types
* Implement user-friendly messages
* Add detailed logging
* Create error recovery paths

📅 Week 3: Document Processing Pipeline
Day 1: Processing Architecture
Step 21: Event System Setup (4 hours)
* Outcome: Event-driven processing flow
* Create event publisher interface
* Implement event consumer
* Design event routing
* Add event persistence
Step 22: Processing Queue Design (2 hours)
* Outcome: Organized task management
* Create queue priority system
* Implement worker pool
* Add dead letter queue
* Design monitoring hooks
Day 2: PDF Processing
Step 23: PDF Parser Integration (4 hours)
* Outcome: Text extraction from PDFs
* Integrate PyMuPDF library
* Implement text extraction
* Handle various PDF types
* Add OCR detection logic
Step 24: Metadata Extraction (2 hours)
* Outcome: Rich document metadata
* Extract document properties
* Identify document structure
* Capture creation/modification dates
* Parse embedded metadata
Day 3: Text Processing
Step 25: Content Cleaning (3 hours)
* Outcome: Clean, processable text
* Remove formatting artifacts
* Handle special characters
* Normalize whitespace
* Preserve meaningful structure
Step 26: Chunking Implementation (3 hours)
* Outcome: Optimally sized text chunks
* Implement 1000-token chunking
* Add 200-token overlap
* Preserve sentence boundaries
* Track chunk relationships
Day 4: Storage & Indexing
Step 27: Chunk Storage (3 hours)
* Outcome: Persistent chunk data
* Design chunk storage schema
* Implement chunk saving
* Add chunk-document linking
* Create chunk retrieval logic
Step 28: Processing Status Updates (2 hours)
* Outcome: Real-time processing tracking
* Update status at each stage
* Implement progress calculation
* Add completion notifications
* Create status history
Day 5: Processing Validation
Step 29: Quality Checks (3 hours)
* Outcome: Verified processing quality
* Implement extraction validation
* Check chunk integrity
* Verify metadata completeness
* Add quality metrics
Step 30: Error Recovery (2 hours)
* Outcome: Self-healing processing
* Implement retry logic
* Add exponential backoff
* Create failure analysis
* Design manual intervention hooks

📅 Week 4: Production Readiness
Day 1: Performance Tuning
Step 31: Upload Optimization (3 hours)
* Outcome: Fast, efficient uploads
* Optimize file streaming
* Tune database queries
* Improve Redis usage
* Profile critical paths
Step 32: Processing Optimization (3 hours)
* Outcome: Rapid document processing
* Parallelize extraction tasks
* Optimize chunking algorithm
* Cache frequently accessed data
* Reduce memory footprint
Day 2: Scalability
Step 33: Load Testing (4 hours)
* Outcome: Verified performance limits
* Test 10+ concurrent uploads
* Process 50MB files
* Measure queue throughput
* Document bottlenecks
Step 34: Resource Management (2 hours)
* Outcome: Efficient resource usage
* Implement connection pooling
* Add memory management
* Create resource limits
* Design scaling triggers
Day 3: Reliability
Step 35: Fault Tolerance (3 hours)
* Outcome: System resilience
* Add circuit breakers
* Implement bulkheads
* Create fallback mechanisms
* Design graceful degradation
Step 36: Monitoring Setup (3 hours)
* Outcome: Complete observability
* Add Prometheus metrics
* Create key dashboards
* Implement alerting rules
* Design SLA tracking
Day 4: Security & Compliance
Step 37: Security Hardening (3 hours)
* Outcome: Secure upload pipeline
* Add input sanitization
* Implement virus scanning hooks
* Create audit logging
* Design access controls
Step 38: Data Protection (2 hours)
* Outcome: Protected sensitive data
* Implement encryption at rest
* Add secure file deletion
* Create data retention policies
* Design compliance tracking
Day 5: Documentation & Deployment
Step 39: API Documentation (2 hours)
* Outcome: Complete API reference
* Generate OpenAPI specs
* Create usage examples
* Document error codes
* Add integration guides
Step 40: Deployment Package (3 hours)
* Outcome: Production-ready system
* Create Docker images
* Write deployment scripts
* Configure environment variables
* Prepare rollback procedures

🎯 Success Metrics
Upload Pipeline Success
* ✅ Handles files up to 30MB smoothly
* ✅ Supports 10+ concurrent uploads
* ✅ <2 second response for small files
* ✅ Presigned URLs for large files
* ✅ 99.9% upload success rate
Processing Pipeline Success
* ✅ Processes PDF in <30 seconds
* ✅ Accurate text extraction
* ✅ Consistent chunk generation
* ✅ Handles processing failures gracefully
* ✅ Maintains processing queue <1 minute
System-Wide Success
* ✅ <100ms API response time (p95)
* ✅ Zero data loss on failures
* ✅ Automatic error recovery
* ✅ Complete audit trail
* ✅ Production-ready monitoring

🔄 Daily Execution Pattern
Morning Block (3 hours)
1. Review previous day's work
2. Implement core feature
3. Write initial tests
4. Commit progress
Afternoon Block (3 hours)
1. Continue feature development
2. Add error handling
3. Perform integration testing
4. Update documentation
Evening Review (1 hour)
1. Run full test suite
2. Review code quality
3. Plan next day
4. Push to repository

---

## 🔮 Future Enhancements (Post-MVP)

### Qdrant Vector Store - Deferred Integration (~1 hour)
**Status**: Infrastructure complete, disabled until needed
**When to Enable**: After Supabase migration or if search >100ms p95

**Deferred Tasks**:
1. **Dual-Write Implementation** (30 min)
   - Update `backend/app/services/embedding_service.py`
   - Write to PostgreSQL (always) + Qdrant (if enabled)
   - Test: Upload document, verify in both stores

2. **Smart Search Routing** (20 min)
   - Update `backend/app/services/search/hybrid_search_service.py`
   - Try Qdrant first → fallback to pgvector if circuit breaker open
   - Add metrics logging (provider used, latency)

3. **Performance Benchmarking** (10 min)
   - Run test queries on both stores
   - Measure latency improvement (expect 10x: 500ms → 50ms)
   - Verify result correctness (90%+ overlap)

**Expected Impact**: 10x faster search, <20ms p95 latency, scales to 10M+ vectors

**Activation Guide**: See `dev/active/querybox-backend/QDRANT_ACTIVATION.md`
**Implementation Details**: See `dev/active/PHASE4_QDRANT_SESSION_SUMMARY.md`

---

### Phase 2: Parsing Optimization - Deferred (~2-3 hours)
**Status**: Basic Docling parser working, advanced features NOT implemented
**When to Implement**: Based on user feedback for specific document types

**Current Implementation**:
- ✅ DoclingParser with smart OCR fallback
- ✅ Basic image metadata extraction (position, type only)
- ✅ Multi-format support (PDF, DOCX, PPTX, HTML, MD, TXT)
- ✅ PyPDF2 fallback for PDFs
- ✅ Quality assessment and language detection

**Deferred Features** (NOT implemented):
1. **MinerU Integration** (~1 hour)
   - Better table extraction for financial documents
   - Smart routing for table-heavy documents
   - File: `backend/app/services/parsers/mineru_parser.py` (not created)

2. **GPT-4o-mini Vision Parser** (~1 hour)
   - Chart and graph interpretation with GPT-4o-mini
   - Image content extraction and description
   - File: `backend/app/services/parsers/vision_parser.py` (not created)

3. **Smart Document Router** (~1 hour)
   - Document classifier (table_heavy, scanned, standard)
   - Confidence-based fallback routing
   - File: `backend/app/services/parsers/router.py` (not created)

4. **Docling Optimization** (~30 min)
   - GPU acceleration (CUDA support)
   - Parallel page processing
   - OCR batch optimization

**Expected Impact**: 99% parsing accuracy across all document types, faster processing

**Note**: Config mentions "smart" parser option but it's not implemented. Factory only supports "docling".

---

📊 Week-by-Week Deliverables
Week 1 Deliverable
Working Upload System: Files can be uploaded, validated, stored, and retrieved with proper metadata tracking
Week 2 Deliverable
Smart Upload Pipeline: Large file handling, session management, queue integration, and comprehensive error recovery
Week 3 Deliverable
Processing Engine: Complete PDF processing with text extraction, chunking, and storage
Week 4 Deliverable
Production-Ready System: Optimized, scalable, monitored, and documented upload & processing pipeline
This focused plan concentrates specifically on the document upload and processing features, providing clear steps with defined outcomes that build progressively toward a production-ready system. -->