# QueryBox Frontend - Implementation Tasks

**Timeline**: 1-2 Weeks (14 days)
**Last Updated**: 2025-01-05 Night (Day 1-5: 100% Complete!)
**Status**: Days 1-5 Complete → Ready for Day 6-8 (Search Interface)

---

## Week 1: Setup + Core Features (Days 1-7)

### Day 1-2: Project Setup + Design System ✅ 90% COMPLETE

#### Initial Setup ✅ COMPLETE
- [x] Verify backend services are running (`docker-compose up -d`)
- [x] Run backend health check (backend at root level, no separate directory)
- [x] Navigate to frontend directory (`cd frontend/`)
- [x] Initialize Next.js 14+ with TypeScript and Tailwind
  - Manual setup completed (tsconfig.json, tailwind.config.ts, etc.)
  - Build verified: `npm run build` succeeds with 0 errors

#### Install Dependencies ✅ COMPLETE
- [x] Install React Query
  - @tanstack/react-query v5.90.6
  - @tanstack/react-query-devtools v5.90.2
- [x] Install Axios v1.13.2
- [x] Install form libraries
  - react-hook-form v7.66.0
  - zod v4.1.12
  - @hookform/resolvers v5.2.2
- [x] Install utility libraries
  - clsx v2.1.1
  - tailwind-merge v3.3.1
  - class-variance-authority v0.7.1
  - react-dropzone v14.3.8
  - recharts v3.3.0
  - lucide-react v0.552.0
  - date-fns v4.1.0
- [x] Install tailwindcss-animate v1.0.7
- [x] Install autoprefixer v10.4.20
- **Total**: 455 packages, 0 vulnerabilities

#### Setup shadcn/ui ✅ COMPLETE
- [x] Initialize shadcn/ui configuration
  - Created `components.json` with settings
  - Configured Tailwind with CSS variables
  - Added theme colors to `app/globals.css`
- [x] Setup core UI structure
  - Created `lib/utils.ts` with cn() utility
  - Configured `tailwind.config.ts` with shadcn/ui colors
  - Added `tailwindcss-animate` plugin
  - Ready to add shadcn/ui components as needed

#### Create Directory Structure ✅ COMPLETE
- [x] Create app routes structure
  - `app/(dashboard)/documents/upload/`
  - `app/(dashboard)/documents/[id]/`
  - `app/(dashboard)/search/`
  - `app/(dashboard)/chat/`
  - `app/(dashboard)/analytics/`
- [x] Create components structure
  - `components/ui/` - For shadcn/ui components
  - `components/layout/` - Sidebar, Topbar, etc.
  - `components/documents/` - Document components
  - `components/search/` - Search components
  - `components/chat/` - Chat components
  - `components/analytics/` - Analytics components
  - `components/common/` - Shared components
- [x] Create lib structure
  - `lib/api/types/` - TypeScript types (ready for implementation)
  - `lib/api/endpoints/` - API functions (ready for implementation)
  - `lib/api/hooks/` - React Query hooks (ready for implementation)
  - `lib/utils/` - Utility functions
- [x] Create public assets folder
  - `public/images/` created

#### Configure Environment ✅ COMPLETE
- [x] Create `.env.local` file
  - NEXT_PUBLIC_API_URL=http://localhost:8000
  - NEXT_PUBLIC_APP_NAME=QueryBox
  - NEXT_PUBLIC_MAX_FILE_SIZE_MB=30
- [x] Update `tailwind.config.ts` with custom colors
  - Electric teal primary colors (#14b8a6)
  - shadcn/ui semantic colors (border, input, ring, etc.)
  - Dark mode support configured
- [x] Setup global styles in `app/globals.css`
  - Inter font from Google Fonts
  - CSS variables for light/dark themes
  - shadcn/ui base styles

#### Create Base Utilities ✅ COMPLETE
- [x] Create `lib/utils.ts` (cn() className utility) - shadcn/ui
- [x] Create `lib/utils/formatters.ts`
  - ✅ formatFileSize(bytes: number): string
  - ✅ formatDate(date: string | Date, formatStr?: string): string
  - ✅ formatRelativeTime(date: string | Date): string
  - ✅ formatPercentage(value: number, decimals?: number): string
  - ✅ getConfidenceColor(confidence: number): string
  - ✅ getCitationQualityColor(quality: 'STRONG' | 'MEDIUM' | 'WEAK'): string
- [x] Create `lib/utils/validators.ts`
  - ✅ isValidFileType(file: File, allowedTypes: string[]): boolean
  - ✅ isValidFileSize(file: File, maxSizeMB: number): boolean
  - ✅ isValidEmail(email: string): boolean
  - ✅ isValidQueryLength(query: string, min?: number, max?: number): boolean
- [x] Create `lib/utils/constants.ts`
  - ✅ API URLs (API_BASE_URL, API_V1_URL)
  - ✅ File size limits (MAX_FILE_SIZE_MB)
  - ✅ Allowed file types (ALLOWED_FILE_TYPES, FILE_TYPE_LABELS)
  - ✅ Pagination defaults (DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS)
  - ✅ Document status mappings (DOCUMENT_STATUS, STATUS_LABELS, STATUS_COLORS)
  - ✅ Search strategies (SEARCH_STRATEGIES, STRATEGY_LABELS)
  - ✅ Answer quality levels (ANSWER_QUALITY_LEVELS, QUALITY_LABELS)
  - ✅ Citation quality (CITATION_QUALITY)
  - ✅ Date ranges (DATE_RANGES)
  - ✅ Polling intervals (DOCUMENT_STATUS_POLL_INTERVAL, ANALYTICS_REFRESH_INTERVAL)

#### Create React Query Provider ✅ COMPLETE
- [x] Create `app/providers.tsx`
  - QueryClientProvider with default options
  - ReactQueryDevtools (dev only)
  - Configured staleTime, gcTime, refetchOnWindowFocus, retry
- [x] Update `app/layout.tsx`
  - Wrapped app in Providers component
  - Fixed React.ReactNode type (was React.Node)

---

### Day 2-3: API Client + TypeScript Types ✅ 100% COMPLETE

#### Create API Client ✅ COMPLETE
- [x] Create `lib/api/client.ts` (134 lines)
  - Axios instance with baseURL from .env.local
  - 30-second timeout configured
  - Request interceptor for API key injection (ready for auth)
  - Response interceptor with comprehensive error handling (400, 401, 403, 404, 422, 500, etc.)
  - Development-only console logging (NODE_ENV check)
  - getErrorMessage() helper function for consistent error display

#### Create TypeScript Types ✅ COMPLETE
- [x] Create `lib/api/types/common.ts` (44 lines)
  - PaginationParams, PaginationMeta, PaginatedResponse<T>
  - SuccessResponse, HealthResponse
  - ValidationError, ErrorResponse
- [x] Create `lib/api/types/document.ts` (78 lines)
  - DocumentStatus, DocumentFileType
  - DocumentMetadata, Document
  - DocumentCreate, DocumentUpdate
  - DocumentListFilters, DocumentStats
- [x] Create `lib/api/types/upload.ts` (53 lines)
  - UploadProgressCallback, UploadResponse
  - AllowedFileTypesResponse
  - FileValidationError, UploadConfig
  - BulkUploadResponse, UploadStatus
- [x] Create `lib/api/types/search.ts` (88 lines)
  - SearchStrategy, SearchRequest, SearchFilters
  - SearchResultChunk, SearchResponse
  - SearchHistoryItem, SearchSuggestionsResponse, SearchAnalytics
- [x] Create `lib/api/types/answer.ts` (116 lines)
  - AnswerQualityLevel, CitationQuality
  - AnswerRequest, Citation, AnswerResponse
  - ConversationMessage, Conversation
  - AnswerStreamChunk, AnswerFeedback, AnswerAnalytics
- [x] Create `lib/api/types/index.ts` (63 lines)
  - Barrel export for all types

#### Create API Endpoint Functions ✅ COMPLETE
- [x] Create `lib/api/endpoints/upload.ts` (76 lines)
  - uploadFile(file, config) with progress tracking
  - getAllowedFileTypes()
  - uploadMultipleFiles() for batch uploads
- [x] Create `lib/api/endpoints/documents.ts` (99 lines)
  - getDocuments(params, filters) - paginated list
  - getDocument(id) - single document
  - updateDocument(id, updates) - PATCH
  - deleteDocument(id), deleteDocuments(ids) - bulk delete
  - getDocumentStats() - statistics
  - reprocessDocument(id) - retry failed processing
  - downloadDocument(id) - file download
- [x] Create `lib/api/endpoints/search.ts` (50 lines)
  - searchDocuments(request) - all strategies
  - getSearchSuggestions(query) - autocomplete
  - getSearchAnalytics() - usage stats
- [x] Create `lib/api/endpoints/answer.ts` (90 lines)
  - generateAnswer(request) - Q&A with citations
  - getConversation(id), getConversations()
  - deleteConversation(id)
  - submitAnswerFeedback(feedback)
  - getAnswerAnalytics()
- [x] Create `lib/api/endpoints/index.ts` (38 lines)
  - Barrel export for all endpoints

#### Create React Query Hooks ✅ COMPLETE
- [x] Create `lib/api/hooks/useUpload.ts` (91 lines)
  - useUploadFile() - mutation with progress tracking
  - useAllowedFileTypes() - query for file config
  - useMultipleUpload() - batch upload helper
- [x] Create `lib/api/hooks/useDocuments.ts` (166 lines)
  - useDocuments(params, filters) - paginated list query
  - useDocument(id, {pollWhileProcessing}) - single document with auto-polling
  - useUpdateDocument() - mutation for metadata updates
  - useDeleteDocument(), useDeleteDocuments() - delete mutations
  - useDocumentStats() - statistics query
  - useReprocessDocument() - retry mutation
- [x] Create `lib/api/hooks/useSearch.ts` (71 lines)
  - useSearch(request, options) - search query
  - useSearchMutation() - search as mutation
  - useSearchSuggestions(query) - autocomplete query
  - useSearchAnalytics() - analytics query
- [x] Create `lib/api/hooks/useAnswer.ts` (104 lines)
  - useGenerateAnswer() - Q&A mutation
  - useConversation(id), useConversations() - conversation queries
  - useDeleteConversation() - delete mutation
  - useAnswerFeedback() - feedback mutation
  - useAnswerAnalytics() - analytics query
- [x] Create `lib/api/hooks/index.ts` (41 lines)
  - Barrel export for all hooks
  - `EnhancedAnswerResponse`
  - `EnrichedCitation`
  - `PropositionDetail`

---

### Day 3-5: Layout + Document Management ✅ 100% COMPLETE

#### shadcn/ui Components ✅ COMPLETE
- [x] Install shadcn/ui components (11 total)
  - npx shadcn@latest add button input card badge progress dialog
  - npx shadcn@latest add dropdown-menu table tabs select separator
  - All components configured with electric teal theme

#### Layout Components ✅ COMPLETE
- [x] Create `components/layout/Sidebar.tsx` (88 lines)
  - Logo with electric teal gradient background
  - Navigation links: Documents, Search, Chat, Analytics
  - Active state highlighting with primary color
  - Mobile overlay menu support
  - Lucide-react icons (FileText, Search, MessageSquare, BarChart3)
- [x] Create `components/layout/Topbar.tsx` (77 lines)
  - Page title with breadcrumb logic
  - Mobile menu toggle button
  - User menu dropdown (Profile, Settings, API Keys, Log out)
  - Notification and settings icons
  - Responsive header
- [x] Create `components/layout/DashboardLayout.tsx` (48 lines)
  - Combines Sidebar + Topbar
  - Mobile menu state management
  - Responsive flex layout
  - Main content area with overflow handling
- [x] Create `app/(dashboard)/layout.tsx` (6 lines)
  - Dashboard route wrapper
  - Applies DashboardLayout to all dashboard routes

#### Document Components ✅ COMPLETE
- [x] Create `components/documents/FileUpload.tsx` (217 lines)
  - Drag-and-drop zone with react-dropzone
  - Real-time upload progress tracking (Progress component)
  - File validation (type & size) with error messages
  - Multi-file support with individual status
  - Upload status: pending, uploading, completed, failed
  - Visual feedback with icons and colors
  - "Clear completed" button for batch cleanup
- [x] Create `components/documents/DocumentList.tsx` (245 lines)
  - Table component from shadcn/ui
  - Search input with debounce
  - Status filter dropdown (Select component)
  - Document actions: Download, Reprocess (failed only), Delete
  - Status badges with color coding
  - Empty state UI
  - Error state for offline backend with retry button
  - Refresh button
  - Format dates with date-fns
  - Format file sizes with formatFileSize utility

#### Document Pages ✅ COMPLETE
- [x] Create `app/(dashboard)/documents/page.tsx` (117 lines)
  - Stats cards (total documents, total size, completed count)
  - Tabs component: "All Documents" and "Upload"
  - FileUpload integration with onUploadComplete callback
  - DocumentList integration with refresh key
  - Auto-refresh on upload completion
  - useDocumentStats hook integration
- [x] Create `app/(dashboard)/search/page.tsx` (21 lines)
  - Placeholder for Day 6-8
- [x] Create `app/(dashboard)/chat/page.tsx` (21 lines)
  - Placeholder for Day 9-11
- [x] Create `app/(dashboard)/analytics/page.tsx` (21 lines)
  - Placeholder for Day 12-14
- [x] Update `app/page.tsx` (5 lines)
  - Redirects to /documents with redirect() function

#### Error Handling & Polish ✅ COMPLETE
- [x] Graceful error handling when backend is offline
  - DocumentList shows connection error with backend URL
  - Stats silently fail (don't render if unavailable)
  - Retry buttons on error states
- [x] Development-only console logging
  - lib/api/client.ts: console.warn for network errors (dev only)
  - No errors logged in production
- [x] React Query retry configuration
  - retry: 1 in app/providers.tsx for fast failure
- [x] Fixed Next.js cache issues
  - Cleared .next directory
  - Resolved MODULE_NOT_FOUND errors
  - Optional description
  - Optional action buttons (e.g., "Upload Document")
- [ ] Make it reusable across pages

#### Dashboard Layout
- [ ] Create `app/(dashboard)/layout.tsx`
  - Sidebar + Topbar + main content area
  - Responsive: Sidebar collapses on mobile
  - Grid layout: `grid grid-cols-[240px_1fr]` (desktop)

#### Common Components
- [ ] Create `components/common/LoadingSpinner.tsx`
  - Centered spinner with optional text
- [ ] Create `components/common/EmptyState.tsx`
  - Icon, title, description, optional action button
- [ ] Create `components/common/ErrorBoundary.tsx`
  - Catch errors, display friendly message
- [ ] Create `components/common/ConfirmDialog.tsx`
  - Reusable confirmation modal (delete, etc.)

---

### Day 4-5: Document Management Feature

#### Document Upload
- [ ] Create `components/documents/DocumentUpload.tsx`
  - Drag & drop area (react-dropzone)
  - File type and size validation (client-side)
  - Multiple file support
  - Upload progress indicator per file
  - Success/error messages (toast)
- [ ] Create `app/(dashboard)/documents/upload/page.tsx`
  - Use DocumentUpload component
  - Redirect to document list after success

#### Document List
- [ ] Create `components/documents/DocumentCard.tsx`
  - Document name, type icon, file size
  - Status badge (completed, processing, failed)
  - Processing progress indicator (if processing)
  - Actions: View, Delete
  - Click to view details
- [ ] Create `components/documents/DocumentStatus.tsx`
  - Real-time status indicator
  - Stages: Extraction → Chunking → Embedding
  - Progress bar or stepper
  - Error message if failed
- [ ] Create `components/documents/DocumentTable.tsx`
  - Table view (desktop)
  - Columns: Name, Type, Size, Status, Uploaded, Actions
  - Sortable columns
  - Pagination controls
- [ ] Create `components/documents/DocumentFilters.tsx`
  - Filter by status, type, date range
  - Clear filters button
- [ ] Create `app/(dashboard)/documents/page.tsx`
  - Toggle between Card and Table view
  - Pagination
  - Filters panel (collapsible)
  - Search by name (debounced)
  - "Upload Document" button → navigate to upload page
  - Empty state when no documents

#### Document Details
- [ ] Create `app/(dashboard)/documents/[id]/page.tsx`
  - Document metadata (name, size, type, uploaded date)
  - Processing status (detailed)
  - Processing quality metrics (if available)
  - Download button (future)
  - Delete button (with confirmation)
  - "Search in this document" button → navigate to search with filter

#### Document Actions
- [ ] Implement delete document
  - Confirmation dialog
  - Optimistic update (remove from list immediately)
  - Toast notification on success/error
- [ ] Implement retry processing (if failed)
  - Call metadata extraction endpoint
  - Update status

---

### Day 5-6: Search Interface

#### Search Bar
- [ ] Create `components/search/SearchBar.tsx`
  - Text input with search icon
  - Debounced search (300ms)
  - Clear button
  - Search on Enter key
  - Autocomplete suggestions (optional future)

#### Search Filters
- [ ] Create `components/search/SearchFilters.tsx`
  - Strategy selection: Radio buttons (Keyword, Semantic, Hybrid)
  - Advanced filters (collapsible):
    - Document types (multi-select)
    - Date range (from/to date pickers)
    - Quality threshold (slider)
    - Tags (multi-select)
  - Enable reranking (checkbox)
  - Enable MMR diversity (checkbox)
  - Apply/Reset buttons

#### Search Results
- [ ] Create `components/search/SearchResult.tsx`
  - Document name and type icon
  - Relevance score (percentage or badge)
  - Snippet with highlighted query terms
  - Citations (expandable)
  - Page number and section (if available)
  - Click to view full document
- [ ] Create `components/search/SearchResults.tsx`
  - List of SearchResult components
  - Loading skeleton during search
  - Empty state if no results
  - Result count and search time

#### Citation Components
- [ ] Create `components/search/CitationHighlight.tsx`
  - Render `<mark>` tags with quality-based colors
  - Green (strong), Yellow (medium), Red (weak)
  - Sanitize HTML (DOMPurify or parse manually)
- [ ] Create `components/search/CitationTooltip.tsx`
  - Tooltip on hover over citation
  - Show: Full passage, page, section, confidence
  - Use shadcn/ui Tooltip component

#### Search Page
- [ ] Create `app/(dashboard)/search/page.tsx`
  - SearchBar at top
  - SearchFilters in sidebar (collapsible)
  - SearchResults in main area
  - Pagination for results
  - URL state management (query, filters in URL params)
  - Handle loading, error, empty states

---

### Day 6-7: Chat/Q&A Interface (Part 1)

#### Chat Layout
- [ ] Create `components/chat/ChatInterface.tsx`
  - Chat container (scrollable message area)
  - Message list (user + assistant messages)
  - Input area at bottom
  - Auto-scroll to bottom on new messages

#### Chat Messages
- [ ] Create `components/chat/ChatMessage.tsx`
  - User message: Right-aligned, primary color background
  - Assistant message: Left-aligned, neutral background
  - Timestamp
  - Avatar/icon
- [ ] Create `components/chat/ChatInput.tsx`
  - Text area (auto-resize)
  - Send button
  - Character count (optional)
  - Disable during loading
  - Submit on Enter (Shift+Enter for new line)

#### Quality Level Selection
- [ ] Create quality level tabs/selector
  - Fast (Basic): ~3s, green indicator
  - Verified: ~5-7s, blue indicator
  - Enhanced (Recommended): ~5-8s, purple indicator
  - Show estimated time for each

#### Answer Display
- [ ] Create `components/chat/AnswerCard.tsx`
  - Answer text with citation references `[1]`, `[2]`, etc.
  - Confidence indicator (progress bar or badge)
  - Processing time
  - Model used (small text at bottom)
- [ ] Create `components/chat/ConfidenceIndicator.tsx`
  - Progress bar: 0-100%
  - Color-coded: Red (<50%), Yellow (50-75%), Green (>75%)
  - Tooltip with confidence breakdown (on hover)
  - Label: "High Confidence", "Medium Confidence", "Low Confidence"

#### Chat Page (Part 1)
- [ ] Create `app/(dashboard)/chat/page.tsx`
  - ChatInterface component
  - Quality level selector at top
  - Optional: Document filter (search which documents to use)
  - Loading state with estimated time
  - Error handling

---

## Week 2: Chat + Analytics + Polish (Days 8-14)

### Day 8-9: Chat/Q&A Interface (Part 2)

#### Citation Display
- [ ] Create `components/chat/CitationList.tsx`
  - Numbered list of citations
  - Expandable citations (accordion)
  - Each citation shows:
    - Document name (link to document)
    - Passage text (highlighted)
    - Page and section
    - Confidence score
    - Quality badge (STRONG/MEDIUM/WEAK)
- [ ] Integrate citations into AnswerCard
  - Inline citation numbers `[1]`, `[2]` clickable
  - Click to scroll to citation in CitationList
  - Highlight citation on click

#### Abstention Handling
- [ ] Create `components/chat/AbstractionAlert.tsx`
  - Special alert when system abstains
  - Show abstention message
  - Display abstention factors:
    - Low confidence
    - High hallucination risk
    - No evidence found
  - Suggestions:
    - Refine query
    - Upload more documents
    - Specify documents to search
- [ ] Integrate into Chat page
  - Show AbstractionAlert instead of AnswerCard when abstained
  - Different styling (warning colors)

#### Enhanced Metadata Display
- [ ] Create confidence breakdown component
  - Overall confidence
  - Average passage relevance
  - Average quote quality
  - Average verification agreement
  - Citation count breakdown (Strong/Medium/Weak)
- [ ] Add collapsible "Advanced Details" section
  - Hallucination probability
  - Propositions checked/verified/removed
  - Verification latency
  - Per-proposition details (expandable table)

#### Chat History (Optional Future)
- [ ] Store chat messages in React state
- [ ] Display conversation history
- [ ] Clear chat button
- [ ] Future: Persist to backend

---

### Day 10-11: Analytics Dashboard

#### Stats Cards
- [ ] Create `components/analytics/StatsCard.tsx`
  - Large number (KPI)
  - Label
  - Optional trend indicator (up/down arrow with percentage)
  - Optional icon
  - Subtle background color
- [ ] Create KPI cards for dashboard:
  - Total Documents
  - Total Storage Used (GB)
  - Documents Ready for Search
  - Failed Documents (if any)

#### Charts
- [ ] Create `components/analytics/UploadTrendChart.tsx`
  - Line chart (Recharts)
  - X-axis: Date
  - Y-axis: Upload count
  - Responsive
  - Tooltip on hover
- [ ] Create `components/analytics/DocumentTypeChart.tsx`
  - Pie chart or bar chart
  - Show distribution by MIME type
  - Legend
  - Colors for each type
- [ ] Create `components/analytics/ProcessingStatusChart.tsx`
  - Bar chart
  - Show count by status (Completed, Processing, Failed)
  - Color-coded bars

#### System Health
- [ ] Create `components/analytics/SystemHealthCard.tsx`
  - Health indicators:
    - Database: Connected/Disconnected
    - Redis: Connected/Disconnected
    - Storage: Available/Unavailable
    - Ollama (LLM): Available/Unavailable
  - Color-coded status (green/red)
  - Disk space usage (progress bar)
  - Last checked timestamp

#### Analytics Page
- [ ] Create `app/(dashboard)/analytics/page.tsx`
  - Grid layout: Stats cards at top (4 columns)
  - Charts in middle (2 columns)
  - System health at bottom
  - Date range filter (7d, 30d, 90d, 1y, all)
  - Refresh button
  - Auto-refresh every 5 minutes (optional)

#### Dashboard Home
- [ ] Update `app/(dashboard)/page.tsx`
  - Redirect to analytics page (or show analytics overview)
  - Welcome message
  - Quick actions: Upload, Search, Chat
  - Recent documents (last 5)

---

### Day 11-12: Responsive Design + Accessibility

#### Mobile Responsive (< 768px)
- [ ] Sidebar: Collapse to hamburger menu
  - Hamburger icon in Topbar
  - Slide-in drawer on click
  - Close on navigation or outside click
- [ ] Document list: Card layout only (no table)
  - Full-width cards
  - Stacked layout
- [ ] Search: Full-width search bar
  - Filters in drawer (bottom sheet or modal)
  - Results: Full-width cards
- [ ] Chat: Single-column layout
  - Full-width messages
  - Sticky input at bottom
- [ ] Analytics: Stacked layout
  - 1 column for all charts
  - Stats cards: 2 columns (not 4)

#### Tablet Responsive (768px - 1024px)
- [ ] Sidebar: Collapsible (icon + label)
  - Toggle button to expand/collapse
  - Persist state in localStorage
- [ ] Document list: Compact table
  - Fewer columns (hide less important ones)
- [ ] Search: 2-column layout (filters + results)
  - Filters collapsible
- [ ] Analytics: 2-column layout for charts

#### Desktop Responsive (> 1024px)
- [ ] Sidebar: Expanded by default
  - Full width with labels
- [ ] Document list: Full table with all columns
- [ ] Search: 3-column layout (filters sidebar + results + details panel - optional)
- [ ] Analytics: 3-4 column layout

#### Accessibility (WCAG 2.1 AA)
- [ ] Keyboard navigation
  - Tab through all interactive elements
  - Enter to activate buttons
  - Escape to close modals/dropdowns
  - Arrow keys for navigation (lists, dropdowns)
- [ ] ARIA labels
  - Icon-only buttons have aria-label
  - Form inputs have associated labels
  - Error messages have aria-live regions
- [ ] Focus indicators
  - Visible focus ring on all interactive elements
  - Custom focus styles (not just browser default)
- [ ] Color contrast
  - Text: ≥ 4.5:1 contrast ratio
  - UI components: ≥ 3:1 contrast ratio
  - Test with WebAIM Contrast Checker
- [ ] Screen reader support
  - Semantic HTML (nav, main, article, etc.)
  - Heading hierarchy (h1 → h2 → h3)
  - Alt text for all images
  - Form validation messages announced
- [ ] Test with tools
  - Lighthouse accessibility audit
  - axe DevTools
  - Manual keyboard testing
  - Manual screen reader testing (NVDA, VoiceOver)

---

### Day 12-13: Error Handling + Loading States + Polish

#### Error Handling
- [ ] Create global error handler in API client
  - Map backend errors to user-friendly messages
  - Display toast notifications
  - Log errors to console (dev) or monitoring service (prod)
- [ ] Add error boundaries to each major page
  - Catch React errors
  - Display fallback UI
  - "Try again" button
- [ ] Handle specific error cases:
  - 400 Bad Request → Show validation errors
  - 401 Unauthorized → Redirect to login (future)
  - 404 Not Found → Show "Resource not found" message
  - 413 Payload Too Large → Show file size error
  - 429 Rate Limited → Show "Too many requests, try again later"
  - 500 Server Error → Show "Something went wrong, try again"
  - Network Error → Show "Check your connection"

#### Loading States
- [ ] Document list: Skeleton loaders (cards or table rows)
- [ ] Document details: Skeleton for metadata
- [ ] Search results: Skeleton cards during search
- [ ] Chat: Loading indicator with estimated time
  - "Generating answer... (~5-8 seconds)"
  - Progress spinner or animated dots
- [ ] Analytics: Skeleton for charts and stats
- [ ] File upload: Progress bar per file
  - Percentage indicator
  - Cancel button (optional)

#### Empty States
- [ ] Document list (no documents)
  - Illustration or icon
  - "No documents yet"
  - "Upload your first document" button
- [ ] Search results (no matches)
  - "No results found for '{query}'"
  - Suggestions: Try different keywords, check filters
- [ ] Chat (no messages)
  - "Ask a question to get started"
  - Example questions (clickable)
- [ ] Analytics (no data)
  - "No data available for selected date range"

#### Optimistic Updates
- [ ] Document delete: Remove from list immediately
  - Revert if API call fails
  - Show toast notification
- [ ] Document upload: Add to list immediately with "uploading" status
  - Update to "processing" after upload completes
  - Show progress

#### Form Validation
- [ ] Document upload: Validate file type and size before upload
  - Show error message if invalid
  - Disable submit button until valid
- [ ] Search: Validate query length (min 3 chars)
  - Disable search button if invalid
- [ ] Chat: Validate query length (min 1 char, max 500 chars)
  - Show character count
  - Disable send button if invalid

#### Toast Notifications
- [ ] Setup toast provider (shadcn/ui Toast)
- [ ] Add toasts for:
  - Upload success
  - Upload error
  - Delete success
  - Delete error
  - Search error
  - Chat error
  - Rate limit exceeded
  - Network error

#### Polish
- [ ] Consistent spacing throughout (Tailwind spacing scale)
- [ ] Smooth transitions and animations
  - Hover effects on buttons, cards
  - Fade in/out for modals
  - Slide in/out for drawers
  - Page transitions (optional)
- [ ] Loading states for all async actions
- [ ] Proper typography hierarchy
  - Page titles: text-2xl or text-3xl
  - Section headings: text-xl
  - Body text: text-base
  - Small text: text-sm
- [ ] Consistent button styles
  - Primary: bg-primary-500
  - Secondary: bg-neutral-100
  - Destructive: bg-red-500
  - Ghost: transparent with hover
- [ ] Icon consistency (all from lucide-react)
  - Same size for same context (20px default)
  - Proper alignment with text

---

### Day 13-14: Testing + Deployment + Documentation

#### Manual Testing
- [ ] Test document upload flow
  - Upload single file
  - Upload multiple files
  - Upload invalid file type
  - Upload file too large
  - Verify processing status updates
- [ ] Test document management
  - View document list (pagination, sorting, filtering)
  - View document details
  - Delete document (with confirmation)
  - Search documents by name
- [ ] Test search functionality
  - Keyword search
  - Semantic search
  - Hybrid search (default)
  - Apply filters
  - View results with citations
  - Click citation to expand
- [ ] Test chat/Q&A
  - Ask question (all 3 quality levels)
  - View answer with citations
  - Check confidence indicators
  - Test abstention (ask unanswerable question)
  - Click citations to expand
- [ ] Test analytics dashboard
  - View stats
  - View charts
  - Change date range
  - Check system health
- [ ] Test responsive design
  - Mobile (iPhone, Android)
  - Tablet (iPad)
  - Desktop (1920x1080, 1366x768)
- [ ] Test accessibility
  - Keyboard navigation (Tab, Enter, Escape)
  - Screen reader (VoiceOver, NVDA)
  - Color contrast

#### Cross-Browser Testing
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

#### Performance Testing
- [ ] Run Lighthouse audit
  - Performance score ≥ 90
  - Accessibility score ≥ 95
  - Best Practices score ≥ 90
  - SEO score ≥ 90 (if applicable)
- [ ] Check bundle size
  - Initial load < 500KB gzipped
  - Use webpack-bundle-analyzer
- [ ] Test with slow network (3G throttling)
  - Page loads in < 5s
  - Loading states work properly

#### Code Quality
- [ ] Run ESLint
  - Fix all errors
  - Fix warnings if possible
- [ ] Run TypeScript compiler
  - No `any` types (except where necessary)
  - All types properly defined
- [ ] Code review
  - Check for duplicated code
  - Ensure component reusability
  - Check for proper error handling
  - Ensure proper naming conventions

#### Deployment
- [ ] Build production bundle
  ```bash
  npm run build
  ```
- [ ] Test production build locally
  ```bash
  npm run start
  ```
- [ ] Deploy to Vercel (recommended)
  - Connect GitHub repo
  - Configure environment variables
  - Deploy
  - Test deployed site
- [ ] Or deploy to custom server
  - Build Docker image
  - Deploy with Docker Compose
  - Configure Nginx reverse proxy
  - Setup SSL (Let's Encrypt)

#### Documentation
- [ ] Update `README.md`
  - Add frontend setup instructions
  - Add development workflow
  - Add build and deployment instructions
- [ ] Update `ARCHITECTURE.md`
  - Add frontend architecture section
  - Add component hierarchy
  - Add API integration details
- [ ] Update `ProgressTracker.md`
  - Mark Step 13 (Frontend Development) as complete
  - Update timeline
- [ ] Update `CLAUDE.md`
  - Update current phase to Step 14 (Advanced Analytics)
  - Update quick commands with frontend commands
- [ ] Create `frontend/README.md`
  - Tech stack
  - Project structure
  - Development guide
  - Component documentation
  - API integration guide

---

## Post-MVP Enhancements (Future)

### Step 14: Advanced Analytics (Tremor Integration)
- [ ] Install Tremor
  ```bash
  npm install @tremor/react
  ```
- [ ] Replace Recharts with Tremor components
  - AreaChart for upload trends
  - BarChart for document types
  - DonutChart for status distribution
  - BadgeDelta for trends
  - Card, Grid, Metric, Text components
- [ ] Add new analytics features
  - Search query analytics
  - User activity tracking (when auth is added)
  - Query performance metrics
  - Citation quality over time

### Step 15: Multi-Client White-Labeling
- [ ] Theme customization
  - Dynamic color system (CSS variables)
  - Logo upload and display
  - Font selection
  - Custom branding
- [ ] Client-specific feature toggles
  - Enable/disable features per client
  - Custom feature configurations
- [ ] Subdomain routing
  - `client1.querybox.com`
  - `client2.querybox.com`
  - Load client config based on subdomain

### Step 16: Advanced Features
- [ ] Real-time updates (WebSocket)
  - Live document processing updates
  - Live search results
  - Live chat (multi-user)
- [ ] Document annotations
  - Highlight and comment on passages
  - Save annotations
  - Share annotations
- [ ] Saved searches
  - Save search queries
  - Quick access to saved searches
  - Share saved searches
- [ ] Search history
  - View past searches
  - Re-run past searches
  - Analytics on search patterns
- [ ] Bookmarks
  - Bookmark documents
  - Bookmark search results
  - Organize with tags
- [ ] Export functionality
  - Export search results to PDF
  - Export search results to CSV
  - Export analytics to PDF/Excel
- [ ] Advanced document management
  - Folders and organization
  - Document versioning
  - Bulk operations (delete, move, tag)
- [ ] Collaboration features
  - Share documents with team
  - Share chat conversations
  - Comments and discussions

---

## Success Checklist

### Functionality
- [ ] All 4 MVP features fully functional
  - [ ] Document upload and management
  - [ ] Search with citations
  - [ ] Chat/Q&A with quality levels
  - [ ] Analytics dashboard
- [ ] All backend API endpoints integrated
- [ ] Real-time document processing status updates
- [ ] Citations display correctly with quality indicators
- [ ] Abstention handling works properly
- [ ] Error handling throughout

### Performance
- [ ] Initial page load < 2s
- [ ] Search results render < 500ms after API response
- [ ] File upload with progress tracking
- [ ] Smooth animations (60fps)
- [ ] No console errors

### Design
- [ ] Responsive on mobile, tablet, desktop
- [ ] Consistent design language
- [ ] Professional, premium feel
- [ ] Distinct from generic dashboards
- [ ] Accessible (WCAG 2.1 AA)

### Code Quality
- [ ] TypeScript strict mode, minimal `any` types
- [ ] Component reusability
- [ ] Clear folder structure
- [ ] API types match backend schemas
- [ ] Error handling throughout
- [ ] No ESLint errors
- [ ] Proper naming conventions

### Deployment
- [ ] Production build succeeds
- [ ] Deployed to Vercel or custom server
- [ ] Environment variables configured
- [ ] SSL enabled (HTTPS)
- [ ] Tested on deployed site

### Documentation
- [ ] README updated with frontend instructions
- [ ] ARCHITECTURE.md updated
- [ ] ProgressTracker.md updated
- [ ] CLAUDE.md updated
- [ ] Frontend-specific README created

---

## Notes

- Mark tasks as completed: `- [x]` as you finish them
- If you encounter blockers, document them here
- Update this file regularly to track progress
- Use `/dev-docs-update` before context compaction to save progress

---

**Total Estimated Time**: 12-14 days (1-2 weeks)
**Priority**: High (Step 13 - MVP Frontend)
**Next Step After Completion**: Step 14 - Advanced Analytics with Tremor
