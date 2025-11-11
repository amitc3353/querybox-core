# QueryBox Frontend - Strategic Plan

**Feature**: Enterprise-Grade Document Intelligence UI
**Timeline**: 1-2 Weeks MVP (Step 13)
**Status**: Planning Complete → Ready for Implementation
**Created**: 2025-01-05

---

## 1. Vision & Philosophy

### Core Requirements
- **Modern & Premium**: Enterprise-worthy UI that feels trustworthy and professional
- **Performant**: Fast, responsive across all devices
- **Maintainable**: Easy to scale as features and clients are added
- **Distinctive**: Visually unique, not a cookie-cutter dashboard
- **Composable**: Modular architecture for easy feature addition
- **Future-Proof**: Ready for multi-client white-labeling

### Design Philosophy

| Pillar | Implementation | Why |
|--------|----------------|-----|
| **Modern Minimalism** | Flat design, whitespace, neutral tones + accent | Clean, calm, professional |
| **Enterprise Trust** | Stable layouts, legible typography, restrained animations | Instant credibility for finance/legal/SaaS clients |
| **Composable Architecture** | Modular features (Search, Upload, Analytics) | Easy feature addition |
| **Unified Design Language** | Consistent grid, typography, colors | Brand consistency and polish |
| **Performance First** | Prefetch, lazy load, optimistic updates | Fast and fluid UX |

---

## 2. Tech Stack & Architecture

### Framework & Language
```
Next.js 14+ (App Router)
├── TypeScript (strict mode)
├── React 18+ (Server & Client Components)
└── Node.js 18+
```

**Why Next.js App Router?**
- Server Components for better performance
- Built-in API routes (for backend proxy if needed)
- File-based routing
- Image optimization
- SEO-ready (future marketing pages)

### Styling & Components
```
Tailwind CSS 3.4+
├── shadcn/ui (Primary component library)
│   ├── Built on Radix UI (accessible)
│   ├── Customizable via CVA (Class Variance Authority)
│   └── Copy-paste approach (full control)
├── Tremor (Future - Step 14 Analytics)
│   └── Analytics-focused charts & dashboards
└── Custom Components (QueryBox-specific)
```

**Component Strategy**:
- Use **shadcn/ui** for generic UI (buttons, forms, modals, dropdowns)
- Build **custom components** for domain-specific features (DocumentCard, SearchResult, ChatMessage, CitationTooltip)
- Integrate **Tremor** later for advanced analytics dashboards

### State & Data Fetching
```
TanStack Query (React Query) v5
├── Server state management
├── Automatic caching & refetching
├── Optimistic updates
└── Background sync
```

**Why React Query?**
- Perfect for backend API integration
- Built-in loading/error states
- Automatic retries and stale-while-revalidate
- DevTools for debugging

### Forms & Validation
```
React Hook Form + Zod
├── Type-safe validation
├── Performance (uncontrolled components)
└── Easy integration with TypeScript
```

### File Upload
```
react-dropzone
├── Drag & drop
├── File type validation
├── Multiple file support
└── Preview generation
```

### Charts & Visualization
```
Recharts (MVP Analytics)
├── React-native charts
├── Responsive
└── Customizable

Tremor (Future - Advanced Analytics)
├── Pre-built dashboard components
├── Analytics-focused
└── Beautiful defaults
```

### HTTP Client
```
Axios
├── Interceptors (auth, error handling)
├── Request/response transformation
├── Automatic retries
└── Progress tracking (file uploads)
```

---

## 3. Design System

### Color Palette

**Primary**: Electric Teal / Cobalt Blue
```css
--primary-50: #f0fdfa;
--primary-100: #ccfbf1;
--primary-500: #14b8a6;  /* Main accent */
--primary-600: #0d9488;
--primary-900: #134e4a;
```

**Neutral**: Gray scale
```css
--neutral-50: #fafafa;
--neutral-100: #f5f5f5;
--neutral-500: #737373;
--neutral-900: #171717;
```

**Semantic Colors**:
- **Success**: Green (#10b981) - Strong citations, completed processing
- **Warning**: Yellow (#f59e0b) - Medium citations, processing
- **Error**: Red (#ef4444) - Weak citations, failed processing
- **Info**: Blue (#3b82f6) - Informational messages

### Typography

**Font Family**: Inter (Google Fonts)
```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
```

**Scale** (Tailwind defaults):
```
text-xs:   0.75rem  (12px)  - Captions, labels
text-sm:   0.875rem (14px)  - Body small, metadata
text-base: 1rem     (16px)  - Body text
text-lg:   1.125rem (18px)  - Subheadings
text-xl:   1.25rem  (20px)  - Section headings
text-2xl:  1.5rem   (24px)  - Page headings
text-3xl:  1.875rem (30px)  - Hero text
```

### Layout Grid

**Container**:
- Max width: `1280px` (xl breakpoint)
- Padding: `px-4 sm:px-6 lg:px-8`

**Breakpoints** (Tailwind defaults):
```
sm:  640px   (Mobile landscape)
md:  768px   (Tablet)
lg:  1024px  (Desktop)
xl:  1280px  (Large desktop)
2xl: 1536px  (Extra large)
```

**Spacing System**:
- Use consistent spacing: 4px, 8px, 12px, 16px, 24px, 32px, 48px
- Tailwind classes: `p-1`, `p-2`, `p-3`, `p-4`, `p-6`, `p-8`, `p-12`

### Component Patterns

**Cards**:
```tsx
<Card className="border-neutral-200 hover:shadow-md transition-shadow">
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent>Content</CardContent>
</Card>
```

**Buttons**:
- Primary: `bg-primary-500 hover:bg-primary-600 text-white`
- Secondary: `bg-neutral-100 hover:bg-neutral-200 text-neutral-900`
- Destructive: `bg-red-500 hover:bg-red-600 text-white`
- Ghost: `hover:bg-neutral-100 text-neutral-700`

**Icons**:
- Library: `lucide-react` (consistent with shadcn/ui)
- Size: 16px (small), 20px (default), 24px (large)

---

## 4. Application Architecture

### Page Structure

```
app/
├── (auth)/                    # Future authentication
│   ├── login/
│   └── register/
├── (dashboard)/               # Main app (layout with sidebar)
│   ├── layout.tsx             # Sidebar + Topbar
│   ├── page.tsx               # Dashboard home (analytics overview)
│   ├── documents/             # Document management
│   │   ├── page.tsx           # Document list
│   │   ├── upload/
│   │   │   └── page.tsx       # Upload interface
│   │   └── [id]/
│   │       └── page.tsx       # Document details
│   ├── search/                # Search interface
│   │   └── page.tsx           # Search page
│   ├── chat/                  # Q&A interface
│   │   └── page.tsx           # Chat page
│   └── analytics/             # Analytics dashboard
│       └── page.tsx           # Stats & metrics
├── api/                       # API routes (optional proxy)
│   └── backend/
│       └── [...path]/
│           └── route.ts
├── layout.tsx                 # Root layout
└── page.tsx                   # Landing page (redirect to dashboard)
```

### Component Hierarchy

```
components/
├── ui/                        # shadcn/ui components
│   ├── button.tsx
│   ├── card.tsx
│   ├── dialog.tsx
│   ├── dropdown-menu.tsx
│   ├── input.tsx
│   ├── label.tsx
│   ├── select.tsx
│   ├── table.tsx
│   ├── tabs.tsx
│   ├── toast.tsx
│   └── ...
├── layout/                    # Layout components
│   ├── Sidebar.tsx
│   ├── Topbar.tsx
│   └── PageHeader.tsx
├── documents/                 # Document-specific
│   ├── DocumentCard.tsx       # Document list item
│   ├── DocumentUpload.tsx     # Upload interface
│   ├── DocumentStatus.tsx     # Processing status indicator
│   ├── DocumentTable.tsx      # Table view
│   └── DocumentFilters.tsx    # Filter panel
├── search/                    # Search-specific
│   ├── SearchBar.tsx          # Query input
│   ├── SearchFilters.tsx      # Advanced filters
│   ├── SearchResult.tsx       # Single result card
│   ├── SearchResults.tsx      # Results list
│   ├── CitationHighlight.tsx  # Highlighted text with citations
│   └── CitationTooltip.tsx    # Citation hover details
├── chat/                      # Chat-specific
│   ├── ChatInterface.tsx      # Main chat UI
│   ├── ChatMessage.tsx        # Message bubble
│   ├── ChatInput.tsx          # Query input
│   ├── AnswerCard.tsx         # Answer display
│   ├── ConfidenceIndicator.tsx # Confidence badge/bar
│   ├── CitationList.tsx       # Citations list
│   └── AbstractionAlert.tsx   # When system abstains
├── analytics/                 # Analytics-specific
│   ├── StatsCard.tsx          # KPI card
│   ├── UploadTrendChart.tsx   # Upload over time
│   ├── DocumentTypeChart.tsx  # Pie/bar chart
│   └── SystemHealthCard.tsx   # Health indicators
└── common/                    # Shared components
    ├── LoadingSpinner.tsx
    ├── ErrorBoundary.tsx
    ├── EmptyState.tsx
    └── ConfirmDialog.tsx
```

### State Management Strategy

**Server State** (React Query):
- Documents list
- Document details
- Search results
- Chat history
- Analytics data

**Client State** (React hooks):
- UI state (modals, dropdowns, filters)
- Form state (React Hook Form)
- Local preferences (theme, sidebar collapsed)

**URL State** (Next.js router):
- Search query
- Filters
- Pagination
- Current document ID

---

## 5. API Integration Architecture

### API Client Structure

```
lib/
├── api/
│   ├── client.ts              # Axios instance with interceptors
│   ├── types/                 # TypeScript interfaces (generated from backend)
│   │   ├── document.ts
│   │   ├── search.ts
│   │   ├── answer.ts
│   │   └── common.ts
│   ├── endpoints/             # API endpoint functions
│   │   ├── documents.ts       # Document CRUD
│   │   ├── upload.ts          # Upload operations
│   │   ├── search.ts          # Search operations
│   │   ├── answer.ts          # Q&A operations
│   │   ├── metadata.ts        # Metadata operations
│   │   └── health.ts          # Health checks
│   └── hooks/                 # React Query hooks
│       ├── useDocuments.ts    # useDocumentList, useDocument, etc.
│       ├── useSearch.ts       # useSearch, useSearchSuggestions
│       ├── useAnswer.ts       # useGenerateAnswer
│       └── useUpload.ts       # useUploadDocument
└── utils/
    ├── formatters.ts          # Date, file size, etc.
    ├── validators.ts          # Client-side validation
    └── constants.ts           # API URLs, limits, etc.
```

### API Client Configuration

```typescript
// lib/api/client.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor (auth, logging)
apiClient.interceptors.request.use(
  (config) => {
    // Add API key if needed
    const apiKey = localStorage.getItem('api_key');
    if (apiKey && config.url?.includes('/answer')) {
      config.headers['X-API-Key'] = apiKey;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor (error handling)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Global error handling
    if (error.response?.status === 429) {
      toast.error('Rate limit exceeded. Please wait.');
    }
    return Promise.reject(error);
  }
);
```

### React Query Setup

```typescript
// app/providers.tsx
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

---

## 6. Key Features & User Flows

### Feature 1: Document Upload & Management

**User Flow**:
1. Navigate to Upload page
2. Drag & drop or browse files
3. Client-side validation (type, size)
4. Upload with progress indicator
5. Redirect to document list
6. Auto-poll processing status until complete

**Key Components**:
- `DocumentUpload.tsx` - Dropzone with validation
- `DocumentCard.tsx` - Document list item with status
- `DocumentStatus.tsx` - Real-time processing indicator

**API Integration**:
- `POST /api/v1/upload/` - Upload file
- `GET /api/v1/documents/{id}/status` - Poll status (every 2-3s)
- `GET /api/v1/documents/` - List with pagination/filters
- `DELETE /api/v1/documents/{id}` - Delete document

**UI States**:
- Empty state (no documents)
- Uploading (progress bar)
- Processing (spinner with stage: extraction → chunking → embedding)
- Ready (green checkmark)
- Failed (error message with retry)

---

### Feature 2: Search Interface

**User Flow**:
1. Enter search query
2. Select strategy (Keyword/Semantic/Hybrid) - default: Hybrid
3. Optionally apply filters (date, type, tags)
4. Submit search
5. View results with snippets and citations
6. Click result to view full document
7. Expand citations for details

**Key Components**:
- `SearchBar.tsx` - Debounced input with autocomplete
- `SearchFilters.tsx` - Collapsible filter panel
- `SearchResult.tsx` - Result card with citations
- `CitationHighlight.tsx` - Highlighted passages
- `CitationTooltip.tsx` - Hover details

**API Integration**:
- `POST /api/v1/search/hybrid` - Primary search endpoint
- `POST /api/v1/search/keyword` - Fallback/alternative
- `POST /api/v1/search/semantic` - Fallback/alternative

**Citation Display**:
- Color-coded by quality:
  - **Strong** (≥0.95): Green background
  - **Medium** (0.85-0.95): Yellow background
  - **Weak** (<0.85): Red background
- Inline citations: `[1]`, `[2]`, `[3]`
- Tooltip on hover: Full passage + page + section
- Highlighted text with `<mark>` tags (sanitized HTML)

---

### Feature 3: Chat/Q&A Interface

**User Flow**:
1. Enter question in chat input
2. Select quality level (tabs):
   - **Fast** (Basic) - ~3s
   - **Verified** - ~5-7s
   - **Enhanced** (Recommended) - ~5-8s
3. Optionally filter by documents
4. Submit query
5. Loading state with estimated time
6. Answer appears with citations
7. Confidence indicator shows trust level
8. If abstained, show special alert with reason
9. Click citations to expand

**Key Components**:
- `ChatInterface.tsx` - Chat container with history
- `ChatMessage.tsx` - User/assistant message bubbles
- `ChatInput.tsx` - Query input with send button
- `AnswerCard.tsx` - Answer with citations
- `ConfidenceIndicator.tsx` - Progress bar or badge
- `AbstractionAlert.tsx` - Special UI for abstention
- `CitationList.tsx` - Expandable citations

**API Integration**:
- `POST /api/v1/answer` - Basic (fast)
- `POST /api/v1/answer/verified` - Verified (hallucination detection)
- `POST /api/v1/answer/enhanced` - Enhanced (recommended)

**Abstention Handling**:
```tsx
{response.abstained && (
  <Alert variant="warning">
    <AlertTitle>Unable to answer confidently</AlertTitle>
    <AlertDescription>
      {response.abstention_message}
      {/* Suggestions: Refine query, upload more docs */}
    </AlertDescription>
  </Alert>
)}
```

**Confidence Visualization**:
- Progress bar: 0-100%
- Color: Red (<50%), Yellow (50-75%), Green (>75%)
- Breakdown: Average passage relevance, quote quality, verification agreement

---

### Feature 4: Analytics Dashboard

**User Flow**:
1. View dashboard home (default page)
2. See key metrics (KPI cards):
   - Total documents
   - Total storage used
   - Documents by status
   - Recent uploads
3. View charts:
   - Upload trend (line chart)
   - Document types (pie chart)
   - Processing status (bar chart)
4. System health indicators
5. Filter by date range (7d, 30d, 90d, 1y, all)

**Key Components**:
- `StatsCard.tsx` - KPI card (number + label + trend)
- `UploadTrendChart.tsx` - Line chart (Recharts)
- `DocumentTypeChart.tsx` - Pie/bar chart
- `SystemHealthCard.tsx` - Health status with indicators

**API Integration**:
- `GET /api/v1/documents/stats` - Document statistics
- `GET /health` - System health

**Future Enhancement (Step 14)**:
- Replace Recharts with Tremor for advanced analytics
- Add search quality metrics
- Add user activity tracking
- Add query performance metrics

---

## 7. Performance Optimization Strategy

### Code Splitting
- Route-based splitting (Next.js automatic)
- Dynamic imports for heavy components:
  ```tsx
  const DocumentTable = dynamic(() => import('@/components/documents/DocumentTable'))
  ```

### Image Optimization
- Use Next.js `<Image>` component
- Lazy loading by default
- Responsive sizes

### Data Fetching
- Prefetch on hover (links, tabs)
- Optimistic updates (delete, status changes)
- Stale-while-revalidate (React Query)
- Pagination for long lists

### Caching Strategy
- **Documents list**: 5 min stale time
- **Document details**: 10 min stale time
- **Search results**: 1 min stale time (queries change frequently)
- **Analytics**: 5 min stale time

### Real-time Updates
- Poll document status every 2-3s during processing
- Stop polling when status is "completed" or "failed"
- Use WebSocket in future for true real-time

---

## 8. Responsive Design Strategy

### Mobile (< 768px)
- Sidebar collapses to hamburger menu
- Card layout for documents (no table)
- Full-width search bar
- Stacked filters (drawer instead of sidebar)
- Single-column chat

### Tablet (768px - 1024px)
- Collapsible sidebar (icon + label)
- Table view for documents (compact columns)
- 2-column layout for analytics

### Desktop (> 1024px)
- Full sidebar (expanded by default)
- Table view for documents (all columns)
- 3-column layout for analytics
- Side-by-side search results and filters

---

## 9. Accessibility (a11y)

### WCAG 2.1 AA Compliance
- Semantic HTML
- ARIA labels for icons
- Keyboard navigation (tab, enter, escape)
- Focus indicators
- Color contrast (4.5:1 for text)
- Screen reader support

### shadcn/ui Benefits
- Built on Radix UI (accessible primitives)
- Keyboard navigation built-in
- Focus management
- ARIA attributes

---

## 10. Testing Strategy

### Unit Tests
- Component tests (React Testing Library)
- Utility function tests (Jest)
- API client tests (MSW for mocking)

### Integration Tests
- User flow tests (Playwright or Cypress)
- API integration tests
- Form submission tests

### E2E Tests (Future)
- Critical paths:
  - Upload → Process → Search
  - Search → View Results
  - Chat → Get Answer

---

## 11. Deployment & Hosting

### Recommended Hosting
- **Vercel** (Next.js creators, best DX)
- **Netlify** (alternative)
- **Self-hosted** (Docker + Nginx)

### Environment Variables
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=QueryBox
NEXT_PUBLIC_MAX_FILE_SIZE_MB=30
```

### Build & Deploy
```bash
npm run build    # Production build
npm run start    # Production server
```

---

## 12. Future Enhancements (Post-MVP)

### Step 14: Advanced Analytics (Tremor Integration)
- Replace basic charts with Tremor components
- Add search quality metrics
- Add user activity tracking
- Add performance monitoring dashboard

### Step 15: Multi-Client White-Labeling
- Theme customization (colors, logos, fonts)
- Client-specific feature toggles
- Custom branding per client
- Subdomain routing

### Step 16: Advanced Features
- Real-time collaboration (WebSocket)
- Document annotations
- Saved searches
- Search history
- Bookmarks
- Export results (PDF, CSV)

---

## 13. Success Criteria

### Functionality
- [ ] All 4 MVP features fully functional
- [ ] All backend APIs integrated
- [ ] Real-time status updates working
- [ ] Citations displaying correctly
- [ ] Abstention handling working

### Performance
- [ ] Initial page load < 2s
- [ ] Search results render < 500ms after API response
- [ ] File upload with progress tracking
- [ ] Smooth animations (60fps)

### Design
- [ ] Responsive on mobile, tablet, desktop
- [ ] Consistent design language
- [ ] Professional, premium feel
- [ ] Distinct from generic dashboards

### Code Quality
- [ ] TypeScript strict mode, no `any` types
- [ ] Component reusability
- [ ] Clear folder structure
- [ ] API types match backend schemas
- [ ] Error handling throughout

---

## 14. Timeline Breakdown (1-2 Weeks)

### Week 1: Setup + Core Features (Days 1-7)
**Day 1-2**: Project setup + Design system
- Next.js + TypeScript + Tailwind setup
- shadcn/ui installation
- Layout components (Sidebar, Topbar)
- Design system (colors, typography, spacing)

**Day 3-4**: Document Management
- Upload interface with drag-drop
- Document list with pagination
- Processing status polling
- Delete functionality

**Day 5-6**: Search Interface
- Search bar with debouncing
- Strategy selection (Hybrid default)
- Results display with citations
- Citation highlighting

**Day 7**: Chat Interface (Part 1)
- Chat UI layout
- Quality level selection
- Answer display with citations

### Week 2: Chat + Analytics + Polish (Days 8-14)
**Day 8-9**: Chat Interface (Part 2)
- Confidence indicators
- Abstention handling
- Citation tooltips
- Chat history

**Day 10-11**: Analytics Dashboard
- KPI cards (stats)
- Upload trend chart
- Document type chart
- System health

**Day 12-13**: Polish & Testing
- Responsive design fixes
- Accessibility improvements
- Error handling
- Loading states
- Empty states

**Day 14**: Final Review & Deploy
- Code review
- Performance testing
- Deploy to Vercel
- Documentation update

---

## 15. Risk Mitigation

### Potential Challenges

**Challenge**: Polling for document status is inefficient
**Mitigation**: Use short-lived polling (2-3s), stop when complete, add WebSocket in future

**Challenge**: Large file uploads may timeout
**Mitigation**: Use chunked uploads, show progress, handle errors gracefully

**Challenge**: Citation HTML (`<mark>` tags) may have XSS risk
**Mitigation**: Sanitize HTML with DOMPurify or use safe rendering

**Challenge**: Complex state management for chat history
**Mitigation**: Use React Query for server state, simple hooks for UI state

**Challenge**: Design may take longer than expected
**Mitigation**: Use TailAdmin layout as reference, focus on functionality first

---

## Summary

This plan provides a comprehensive roadmap for building the QueryBox frontend in 1-2 weeks. The hybrid approach (template-inspired layout + custom features with shadcn/ui) balances speed and quality. All 4 MVP features are scoped, and the architecture is designed for easy scaling and future enhancements.

**Next Steps**: Proceed to implementation with detailed task breakdown in `tasks.md`.
