---
description: Update existing dev docs with current progress before context compaction
---

# Update Development Documentation

You are about to update existing development documentation to reflect the current state of work. This preserves progress before conversation context is compacted.

## Your Task

1. **Identify the active feature** by:
   - Checking `.claude/.edit-log.json` for recently edited files
   - Reviewing recent conversation for feature context
   - Listing directories in `dev/active/`

2. **Update the relevant dev docs** in `dev/active/[feature-name]/`:

   **a) Update context.md**:
   - Add newly created/modified files with line references
   - Update "Current Progress" section
   - Revise "Next Immediate Steps" based on current state
   - Note any new challenges or decisions made
   - Include important code snippets or patterns discovered

   **b) Update tasks.md**:
   - Mark completed items with `- [x]`
   - Add new tasks discovered during implementation
   - Reorder if priorities changed
   - Remove obsolete tasks
   - Add notes to tasks if needed (indented under task)

   **c) Update plan.md** (only if strategy changed):
   - Add architecture decisions made
   - Update implementation phases if approach changed
   - Note deviations from original plan

3. **Summarize changes** made to the docs

## What to Track

**Always include:**
- Files created/modified with specific line numbers
- Completed tasks from tasks.md
- Current blockers or issues
- Next 1-3 immediate steps

**Important details:**
- Database migrations run
- Dependencies added
- Configuration changes
- Test files created
- Breaking changes

## Example Context Update

```markdown
## Current Progress (Updated: Dec 5, 2024)

### Completed
- [x] Created `backend/api/routes/auth.py` with login/register endpoints
- [x] Added JWT token generation in `backend/services/auth_service.py:45-78`
- [x] Database migration for users table (`alembic/versions/abc123_add_users.py`)
- [x] Tests in `backend/tests/integration/test_auth.py` (12 tests passing)

### Current Blockers
- Need to decide on refresh token strategy (JWT vs database-stored)
- Password hashing performance slow (bcrypt) - consider argon2

### Files Modified
- `backend/api/routes/auth.py` - Login/register endpoints
- `backend/models/user.py` - User model with password hashing
- `backend/schemas/auth.py` - Auth request/response models
- `backend/services/auth_service.py` - Token generation logic

## Next Immediate Steps
1. Implement refresh token endpoint
2. Add rate limiting to login endpoint
3. Create password reset flow
```

## Automatic Detection

This command will automatically:
- Check `.claude/.edit-log.json` to see what files were edited
- Find the most recently active feature directory
- Determine what needs updating

## When to Use This Command

Run `/dev-docs-update` when:
- About to reach context limit (before compaction)
- Taking a break from a multi-session feature
- Switching to work on a different feature
- Making significant progress on active feature
- End of each coding session on large feature

## After Updating

The command will:
1. Show what was updated
2. Confirm docs are saved
3. Tell you how to resume: "Continue from dev/active/[feature-name]/"

---

**Now**: Analyze recent work, identify the active feature, and update its documentation with current progress.
