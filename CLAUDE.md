# CLAUDE.md - QueryboxCore Project Context

## 🎯 Project Overview
**QueryboxCore** is a high-performance document processing and retrieval system built on proven pipeshub-ai architecture, focused on accuracy, speed, and scalability.

## 🚀 Current Phase: MVP Development
**Sprint**: Foundation Setup (Week 1)
**Focus**: Core Pipeline Implementation
**Status**: Project Initialization

## 📋 Core Pipeline Components
1. **Upload** → Accept all file types via manual upload
2. **Process** → Extract and normalize content
3. **Storage** → Efficient document storage system
4. **Chunking** → Intelligent text segmentation
5. **Embedding** → Vector generation for semantic search
6. **Retrieval** → Fast, accurate document retrieval
7. **Chat** → Conversational interface with citations

## 🎯 MVP Scope

### ✅ In Scope
- Manual file upload (all types)
- Document processing pipeline
- Vector storage and retrieval
- Chat interface with accurate citations
- Performance optimization from pipeshub-ai
- Scalable architecture

### ❌ Out of Scope (Post-MVP)
- Google Drive integration
- Other cloud storage imports
- User authentication (basic only for MVP)
- Advanced analytics
- Multi-tenant workspaces

## 🏗️ Technology Stack (From Pipeshub)
**Backend:**
- FastAPI (async performance)
- PostgreSQL + pgvector
- Redis (caching)
- Celery (task processing)
- LangChain (LLM orchestration)

**Frontend:**
- Next.js 14
- TypeScript
- Tailwind CSS
- React Query

**Infrastructure:**
- Docker
- Vector Database (pgvector/Qdrant)
- S3-compatible storage

## 📝 Development Workflow

### Standard Process
1. **Understand**: Study pipeshub-ai implementation
2. **Extract**: Identify proven patterns and optimizations
3. **Document**: Generate Claude CLI commands with context
4. **Implement**: Build in QueryboxCore with improvements
5. **Validate**: Ensure accuracy and performance

### Claude CLI Integration Pattern
```bash
# Example command generation
claude "Study pipeshub chunking strategy" \
  --project pipeshub-ai \
  --output "Generate implementation command for QueryboxCore"
```

## 🎨 Key Design Principles (From Pipeshub)
1. **Accuracy First**: Citation precision is non-negotiable
2. **Performance**: Sub-second retrieval times
3. **Scalability**: Handle millions of documents
4. **Modularity**: Pluggable components
5. **Observability**: Comprehensive logging and monitoring

## 📊 Success Metrics
- Upload to searchable: <30 seconds
- Search latency: <200ms
- Citation accuracy: >95%
- Concurrent users: 1000+
- Document capacity: 1M+ pages

## 🔄 Current Focus Areas

### Week 1: Foundation
- [ ] Project structure setup
- [ ] Core pipeline architecture
- [ ] Database schema design
- [ ] Basic upload interface

### Week 2: Processing Pipeline
- [ ] Document processors (PDF, DOCX, etc.)
- [ ] Chunking strategies
- [ ] Embedding generation
- [ ] Vector storage setup

### Week 3: Retrieval & Chat
- [ ] Retrieval algorithms
- [ ] Citation extraction
- [ ] Chat interface
- [ ] Accuracy validation

## 🚨 Critical Implementation Notes
- Always reference pipeshub-ai patterns
- Document performance benchmarks
- Maintain backward compatibility
- Test citation accuracy rigorously
- Keep components loosely coupled

## 📚 Reference Commands
```bash
# Development
make dev           # Start development environment
make test         # Run test suite
make benchmark    # Performance testing

# Deployment
make build        # Build containers
make deploy       # Deploy to staging
make scale        # Scale workers

# Analysis
make profile      # Profile performance
make citations    # Test citation accuracy
```

## 🔗 Important Links
- Pipeshub-AI: https://github.com/pipeshub-ai/pipeshub-ai
- QueryboxCore: [Your GitHub URL]
- Documentation: /docs
- API Reference: /docs/api

---
*Last Updated: [Current Date]*
*Phase: MVP Foundation*
*Next Review: Daily Standup*