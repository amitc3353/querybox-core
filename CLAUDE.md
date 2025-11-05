# CLAUDE.md - QueryboxCore Project Context

## 💡 Project Vision
**QueryboxCore** is a modular, configurable AI document intelligence platform where components (parsers, embedders, retrievers, LLMs) can be swapped per client without rewriting core logic.

Built on pipeshub-ai's proven architecture, delivering unmatched speed, citation transparency, and developer control.

## 🏗️ Current Phase
**Phase**: Step 12.5 - Claude Code Infrastructure Setup
**Status**: Setting up productivity tools for UI development
**Next**: Step 13 - Frontend Development (Dec 9-22)

## ⚡ Quick Commands

### Development
```bash
# Backend
pytest backend/tests/                    # Run all tests
pytest backend/tests/ -v -k "test_name"  # Run specific test
pytest backend/tests/ --cov=app          # With coverage

# Docker
docker-compose up -d                     # Start all services
docker-compose logs -f backend           # View backend logs
docker-compose down                      # Stop all services

# Database
alembic upgrade head                     # Run migrations
alembic revision --autogenerate -m "msg" # Create migration
python backend/scripts/seed_demo.py      # Seed demo data

# Services
python backend/scripts/health_check.py   # Check all services
python backend/scripts/run_tests.py --coverage  # Run tests with coverage
```

### Frontend (Coming in Step 13)
```bash
cd frontend
npm install
npm run dev                              # Start dev server
npm run build                            # Production build
```

## 🎨 Skills System
Skills auto-activate based on your work context:

**Available Skills** (in `.claude/skills/`):
- **python-fastapi-dev**: FastAPI routes, Pydantic models, SQLAlchemy, Celery patterns
- **testing-patterns**: Pytest fixtures, mocks, integration tests, coverage

**How it works**:
1. You write a prompt or edit a file
2. `skill-activation-prompt.ts` hook analyzes context
3. Relevant skills suggested automatically
4. Claude follows QueryBox patterns consistently

See skill-rules.json for activation triggers.

## 📋 Dev Docs Workflow

### For Large Features (Multiple Sessions)
1. **Plan in planning mode**: Let Claude research and create comprehensive plan
2. **Generate dev docs**: Run `/dev-docs` to create plan/context/tasks files in `dev/active/[feature-name]/`
3. **Implement**: Update `tasks.md` checklist as you complete items
4. **Before compaction**: Run `/dev-docs-update` to save progress
5. **New session**: "Continue from dev/active/[feature-name]/" - full context restored

### Files Created
- `plan.md`: Strategic plan from planning mode
- `context.md`: Key files, architectural decisions, next steps
- `tasks.md`: Checklist format, mark items as you complete them

### Why This Matters
Without dev docs, context resets lose progress. With dev docs, you can work on large features across multiple sessions without losing track.

## 🔗 Full Documentation

**For Detailed Information**:
- **Vision & Roadmap**: PROJECT.md (product spec, MVP scope)
- **System Architecture**: ARCHITECTURE.md (components, scaling, security)
- **Development Progress**: ProgressTracker.md (all steps, timelines)
- **Quick Start**: README.md (installation, setup)
- **Technical Guides**: docs/technical/ (step-by-step implementations)

**Current Modular Vision** (Step 15 - after UI):
- Transform to configurable platform
- Swappable parsers (PyMuPDF, Docling, Unstructured)
- Swappable embedders (BGE-M3, OpenAI, Cohere)
- Swappable retrievers (Hybrid, Vector-only, BM25)
- Swappable LLMs (Ollama, OpenAI, Claude)

See PROJECT.md Section "Modular Architecture Vision" for details.

## 🎯 Current Sprint Focus

**Step 12 (This Week)**:
- Complete database migrations (Alembic)
- Finalize Docker setup
- Create demo data seed scripts

**Step 12.5 (Just Completed)**:
- ✅ Claude Code infrastructure
- ✅ Skills auto-activation system
- ✅ Dev docs templates

**Step 13 (Next 2 Weeks)**:
- Frontend development (Next.js + TypeScript)
- Upload → Search → Chat UI
- Citation display with confidence indicators

## 🚨 Important Patterns

### Testing
- Always run tests after changes: `pytest backend/tests/`
- Use fixtures for test data (see testing-patterns skill)
- Integration tests require database: `pytest backend/tests/integration/`

### Database
- All schema changes via Alembic migrations
- Test migrations both up and down
- Never edit schema.sql directly

### API Development
- Follow FastAPI async patterns (see python-fastapi-dev skill)
- Pydantic models for all request/response
- Include OpenAPI documentation in docstrings

### Error Handling
- All exceptions should be captured
- Use structured logging (structlog)
- Celery tasks: retry with exponential backoff

For detailed patterns, see auto-activated skills in `.claude/skills/`.

## 📞 Need Help?

- **Architecture questions**: Check ARCHITECTURE.md
- **Feature planning**: Check ProgressTracker.md for step breakdown
- **API details**: Check PROJECT.md API specifications
- **Technical how-to**: Check docs/technical/step*.md files

---

**Remember**: This file is intentionally lean. Detailed documentation lives in:
- PROJECT.md (what we're building)
- ARCHITECTURE.md (how it works)
- ProgressTracker.md (where we are)
- Skills (how to build it)

Last Updated: Step 12.5 Complete
Next Milestone: Frontend Development (Step 13)
