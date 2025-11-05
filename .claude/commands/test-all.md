---
description: Run the full pytest suite with coverage reporting and detailed results
---

# Run Full Test Suite

Run comprehensive tests on the QueryBox backend with coverage analysis and detailed reporting.

## Your Task

Execute the following test sequence and report results:

### 1. Run Full Test Suite with Coverage

```bash
pytest backend/tests/ --cov=backend --cov-report=term-missing --cov-report=html -v
```

**Flags explained:**
- `--cov=backend` - Measure coverage for backend code
- `--cov-report=term-missing` - Show which lines are missing coverage
- `--cov-report=html` - Generate HTML coverage report
- `-v` - Verbose output showing each test

### 2. Analyze and Report Results

After running tests, provide a structured summary:

**Test Results:**
- Total tests run
- Passed ✅
- Failed ❌
- Skipped ⏭️
- Warnings ⚠️

**Coverage Summary:**
- Overall coverage percentage
- Files with <80% coverage (if any)
- Critical uncovered areas

**Performance:**
- Total test execution time
- Slowest tests (>1 second)

### 3. Handle Failures

If tests fail:
1. Show the failure details
2. Identify the failing test(s)
3. Show relevant error messages and stack traces
4. Suggest likely causes
5. Ask if user wants to investigate/fix

### 4. Additional Checks

Also run:

**a) Type checking** (if mypy configured):
```bash
mypy backend/ --ignore-missing-imports
```

**b) Linting** (if configured):
```bash
flake8 backend/ --count --max-line-length=100
```

## Example Output Format

```
🧪 RUNNING FULL TEST SUITE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ TEST RESULTS
- Tests run: 156
- Passed: 154
- Failed: 2
- Skipped: 0
- Warnings: 3

❌ FAILURES
1. test_hybrid_search_with_reranking (backend/tests/integration/test_search.py:145)
   AssertionError: Expected 5 results, got 3

2. test_embedding_generation_batch (backend/tests/unit/test_embeddings.py:67)
   TimeoutError: Embedding generation exceeded 30s timeout

📊 COVERAGE SUMMARY
- Overall: 87.3%
- Below threshold (<80%):
  - backend/services/llm_service.py: 72%
  - backend/utils/pdf_parser.py: 75%

⚡ PERFORMANCE
- Total time: 45.2s
- Slowest tests:
  1. test_end_to_end_document_pipeline: 12.3s
  2. test_vector_search_1000_docs: 8.7s

💡 RECOMMENDATIONS
1. Fix failing search test - check reranking logic
2. Increase embedding timeout or optimize batch processing
3. Add tests for llm_service.py to reach 80% coverage
```

## When to Use This Command

Run `/test-all` when:
- Before committing major changes
- After implementing a new feature
- Before creating a pull request
- Investigating test failures
- Checking overall project health
- After refactoring
- Before deployment

## Environment Setup

This command assumes:
- Backend tests are in `backend/tests/`
- pytest is installed (`pip install pytest pytest-cov`)
- Database is running (for integration tests)
- Environment variables are configured

If tests require services (PostgreSQL, Redis, etc.), the command will check if they're running and warn if not.

## Quick Test Options

If user wants faster feedback:
- **Unit tests only**: `pytest backend/tests/unit/ -v`
- **Integration tests only**: `pytest backend/tests/integration/ -v`
- **Specific test file**: `pytest backend/tests/unit/test_embeddings.py -v`
- **Specific test**: `pytest backend/tests/unit/test_embeddings.py::test_bge_embedding -v`

---

**Now**: Run the full test suite and provide a comprehensive report with actionable insights.
