# Claude Code Success Workbook

**Purpose**: Maximize productivity with QueryBox Claude Code infrastructure
**Target**: 2-3x faster development, zero lost context
**Time to Master**: 30 minutes reading, 1 week practicing

---

## I. Quick Start (30 seconds)

### The System Does 3 Things
1. **Skills auto-activate** based on your prompts/files → Consistent patterns
2. **Dev docs survive resets** → Continue large features seamlessly
3. **Commands automate workflows** → Run tests, generate docs instantly

### Your First Session Checklist
```
✓ Skills activate automatically (you'll see "🎯 SKILL ACTIVATION CHECK")
✓ Use /dev-docs for features spanning >1 session
✓ Use /dev-docs-update before context resets
✓ Use /test-all before commits
```

### 3 Core Workflows
1. **Small feature**: Ask naturally → Skills activate → Implement → /test-all
2. **Large feature**: Plan → /dev-docs → Implement → /dev-docs-update → Continue next session
3. **Bug fix**: Describe → Fix with auto-activated patterns → /test-all

---

## II. Your Role vs Claude's Role

### ✅ You Must Do

**Run Commands When Needed**
- `/dev-docs` when starting multi-session features
- `/dev-docs-update` before context limits hit
- `/test-all` before commits/PRs

##  Good times to run /dev-docs-update:
  - After Day 2 (completed setup + API client)
  - After Day 5 (completed document management)
  - After Day 7 (completed search interface)
  - After Day 11 (completed analytics)
  - End of each major feature
  - Before switching context to backend work

    Run /dev-docs-update when:
  ✓ End of coding session on large feature
  ✓ Switching to different feature
  ✓ Before taking a break from multi-day feature
  ✓ After completing a major milestone (e.g., finished Day 1-2 tasks)

**Review Skill Suggestions**
- When you see "🎯 SKILL ACTIVATION CHECK", acknowledge it
- Skills contain QueryBox-specific patterns Claude should follow

**Update Progress Manually**
- Mark tasks.md items as complete: `- [x] Task done`
- Update ProgressTracker.md for major milestones (Claude can help)

**Test After Major Changes**
- Always run `/test-all` before pushing code
- Verify tests pass, not just that code compiles

### 🤖 Claude Handles Automatically

**Skills Auto-Activation**
- Detects FastAPI keywords → Activates python-fastapi-dev
- Editing test files → Activates testing-patterns
- You don't need to remind Claude about patterns

**Pattern Application**
- Follows FastAPI async patterns
- Uses Pydantic for validation
- Writes pytest fixtures correctly
- Applies QueryBox conventions

**File Tracking**
- Tracks all edits in `.claude/.edit-log.json`
- Used by /dev-docs-update to know what changed
- You never touch this file

**Context Management**
- Reads dev docs when you say "Continue from dev/active/X/"
- Restores full context from plan/context/tasks files
- Updates context.md with current state

### ⚠️ When You Need to Intervene

**Claude Misses a Pattern**
- Rare due to auto-activation
- Fix: Reference skill directly: "Use python-fastapi-dev patterns"

**Tests Fail**
- Run `/test-all` to see failures
- Claude will offer to fix or you can fix manually

**Context Feels Lost**
- If working on large feature: "/dev-docs-update" then "Continue from dev/active/X/"
- Creates checkpoint you can always return to

---

## III. Command Reference

### /dev-docs - Generate Development Documentation

**When to Use:**
- Starting a feature that will take 2+ sessions
- Complex refactoring that needs planning
- Any work you might lose context on

**What It Does:**
1. Asks about the feature (or infers from recent conversation)
2. Creates `dev/active/[feature-name]/` with:
   - `plan.md` - Strategic approach
   - `context.md` - Key files, decisions, next steps
   - `tasks.md` - Checklist of work items

**Usage:**
```
You: "Let's implement user authentication"
Claude: [Creates plan]
You: "/dev-docs"
Claude: Creates dev/active/user-authentication/
```

**What Happens:**
- Feature name auto-generated (lowercase-kebab-case)
- All planning context saved
- Checklist created for tracking progress

**After Using:**
- Implement while checking off tasks.md items
- Update context.md as you discover new info
- Run /dev-docs-update before context reset

### /dev-docs-update - Save Progress Before Reset

**When to Use:**
- Approaching context limit (you'll see warnings)
- Switching to different feature
- End of coding session on large feature
- Before taking a break from multi-day feature

**What It Does:**
1. Checks `.claude/.edit-log.json` for changed files
2. Finds the active feature directory
3. Updates `context.md` with:
   - Files created/modified
   - Current progress
   - Next immediate steps
4. Updates `tasks.md` - marks completed items

**Usage:**
```
You: "/dev-docs-update"
Claude:
  ✓ Updated dev/active/user-authentication/context.md
  ✓ Marked 5 tasks complete in tasks.md

  To continue: "Continue from dev/active/user-authentication/"
```

**What Gets Saved:**
- All files you edited with line numbers
- Completed tasks marked with [x]
- Current blockers or decisions
- Next 1-3 steps to take

**After Using:**
- Safe to let context compact
- New session: "Continue from dev/active/user-authentication/"
- Full context restored instantly

### /test-all - Run Full Test Suite

**When to Use:**
- Before committing code
- Before creating a PR
- After implementing a feature
- After major refactoring
- When investigating test failures

**What It Does:**
1. Runs `pytest backend/tests/ --cov=backend --cov-report=html -v`
2. Analyzes results
3. Reports:
   - Pass/fail counts
   - Coverage percentages
   - Slow tests
   - Specific failures with suggestions

**Usage:**
```
You: "/test-all"
Claude:
  🧪 RUNNING FULL TEST SUITE
  ━━━━━━━━━━━━━━━━━━━━━━━━

  ✅ Tests: 156 passed, 2 failed
  📊 Coverage: 87.3%
  ⚡ Time: 45.2s

  ❌ Failures:
  1. test_hybrid_search (line 145) - Expected 5, got 3

  Fix this?
```

**Quick Options:**
- Unit tests only: Claude can run `pytest backend/tests/unit/ -v`
- Specific file: Claude can run `pytest backend/tests/unit/test_search.py -v`
- One test: Claude can run `pytest backend/tests/unit/test_search.py::test_hybrid -v`

---

## IV. Skills Auto-Activation System

### How It Works (Automatic)

**Trigger 1: Keywords in Prompt**
- You say: "Create a FastAPI route for search"
- System detects: "fastapi", "route"
- Activates: python-fastapi-dev skill

**Trigger 2: File Being Edited**
- You edit: `backend/api/routes/search.py`
- System detects: Path matches `backend/api/**/*.py`
- Activates: python-fastapi-dev skill

**Trigger 3: File Content Patterns**
- File contains: `@router.post(` or `class X(BaseModel)`
- Activates: python-fastapi-dev skill

### What You'll See

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 SKILL ACTIVATION CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Relevant skills detected: @.claude/skills/python-fastapi-dev.md

Please review these skills before proceeding.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User request: Create a FastAPI route for search
```

**What to Do:**
- Just acknowledge and continue
- Claude has already loaded the skill
- Patterns will be applied automatically

### Current Skills

**python-fastapi-dev.md**
- FastAPI routes and async patterns
- Pydantic models for validation
- SQLAlchemy database operations
- Celery background tasks
- Error handling with structlog

**testing-patterns.md**
- Pytest fixtures and factories
- Mocking external services
- Integration test patterns
- Coverage best practices

### Manual Skill Reference (Rare)

If Claude forgets a pattern:
```
You: "Follow the python-fastapi-dev patterns for this route"
```

---

## V. What Gets Updated & When

### 🤖 Auto-Updated by Claude (Never Touch)

**`.claude/.edit-log.json`**
- Tracks every file edit
- Used by /dev-docs-update
- Auto-cleaned periodically

**`dev/active/[feature]/context.md`**
- Updated by /dev-docs-update
- Contains current progress

**`dev/active/[feature]/tasks.md`**
- You mark items [x] as you complete
- Claude adds new tasks if discovered during implementation

### ✋ You Update When Needed

**CLAUDE.md**
- Only if project vision fundamentally changes
- Typically never needed
- Current: 152 lines, streamlined

**ProgressTracker.md**
- Major milestone completion
- Step completion checkmarks
- Claude can help update this

**Skill files (`.claude/skills/*.md`)**
- Only when adding new QueryBox-specific patterns
- Rare - current skills cover 90% of cases

### 🔒 Never Update (Unless Broken)

**`.claude/hooks/*.ts` or `*.sh`**
- Skill activation logic
- File tracking logic
- Only touch if something breaks

**`.claude/skills/skill-rules.json`**
- Activation triggers
- Only update when adding new skills

**`.claude/settings.local.json`**
- Hook configuration
- Already set up correctly

---

## VI. Effective Prompting

### ✅ Best Practices

**Be Specific with Context**
```
Good: "Create a FastAPI route for document upload at /api/v1/documents"
Great: "Create a FastAPI route for document upload. Follow python-fastapi-dev patterns, include Pydantic models, async/await, and proper error handling"
```

**Use Dev Docs for Continuity**
```
New session:
You: "Continue from dev/active/user-authentication/"
Claude: [Loads plan.md + context.md + tasks.md] "I see we completed OAuth setup. Next step is refresh token logic."
```

**Reference Files with Line Numbers**
```
Good: "Fix the bug in search.py"
Great: "Fix the reranking bug in backend/api/routes/search.py:145 where we expected 5 results but got 3"
```

**Let Skills Activate Naturally**
```
You: "How do I create a new FastAPI route?"
[python-fastapi-dev activates automatically]
Claude: [Provides QueryBox-specific patterns]
```

### ❌ Anti-Patterns to Avoid

**Don't Ask Claude to "Remember"**
```
Bad: "Remember to use async/await"
Better: Let python-fastapi-dev skill activate (it will enforce this)
```

**Don't Lose Context on Large Features**
```
Bad: Work 3 sessions without dev docs → Lose context
Better: /dev-docs → work → /dev-docs-update → Continue seamlessly
```

**Don't Skip Testing**
```
Bad: Implement → Commit → Discover failures later
Better: Implement → /test-all → Fix failures → Commit
```

**Don't Update Infrastructure Files**
```
Bad: Edit .claude/hooks/skill-activation-prompt.ts "to improve it"
Better: It works. Leave it alone.
```

---

## VII. Success Workflows

### Small Feature (<1 session)

```
1. Ask naturally: "Add pagination to /api/v1/documents endpoint"
2. Skills activate: python-fastapi-dev
3. Implement: Claude follows patterns automatically
4. Test: "/test-all"
5. Commit: If tests pass
```

**Time**: 30-60 minutes
**Dev docs**: Not needed

### Large Feature (Multi-session)

```
Session 1:
1. Plan: "I want to implement user authentication with JWT"
2. Generate docs: "/dev-docs"
3. Implement: Work through tasks.md checklist
4. Save progress: "/dev-docs-update"

Session 2 (days later):
1. Restore: "Continue from dev/active/user-authentication/"
2. Review: Claude summarizes progress from context.md
3. Continue: Pick up exactly where you left off
4. Save again: "/dev-docs-update" before break

Session 3:
1. Restore: "Continue from dev/active/user-authentication/"
2. Finish: Complete remaining tasks
3. Test: "/test-all"
4. Archive: Move dev/active/user-authentication/ to dev/completed/
```

**Time**: 3-5 sessions over days/weeks
**Context loss**: Zero (dev docs preserve everything)

### Bug Fix

```
1. Describe: "Search returns 3 results but should return 5. Check reranking logic in search.py:145"
2. Skills activate: python-fastapi-dev, testing-patterns
3. Fix: Claude identifies issue, suggests fix
4. Test: "/test-all" to verify fix + no regressions
5. Commit: Clean fix with test
```

**Time**: 15-45 minutes
**Dev docs**: Not needed

### Refactoring

```
Small refactor (<1 session):
1. Describe: "Refactor DocumentService to use async/await consistently"
2. Skills activate: python-fastapi-dev
3. Refactor: Apply patterns
4. Test frequently: "/test-all" after each change

Large refactor (multi-session):
1. Plan: "Refactor to modular architecture - swappable embedders"
2. Generate docs: "/dev-docs"
3. Refactor incrementally: Update tasks.md as you go
4. Test after each phase: "/test-all"
5. Save progress: "/dev-docs-update" between sessions
```

**Time**: Varies
**Dev docs**: Use for refactors >1 session

---

## VIII. Troubleshooting

### Skills Don't Activate

**Symptom**: No "🎯 SKILL ACTIVATION CHECK" appears
**Cause**: Prompt lacks trigger keywords
**Fix**: Reference skill manually: "Use python-fastapi-dev patterns"

### Tests Fail After Implementation

**Symptom**: /test-all shows failures
**Cause**: New code broke existing tests or tests need updating
**Fix**:
1. Review failure details from /test-all output
2. Ask Claude: "Fix the test failures in test_search.py"
3. Re-run /test-all to verify

### Lost Context Mid-Feature

**Symptom**: Claude doesn't remember what we were building
**Cause**: Didn't use dev docs for large feature
**Fix**:
1. "/dev-docs" to create docs now
2. Manually add context.md with current state
3. Continue with dev docs from now on

### Hook Error Messages

**Symptom**: Error running skill-activation-prompt.ts
**Cause**: TypeScript/Node.js issue or malformed skill-rules.json
**Fix**:
1. Check `.claude/skills/skill-rules.json` is valid JSON
2. Verify `npx tsx` is available: `npx tsx --version`
3. Check hook permissions: `ls -l .claude/hooks/`

---

## IX. Quick Reference

### Commands at a Glance
- `/dev-docs` → Starting large feature
- `/dev-docs-update` → Before context reset
- `/test-all` → Before commits

### File Structure
```
.claude/
├── skills/              # Auto-activate patterns
├── hooks/               # Automation (don't touch)
├── commands/            # Slash command definitions
└── settings.local.json  # Configuration (don't touch)

dev/
├── active/              # In-progress features
└── completed/           # Archived features
```

### When In Doubt
1. **Small task?** → Just ask, skills activate automatically
2. **Large task?** → /dev-docs first
3. **Before reset?** → /dev-docs-update
4. **Before commit?** → /test-all

---

## X. Success Metrics

**After 1 Week:**
- ✅ Zero context lost on large features
- ✅ Skills activate 95%+ of the time
- ✅ Test failures caught before commits
- ✅ 2-3x faster feature implementation

**After 2 Weeks:**
- ✅ Habits formed - commands feel natural
- ✅ Pattern consistency across all code
- ✅ Can resume any feature instantly
- ✅ Minimal time spent on "what was I doing?"

**Productivity Gains:**
- Small features: 1.5-2x faster (skills auto-apply patterns)
- Large features: 3-4x faster (dev docs eliminate context loss)
- Bug fixes: 2x faster (patterns + tests)
- Refactoring: 2-3x faster (consistent patterns + tests)

---

**Last Updated**: Step 12.5 Complete
**Maintainer**: Update only when infrastructure fundamentally changes
**Support**: See `.claude/skills/*.md` for pattern details
