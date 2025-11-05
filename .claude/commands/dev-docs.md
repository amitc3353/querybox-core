---
description: Generate comprehensive dev docs (plan/context/tasks) for a feature that will span multiple sessions
---

# Generate Development Documentation

You are about to create development documentation for a large feature that will be implemented across multiple coding sessions.

## Your Task

1. **Analyze the feature request** from the user's prompt or recent conversation
2. **Create a comprehensive plan** covering:
   - Strategic approach and architecture decisions
   - Key files and components involved
   - Potential challenges and solutions
   - Implementation phases/milestones

3. **Generate three documentation files** in `dev/active/[feature-name]/`:

   **a) plan.md** - Strategic Plan
   - High-level overview of the feature
   - Architecture and design decisions
   - Implementation strategy
   - Success criteria

   **b) context.md** - Implementation Context
   - Key files being modified/created
   - Important code patterns to follow
   - Dependencies and prerequisites
   - Current progress snapshot
   - Next immediate steps

   **c) tasks.md** - Task Checklist
   - Markdown checklist format with `- [ ]` items
   - Ordered by implementation sequence
   - Specific, actionable items
   - Include testing tasks
   - Include documentation tasks

## Guidelines

- **Feature naming**: Use lowercase-kebab-case for directory names (e.g., `user-authentication`, `hybrid-search-optimization`)
- **Be comprehensive**: These docs help restore full context after conversation resets
- **Stay current**: Include current state, not just future plans
- **Be specific**: Reference actual file paths (e.g., `backend/api/routes/search.py:45`)
- **Track progress**: In tasks.md, mark completed items with `- [x]`

## Example Directory Structure

```
dev/active/
├── user-authentication/
│   ├── plan.md
│   ├── context.md
│   └── tasks.md
├── hybrid-search-optimization/
│   ├── plan.md
│   ├── context.md
│   └── tasks.md
```

## When to Use This Command

Use `/dev-docs` when:
- Starting a feature that will take multiple sessions
- Working on complex refactoring
- Implementing a new module or subsystem
- Need to preserve context across conversation resets

## After Creating Docs

Tell the user:
1. Where the docs were created
2. How to resume: "To continue this work in a new session, say: 'Continue from dev/active/[feature-name]/'"
3. Remind them to run `/dev-docs-update` before context compaction to save progress

---

**Now**: Ask the user which feature they want to create dev docs for, or analyze the recent conversation to determine the feature automatically.
