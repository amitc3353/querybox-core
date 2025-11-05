# QueryBox Frontend - Implementation Context

**Last Updated**: 2025-01-05 (Night - Day 3-5 Complete!)
**Current Phase**: Day 3-5 Complete → Layout + Document Management Implemented
**Next Session**: Day 6-8 - Search Interface Implementation

---

## 1. Quick Start Reference

### Resume This Work
```bash
cd /Users/amitchandel/Documents/workspace/build5M/querybox-core

# When starting implementation:
cd frontend/
npm install
npm run dev  # Start dev server on http://localhost:3000
```

### Key Commands
```bash
# Development
npm run dev                    # Start dev server
npm run build                  # Production build
npm run start                  # Run production build
npm run lint                   # Lint code

# shadcn/ui components
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add dialog
# etc.

# Backend (parallel terminal)
cd backend/
docker-compose up -d           # Start backend services
```

---

## 1A. Current Progress (Updated: Jan 5, 2025 Night)

### ✅ Completed (Day 1-5: 100%)

**Day 1-2: Foundation (100% Complete)**
- ✅ Next.js 15.5.6 with TypeScript (strict mode)
- ✅ Tailwind CSS 3.4+ with electric teal theme (#14b8a6)
- ✅ 455 packages installed, 0 vulnerabilities
- ✅ React Query v5 + DevTools configured
- ✅ All utilities: formatters, validators, constants
- ✅ Build verified: 0 errors, 102kB base bundle

**Day 2-3: API Integration Layer (100% Complete)**
- ✅ `lib/api/client.ts` - Axios instance with interceptors (30s timeout)
  - Request interceptor for API key injection (ready for auth)
  - Response interceptor with comprehensive error handling
  - Development-only logging to reduce console noise
  - Lines 1-134
- ✅ `lib/api/types/` - Complete TypeScript type definitions
  - `common.ts` - Pagination, errors, health (44 lines)
  - `document.ts` - Document models, filters, stats (78 lines)
  - `upload.ts` - Upload configs, progress callbacks (53 lines)
  - `search.ts` - Search strategies, filters, results (88 lines)
  - `answer.ts` - Q&A types, citations, conversations (116 lines)
  - `index.ts` - Barrel export (63 lines)
- ✅ `lib/api/endpoints/` - All API endpoint functions
  - `upload.ts` - uploadFile, getAllowedFileTypes, uploadMultipleFiles (76 lines)
  - `documents.ts` - CRUD, stats, reprocess, download (99 lines)
  - `search.ts` - searchDocuments, suggestions, analytics (50 lines)
  - `answer.ts` - generateAnswer, conversations, feedback (90 lines)
  - `index.ts` - Barrel export (38 lines)
- ✅ `lib/api/hooks/` - React Query hooks with caching
  - `useUpload.ts` - Upload with progress, multi-file support (91 lines)
  - `useDocuments.ts` - CRUD with auto-polling for processing status (166 lines)
  - `useSearch.ts` - Search with caching, mutation variant (71 lines)
  - `useAnswer.ts` - Answer generation, conversations (104 lines)
  - `index.ts` - Barrel export (41 lines)

**Day 3-5: Layout + Document Management (100% Complete)**
- ✅ shadcn/ui components installed (11 components)
  - Button, Input, Card, Badge, Progress, Dialog
  - DropdownMenu, Table, Tabs, Select, Separator
- ✅ `components/layout/Sidebar.tsx` - Navigation with active states (88 lines)
- ✅ `components/layout/Topbar.tsx` - Header with user menu (77 lines)
- ✅ `components/layout/DashboardLayout.tsx` - Responsive layout with mobile menu (48 lines)
- ✅ `components/documents/FileUpload.tsx` - Drag-and-drop with progress (217 lines)
  - Real-time upload progress tracking
  - File validation (type & size)
  - Multi-file support with individual status
  - Visual feedback for all states
- ✅ `components/documents/DocumentList.tsx` - Full-featured table (245 lines)
  - Search and status filters
  - Actions: Download, Reprocess, Delete
  - Status badges with color coding
  - Error handling for offline backend
- ✅ `app/(dashboard)/layout.tsx` - Dashboard wrapper (6 lines)
- ✅ `app/(dashboard)/documents/page.tsx` - Full document management (117 lines)
  - Stats dashboard (total docs, size, completed)
  - Tabbed interface (All Documents / Upload)
  - Auto-refresh on upload
- ✅ `app/(dashboard)/search/page.tsx` - Placeholder (21 lines)
- ✅ `app/(dashboard)/chat/page.tsx` - Placeholder (21 lines)
- ✅ `app/(dashboard)/analytics/page.tsx` - Placeholder (21 lines)
- ✅ `app/page.tsx` - Redirects to /documents (5 lines)

**Error Handling & Polish**
- ✅ Graceful error states when backend is offline
- ✅ Development-only console logging
- ✅ React Query configured with retry: 1 for fast failure
- ✅ Clear error messages with retry buttons
- ✅ Next.js cache cleared (fixed MODULE_NOT_FOUND errors)

### 📊 Stats
- **Total Packages**: 455
- **Security Issues**: 0
- **Build Time**: ~3.8s
- **Bundle Size**: 207 kB (documents page), 102 kB (other pages)
- **Total Routes**: 8 (1 redirect, 7 pages)
- **Components Created**: 6 layout/document components
- **API Layer**: 24 files (types, endpoints, hooks)
- **Lines of Code**: ~2,500+ lines across all files

---

## 2. Project Structure Overview

### Current State (UPDATED - Now Built!)
```
querybox-core/
├── app/                       # ✅ Backend (FastAPI) - at root level
│   ├── api/v1/endpoints/      # All API routes ready
│   ├── models/                # SQLAlchemy models
│   ├── schemas/               # Pydantic schemas (USE FOR TYPES)
│   └── services/              # Business logic
├── tests/                     # Backend tests
├── frontend/                  # ✅ 90% Complete (Next.js 14)
│   ├── app/                   # ✅ App Router configured
│   │   ├── (dashboard)/       # ✅ Structure created
│   │   ├── globals.css        # ✅ Tailwind + theme variables
│   │   ├── layout.tsx         # ✅ Root layout with providers
│   │   ├── page.tsx           # ✅ Landing page
│   │   └── providers.tsx      # ✅ React Query provider
│   ├── components/            # ✅ All directories created
│   │   ├── ui/                # For shadcn/ui components
│   │   ├── layout/            # Sidebar, Topbar, etc.
│   │   ├── documents/         # Document components
│   │   ├── search/            # Search components
│   │   ├── chat/              # Chat components
│   │   ├── analytics/         # Analytics components
│   │   └── common/            # Shared components
│   ├── lib/                   # ✅ Structure + utilities complete
│   │   ├── api/               # ⏳ API integration (next step)
│   │   │   ├── types/         # TypeScript types (to create)
│   │   │   ├── endpoints/     # API functions (to create)
│   │   │   └── hooks/         # React Query hooks (to create)
│   │   ├── utils/             # ✅ All utilities created
│   │   │   ├── utils.ts       # ✅ cn() utility
│   │   │   ├── formatters.ts  # ✅ File size, dates, etc.
│   │   │   ├── validators.ts  # ✅ File/query validation
│   │   │   └── constants.ts   # ✅ All app constants
│   │   └── utils.ts           # ✅ cn() utility (shadcn/ui)
│   ├── public/images/         # ✅ Assets directory
│   ├── .env.local             # ✅ Environment variables
│   ├── components.json        # ✅ shadcn/ui config
│   ├── tailwind.config.ts     # ✅ Custom theme
│   ├── tsconfig.json          # ✅ TypeScript config
│   ├── next.config.mjs        # ✅ Next.js config
│   ├── postcss.config.mjs     # ✅ PostCSS config
│   └── package.json           # ✅ 455 packages installed
├── dev/
│   └── active/
│       └── querybox-frontend/ # This documentation
└── docker-compose.yml
```

### Target Frontend Structure
```
frontend/
├── app/                       # Next.js App Router
│   ├── (dashboard)/           # Main app routes
│   │   ├── layout.tsx         # Sidebar + Topbar layout
│   │   ├── page.tsx           # Dashboard home (analytics)
│   │   ├── documents/
│   │   │   ├── page.tsx       # Document list
│   │   │   ├── upload/
│   │   │   │   └── page.tsx   # Upload page
│   │   │   └── [id]/
│   │   │       └── page.tsx   # Document details
│   │   ├── search/
│   │   │   └── page.tsx       # Search interface
│   │   ├── chat/
│   │   │   └── page.tsx       # Q&A interface
│   │   └── analytics/
│   │       └── page.tsx       # Analytics dashboard
│   ├── layout.tsx             # Root layout
│   ├── page.tsx               # Landing (redirect to /documents)
│   └── providers.tsx          # React Query provider
├── components/
│   ├── ui/                    # shadcn/ui components (generated)
│   ├── layout/                # Layout components
│   ├── documents/             # Document-specific components
│   ├── search/                # Search-specific components
│   ├── chat/                  # Chat-specific components
│   ├── analytics/             # Analytics components
│   └── common/                # Shared components
├── lib/
│   ├── api/                   # API client & hooks
│   │   ├── client.ts          # Axios instance
│   │   ├── types/             # TypeScript types (from backend schemas)
│   │   ├── endpoints/         # API endpoint functions
│   │   └── hooks/             # React Query hooks
│   └── utils/                 # Utilities
│       ├── formatters.ts      # Date, file size formatters
│       ├── validators.ts      # Client-side validation
│       └── constants.ts       # Constants
├── public/                    # Static assets
│   ├── images/
│   └── favicon.ico
├── styles/
│   └── globals.css            # Tailwind + global styles
├── .env.local                 # Environment variables
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## 3. Backend API Integration Guide

### API Base URL
```typescript
// .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Complete API Reference

All endpoints are prefixed with `/api/v1` unless otherwise noted.

#### Upload & Documents
```typescript
// Upload
POST   /api/v1/upload/                    // Upload file
GET    /api/v1/upload/allowed-types       // Get allowed types

// Documents
GET    /api/v1/documents/                 // List documents (paginated)
GET    /api/v1/documents/search           // Search documents by name
GET    /api/v1/documents/stats            // Get statistics
GET    /api/v1/documents/{id}             // Get document details
GET    /api/v1/documents/{id}/status      // Get processing status
GET    /api/v1/documents/{id}/search-quality  // Validate search readiness
DELETE /api/v1/documents/{id}             // Delete document

// Search
POST   /api/v1/search/hybrid              // Hybrid search (RECOMMENDED)
POST   /api/v1/search/keyword             // Keyword search
POST   /api/v1/search/semantic            // Vector search
POST   /api/v1/search/unified             // Unified with strategy selection
GET    /api/v1/search/health              // Search health check

// Answer (requires X-API-Key header)
POST   /api/v1/answer                     // Basic answer (fast)
POST   /api/v1/answer/verified            // Verified answer (hallucination detection)
POST   /api/v1/answer/enhanced            // Enhanced answer (RECOMMENDED)
GET    /api/v1/answer/health/ollama       // Ollama health check

// Metadata
GET    /api/v1/metadata/documents/{id}/metadata        // Get metadata
POST   /api/v1/metadata/documents/{id}/metadata/extract  // Extract metadata

// Metrics
GET    /api/v1/metrics/summary            // Pipeline metrics
GET    /api/v1/metrics/health-detailed    // Detailed health

// Health
GET    /health                            // Main health check
```

### Key Request/Response Types

**Reference Location**: `backend/app/schemas/` - Copy these to `frontend/lib/api/types/`

#### Document Types
```typescript
// Document Response
interface DocumentResponse {
  id: string;
  document_name: string;
  original_name: string;
  mime_type: string;
  file_extension: string;
  file_size: number;
  file_size_mb: number;
  storage_provider: string;
  status: string;
  created_at: string;
  updated_at: string;
  processing_status?: {
    extraction: ProcessingStatusDetail;
    chunking: ProcessingStatusDetail;
    embedding: ProcessingStatusDetail;
  };
}

// Processing Status Detail
interface ProcessingStatusDetail {
  status: string;
  started_at?: string;
  completed_at?: string;
  progress?: number;
  error_message?: string;
}

// Upload Response
interface UploadResponse {
  success: boolean;
  message: string;
  duplicate?: boolean;
  document: DocumentResponse;
  processing_status?: {
    extraction_status: string;
    chunking_status: string;
    embedding_status: string;
    ready_for_search: boolean;
  };
}
```

#### Search Types
```typescript
// Search Request
interface SearchRequest {
  query: string;
  filters?: SearchFilters;
  limit?: number;
  offset?: number;
  similarity_threshold?: number;
  keyword_weight?: number;
  vector_weight?: number;
  enable_reranking?: boolean;
}

interface SearchFilters {
  document_types?: string[];
  date_from?: string;
  date_to?: string;
  min_quality?: number;
  tags?: string[];
}

// Search Response
interface SearchResponse {
  success: boolean;
  query: string;
  total_results: number;
  returned_results: number;
  results: SearchResultItemWithCitations[];
  processing_time_ms: number;
}

interface SearchResultItemWithCitations {
  chunk_id?: string;
  document_id: string;
  document_name: string;
  relevance_score: number;
  snippet?: string;
  citations: Citation[];
  snippet_highlighted?: string;
}

interface Citation {
  text: string;
  page?: number;
  section?: string;
  position: { start: number; end: number };
  confidence: number;
  source_context: string;
}
```

#### Answer Types
```typescript
// Answer Request
interface AnswerRequest {
  query: string;
  document_ids?: string[];
  top_k?: number;
  temperature?: number;
  include_citations?: boolean;
}

// Enhanced Answer Response (RECOMMENDED)
interface EnhancedAnswerResponse {
  success: boolean;
  abstained: boolean;
  abstention_message?: string;
  answer: string;
  verified_answer: string;
  enriched_citations: EnrichedCitation[];
  confidence: number;
  verified_confidence?: number;
  enhanced_metadata: {
    status: string;
    hallucination_probability?: number;
    propositions_checked: number;
    propositions_verified: number;
    confidence_breakdown: {
      overall: number;
      average_passage_relevance: number;
      average_quote_quality: number;
    };
    proposition_details: PropositionDetail[];
    abstention_factors: {
      low_confidence?: boolean;
      high_hallucination?: boolean;
      no_evidence?: boolean;
    };
    total_citations: number;
    strong_citations: number;
    medium_citations: number;
    weak_citations: number;
  };
}

interface EnrichedCitation {
  document_id: string;
  document_name: string;
  passage_text: string;
  highlighted_passage_text?: string;
  page?: number;
  section?: string;
  relevance_score: number;
  citation_number: number;
  quality: "STRONG" | "MEDIUM" | "WEAK";
  is_exact_quote: boolean;
  best_similarity?: number;
}
```

---

## 4. Implementation Patterns

### API Client Setup (Critical First Step)

**File**: `lib/api/client.ts`

```typescript
import axios, { AxiosInstance } from 'axios';

const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add API key for answer endpoints
    const apiKey = typeof window !== 'undefined'
      ? localStorage.getItem('api_key')
      : null;

    if (apiKey && config.url?.includes('/answer')) {
      config.headers['X-API-Key'] = apiKey;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message;
    console.error('API Error:', message);
    return Promise.reject(error);
  }
);

export default apiClient;
```

### React Query Hooks Pattern

**File**: `lib/api/hooks/useDocuments.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DocumentAPI } from '../endpoints/documents';
import type { DocumentResponse } from '../types/document';

// List documents
export function useDocuments(params?: {
  page?: number;
  page_size?: number;
  status?: string;
}) {
  return useQuery({
    queryKey: ['documents', params],
    queryFn: () => DocumentAPI.list(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Single document with auto-refresh during processing
export function useDocument(id: string) {
  return useQuery({
    queryKey: ['document', id],
    queryFn: () => DocumentAPI.get(id),
    refetchInterval: (data) => {
      // Poll every 2s if processing, stop if completed/failed
      const status = data?.status;
      return status === 'processing' || status === 'uploading'
        ? 2000
        : false;
    },
  });
}

// Delete document
export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => DocumentAPI.delete(id),
    onSuccess: () => {
      // Invalidate documents list
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}
```

### File Upload with Progress

**File**: `lib/api/hooks/useUpload.ts`

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      file,
      onProgress
    }: {
      file: File;
      onProgress?: (progress: number) => void;
    }) => {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/upload/`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            const progress = progressEvent.total
              ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
              : 0;
            onProgress?.(progress);
          },
        }
      );

      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}
```

### Search with Debouncing

**Component**: `components/search/SearchBar.tsx`

```typescript
'use client';

import { useState, useCallback } from 'react';
import { useDebounce } from '@/lib/hooks/useDebounce';
import { useSearch } from '@/lib/api/hooks/useSearch';
import { Input } from '@/components/ui/input';

export function SearchBar() {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);

  const { data, isLoading } = useSearch({
    query: debouncedQuery,
    enabled: debouncedQuery.length >= 3,
  });

  return (
    <div>
      <Input
        type="text"
        placeholder="Search documents..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {isLoading && <Spinner />}
      {data && <SearchResults results={data.results} />}
    </div>
  );
}
```

### Citation Display with Quality Color Coding

**Component**: `components/search/CitationHighlight.tsx`

```typescript
import { cn } from '@/lib/utils';

interface CitationHighlightProps {
  citation: {
    text: string;
    quality: 'STRONG' | 'MEDIUM' | 'WEAK';
    confidence: number;
  };
}

export function CitationHighlight({ citation }: CitationHighlightProps) {
  const qualityColors = {
    STRONG: 'bg-green-100 border-green-500 text-green-900',
    MEDIUM: 'bg-yellow-100 border-yellow-500 text-yellow-900',
    WEAK: 'bg-red-100 border-red-500 text-red-900',
  };

  return (
    <mark
      className={cn(
        'px-1 rounded border-l-2',
        qualityColors[citation.quality]
      )}
    >
      {citation.text}
    </mark>
  );
}
```

### Abstention Alert

**Component**: `components/chat/AbstractionAlert.tsx`

```typescript
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

interface AbstractionAlertProps {
  message: string;
  factors: {
    low_confidence?: boolean;
    high_hallucination?: boolean;
    no_evidence?: boolean;
  };
}

export function AbstractionAlert({ message, factors }: AbstractionAlertProps) {
  return (
    <Alert variant="warning" className="border-yellow-500 bg-yellow-50">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>Unable to answer confidently</AlertTitle>
      <AlertDescription>
        <p className="mb-2">{message}</p>
        <p className="text-sm text-neutral-600">
          Suggestions:
          <ul className="list-disc ml-4 mt-1">
            <li>Try rephrasing your question</li>
            <li>Upload more relevant documents</li>
            <li>Specify which documents to search</li>
          </ul>
        </p>
      </AlertDescription>
    </Alert>
  );
}
```

---

## 5. Key Files to Reference

### Backend Schemas (Copy to Frontend Types)

**Location**: `backend/app/schemas/`

1. **`upload.py`** → `frontend/lib/api/types/upload.ts`
   - `UploadResponse`
   - `AllowedTypesResponse`

2. **`document.py`** → `frontend/lib/api/types/document.ts`
   - `DocumentResponse`
   - `DocumentListResponse`
   - `DocumentStatsResponse`

3. **`search.py`** → `frontend/lib/api/types/search.ts`
   - `SearchRequest`
   - `SearchResponse`
   - `SearchResultItemWithCitations`

4. **`answer.py`** → `frontend/lib/api/types/answer.ts`
   - `AnswerRequest`
   - `AnswerResponse`

5. **`verification.py`** → `frontend/lib/api/types/verification.ts`
   - `VerificationMetadata`

6. **`citation_confidence.py`** → `frontend/lib/api/types/citation.ts`
   - `EnrichedCitation`
   - `PropositionDetail`

### Design References

**TailAdmin React Template**: Use for layout inspiration
- Sidebar structure
- Topbar with user menu
- Card layouts
- Table designs

**shadcn/ui Examples**: https://ui.shadcn.com/examples
- Dashboard layout
- Form patterns
- Data tables

---

## 6. Environment Configuration

### Frontend Environment Variables

**File**: `frontend/.env.local`

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# App Configuration
NEXT_PUBLIC_APP_NAME=QueryBox
NEXT_PUBLIC_MAX_FILE_SIZE_MB=30

# Feature Flags (optional)
NEXT_PUBLIC_ENABLE_ANALYTICS=true
NEXT_PUBLIC_ENABLE_DARK_MODE=false
```

### Backend Configuration (For Reference)

**File**: `backend/.env`

```env
# Already configured - no changes needed
DATABASE_URL=postgresql://querybox:dev123@localhost:5432/querybox
REDIS_URL=redis://localhost:6379/0
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2:7b
```

---

## 7. Dependencies to Install

### Core Dependencies
```json
{
  "dependencies": {
    "next": "^14.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.3.3",

    "@tanstack/react-query": "^5.17.0",
    "@tanstack/react-query-devtools": "^5.17.0",
    "axios": "^1.6.5",

    "react-hook-form": "^7.49.3",
    "zod": "^3.22.4",
    "@hookform/resolvers": "^3.3.4",

    "react-dropzone": "^14.2.3",
    "recharts": "^2.10.3",
    "lucide-react": "^0.309.0",

    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0",
    "class-variance-authority": "^0.7.0",

    "date-fns": "^3.0.6"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.1",
    "postcss": "^8.4.33",
    "autoprefixer": "^10.4.17",
    "@types/node": "^20.11.5",
    "@types/react": "^18.2.48",
    "@types/react-dom": "^18.2.18",
    "eslint": "^8.56.0",
    "eslint-config-next": "^14.1.0"
  }
}
```

### shadcn/ui Components to Install

**Install as needed**:
```bash
npx shadcn-ui@latest init
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add input
npx shadcn-ui@latest add label
npx shadcn-ui@latest add select
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add table
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add toast
npx shadcn-ui@latest add alert
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add progress
npx shadcn-ui@latest add separator
npx shadcn-ui@latest add skeleton
```

---

## 8. Current Progress Snapshot

### Completed
- ✅ Backend fully implemented (FastAPI + all endpoints)
- ✅ All API schemas defined (Pydantic models)
- ✅ Database models complete (SQLAlchemy)
- ✅ Docker setup for backend services
- ✅ Frontend development plan created
- ✅ Implementation context documented

### In Progress
- 🚧 Frontend project setup (Next.js + TypeScript)

### Not Started
- ⏳ shadcn/ui installation
- ⏳ API client implementation
- ⏳ React Query hooks
- ⏳ Component development
- ⏳ Page layouts
- ⏳ Integration with backend

---

## 9. Next Immediate Steps

### When Resuming This Work

1. **Start Backend Services**
   ```bash
   cd backend/
   docker-compose up -d
   python backend/scripts/health_check.py  # Verify all services running
   ```

2. **Initialize Frontend Project**
   ```bash
   cd frontend/
   npx create-next-app@latest . --typescript --tailwind --app
   npm install @tanstack/react-query axios react-hook-form zod
   ```

3. **Install shadcn/ui**
   ```bash
   npx shadcn-ui@latest init
   # Choose:
   # - Style: Default
   # - Base color: Neutral
   # - CSS variables: Yes
   ```

4. **Create Directory Structure**
   ```bash
   mkdir -p app/\(dashboard\)/{documents,search,chat,analytics}
   mkdir -p components/{ui,layout,documents,search,chat,analytics,common}
   mkdir -p lib/api/{types,endpoints,hooks}
   mkdir -p lib/utils
   ```

5. **Copy Backend Schemas to Frontend Types**
   - Manually convert Pydantic models to TypeScript interfaces
   - Start with: `document.ts`, `search.ts`, `answer.ts`

6. **Implement API Client**
   - Create `lib/api/client.ts` with Axios instance
   - Add interceptors for auth and error handling

7. **Setup React Query**
   - Create `app/providers.tsx` with QueryClientProvider
   - Wrap app in providers

8. **Build Layout Components**
   - `components/layout/Sidebar.tsx`
   - `components/layout/Topbar.tsx`
   - `app/(dashboard)/layout.tsx`

9. **Follow Task Checklist**
   - See `tasks.md` for granular implementation steps
   - Mark tasks as completed as you go

---

## 10. Troubleshooting Guide

### Common Issues

**Issue**: CORS error when calling backend from frontend
**Solution**:
- Ensure backend CORS origins include `http://localhost:3000`
- Check `backend/app/core/config.py`: `BACKEND_CORS_ORIGINS`

**Issue**: API key required error for answer endpoints
**Solution**:
- Store API key in localStorage: `localStorage.setItem('api_key', 'your-key')`
- Or use environment variable: `NEXT_PUBLIC_API_KEY`

**Issue**: Document status not updating in real-time
**Solution**:
- Use React Query's `refetchInterval` option
- Set interval to 2000ms during processing
- Stop polling when status is "completed" or "failed"

**Issue**: File upload fails with 413 error
**Solution**:
- Check file size < 30MB
- Verify backend `MAX_FILE_SIZE` setting
- Ensure Nginx/proxy allows large uploads

**Issue**: Citation HTML not rendering
**Solution**:
- Sanitize HTML with DOMPurify before rendering
- Or use `dangerouslySetInnerHTML` cautiously
- Better: Parse `<mark>` tags and render as React components

---

## 11. Performance Benchmarks

### Target Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| Initial page load | < 2s | First Contentful Paint |
| Time to Interactive | < 3s | Fully interactive |
| Search results render | < 500ms | After API response |
| File upload (10MB) | < 5s | With progress indicator |
| Chat answer (enhanced) | 5-8s | Server-side processing time |
| Document list load | < 1s | 20 items per page |

### Optimization Checklist
- [ ] Use Next.js Image component for images
- [ ] Lazy load heavy components (charts, tables)
- [ ] Debounce search input (300ms)
- [ ] Paginate long lists (20-50 items/page)
- [ ] Use React Query caching (5min stale time)
- [ ] Optimize bundle size (< 500KB gzipped)

---

## 12. Accessibility Checklist

- [ ] All interactive elements keyboard accessible (Tab, Enter, Escape)
- [ ] Proper heading hierarchy (h1 → h2 → h3)
- [ ] Alt text for all images
- [ ] ARIA labels for icon-only buttons
- [ ] Color contrast ≥ 4.5:1 for text
- [ ] Focus visible on all interactive elements
- [ ] Error messages announced to screen readers
- [ ] Form inputs have associated labels

---

## 13. Security Considerations

### Client-Side
- [ ] Sanitize all user input before rendering
- [ ] Use DOMPurify for HTML content (citations)
- [ ] Never store sensitive data in localStorage (use httpOnly cookies for auth)
- [ ] Validate file types and sizes client-side (defense in depth)
- [ ] Use HTTPS in production

### API Integration
- [ ] API keys stored securely (environment variables, not hardcoded)
- [ ] Rate limit handling (429 errors)
- [ ] Input validation (Zod schemas)
- [ ] CORS configured properly
- [ ] No sensitive data in URLs (use POST bodies)

---

## 14. Testing Strategy

### Unit Tests (Jest + React Testing Library)
- Component rendering
- User interactions (click, type, submit)
- Utility functions
- API client error handling

### Integration Tests
- API integration (MSW for mocking)
- Form submission flows
- File upload process
- Search and results display

### E2E Tests (Playwright or Cypress) - Future
- Upload → Process → Search flow
- Search → View Results
- Chat → Get Answer

---

## 15. Documentation to Update

When implementation is complete, update:

1. **README.md** - Add frontend setup instructions
2. **ARCHITECTURE.md** - Add frontend architecture section
3. **ProgressTracker.md** - Mark Step 13 complete
4. **CLAUDE.md** - Update current phase to Step 14

---

## 16. Next Immediate Steps (Day 6-8 - Search Interface)

### Current State
Days 1-5 are 100% complete. Document management with upload is fully functional.

### What to Build Next

**1. Search Input Component** (~1 hour)
- `components/search/SearchInput.tsx`
  - Search query input with debounce
  - Strategy selector (keyword/semantic/hybrid)
  - Document filter dropdown
  - Advanced filters (date range, file type)

**2. Search Results Component** (~2 hours)
- `components/search/SearchResults.tsx`
  - Result cards with document context
  - Highlighted text snippets
  - Relevance scores with color coding
  - Pagination controls
  - Empty state and loading states

**3. Search Page Integration** (~1 hour)
- `app/(dashboard)/search/page.tsx`
  - Integrate SearchInput + SearchResults
  - Use useSearch hook
  - Handle search state and filters
  - Add "Ask about this" button for each result

**4. Polish & Error Handling** (~30 min)
- Loading skeletons
- Error states
- No results state
- Backend offline handling

**Total Time**: ~4.5 hours for complete search interface

---

## Summary

**Day 1-5**: 100% Complete ✅
- Foundation, API layer, layout, and document management fully implemented
- Build verified: 0 errors, all pages functional
- Error handling in place for offline backend

**Day 6-8**: Ready to Start 🚀
- Search interface is next
- All API hooks already created (useSearch, useSearchMutation)
- Types and endpoints ready

**Next Session**: Begin Day 6-8 - Search Interface Implementation
