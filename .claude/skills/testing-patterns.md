# Testing Patterns - QueryBox Test Suite

## Core Testing Principles
- **Fixtures over duplication**: Reuse common setup via pytest fixtures
- **Async all the way**: Use `pytest-asyncio` for async database tests
- **Isolation**: Each test should be independent and repeatable
- **Coverage matters**: Aim for >80% coverage on business logic
- **Fast feedback**: Unit tests < 100ms, integration tests < 1s

## Pytest Configuration

### Essential conftest.py Setup
```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient

from backend.main import app
from backend.database import Base, get_db

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/querybox_test"

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestAsyncSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Provide clean database session for each test"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session
        await session.close()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Provide HTTP client with test database"""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
```

## Test Organization

### File Structure
```
backend/tests/
├── conftest.py          # Shared fixtures
├── unit/                # Fast, isolated tests
│   ├── test_models.py
│   ├── test_schemas.py
│   └── test_utils.py
├── integration/         # Database + API tests
│   ├── test_api_documents.py
│   ├── test_api_search.py
│   └── test_celery_tasks.py
└── e2e/                 # Full flow tests
    └── test_upload_to_search.py
```

## Unit Testing Patterns

### Testing Pydantic Models
```python
import pytest
from pydantic import ValidationError
from backend.schemas import DocumentCreate

def test_document_create_valid():
    """Test valid document creation"""
    doc = DocumentCreate(
        filename="test.pdf",
        client_id=1,
        content_type="application/pdf"
    )
    assert doc.filename == "test.pdf"
    assert doc.client_id == 1

def test_document_create_invalid_filename():
    """Test validation rejects empty filename"""
    with pytest.raises(ValidationError) as exc_info:
        DocumentCreate(
            filename="",
            client_id=1,
            content_type="application/pdf"
        )

    errors = exc_info.value.errors()
    assert any(e["loc"] == ("filename",) for e in errors)
```

### Testing Utility Functions
```python
from backend.utils import sanitize_filename, calculate_confidence

def test_sanitize_filename_removes_special_chars():
    """Test filename sanitization"""
    result = sanitize_filename("test@file#123.pdf")
    assert result == "test_file_123.pdf"

def test_sanitize_filename_preserves_extension():
    """Test extension is preserved"""
    result = sanitize_filename("document.PDF")
    assert result.endswith(".pdf")

@pytest.mark.parametrize("score,expected", [
    (0.9, "high"),
    (0.7, "medium"),
    (0.5, "low"),
    (0.2, "very_low")
])
def test_calculate_confidence(score, expected):
    """Test confidence level calculation"""
    assert calculate_confidence(score) == expected
```

## Integration Testing Patterns

### Testing FastAPI Routes
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_document(client: AsyncClient, db_session):
    """Test document creation endpoint"""
    response = await client.post(
        "/api/v1/documents",
        json={
            "filename": "test.pdf",
            "client_id": 1,
            "content_type": "application/pdf"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert "id" in data
    assert "created_at" in data

@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient):
    """Test 404 for non-existent document"""
    response = await client.get("/api/v1/documents/99999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_list_documents_pagination(client: AsyncClient, db_session):
    """Test document listing with pagination"""
    # Create test documents
    for i in range(5):
        await client.post(
            "/api/v1/documents",
            json={
                "filename": f"test{i}.pdf",
                "client_id": 1,
                "content_type": "application/pdf"
            }
        )

    # Test pagination
    response = await client.get("/api/v1/documents?skip=0&limit=3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
```

### Testing Database Operations
```python
import pytest
from sqlalchemy import select
from backend.models import Document
from backend.services.document_service import create_document, get_document_by_id

@pytest.mark.asyncio
async def test_create_document_in_db(db_session):
    """Test creating document in database"""
    doc_data = {
        "filename": "test.pdf",
        "client_id": 1,
        "content_type": "application/pdf"
    }

    doc = await create_document(db_session, doc_data)

    assert doc.id is not None
    assert doc.filename == "test.pdf"
    assert doc.created_at is not None

@pytest.mark.asyncio
async def test_get_document_cascade_delete(db_session):
    """Test that deleting client deletes documents"""
    # Create client with document
    client = Client(name="Test Client")
    db_session.add(client)
    await db_session.flush()

    doc = Document(filename="test.pdf", client_id=client.id)
    db_session.add(doc)
    await db_session.commit()

    # Delete client
    await db_session.delete(client)
    await db_session.commit()

    # Verify document is gone
    result = await db_session.execute(
        select(Document).where(Document.id == doc.id)
    )
    assert result.scalar_one_or_none() is None
```

## Mocking Patterns

### Mocking External Services
```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.services.llm_service import generate_answer

@pytest.mark.asyncio
async def test_generate_answer_with_mocked_llm():
    """Test answer generation with mocked LLM"""
    mock_llm_response = {
        "answer": "Test answer",
        "confidence": 0.85
    }

    with patch("backend.services.llm_service.call_ollama") as mock_ollama:
        mock_ollama.return_value = mock_llm_response

        result = await generate_answer(
            query="What is this?",
            context="Some context"
        )

        assert result["answer"] == "Test answer"
        assert result["confidence"] == 0.85
        mock_ollama.assert_called_once()
```

### Mocking Celery Tasks
```python
import pytest
from unittest.mock import patch, MagicMock
from backend.tasks import process_document_task

@pytest.mark.asyncio
async def test_trigger_processing_queues_task(client: AsyncClient):
    """Test that processing endpoint queues Celery task"""
    with patch("backend.tasks.process_document_task.delay") as mock_task:
        mock_task.return_value = MagicMock(id="test-task-id")

        response = await client.post("/api/v1/documents/1/process")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-id"
        mock_task.assert_called_once_with(1)
```

## Fixture Patterns

### Reusable Test Data Fixtures
```python
import pytest
from backend.models import Client, Document

@pytest.fixture
async def test_client(db_session):
    """Provide test client for tests"""
    client = Client(
        name="Test Client",
        config={"embedder": "bge-m3"}
    )
    db_session.add(client)
    await db_session.commit()
    await db_session.refresh(client)
    return client

@pytest.fixture
async def test_document(db_session, test_client):
    """Provide test document for tests"""
    doc = Document(
        filename="test.pdf",
        client_id=test_client.id,
        status="completed"
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc

# Usage in tests
@pytest.mark.asyncio
async def test_document_belongs_to_client(test_document, test_client):
    """Test document-client relationship"""
    assert test_document.client_id == test_client.id
```

### Parametrized Fixtures
```python
import pytest

@pytest.fixture(params=["bge-m3", "openai", "cohere"])
def embedder_type(request):
    """Test with multiple embedder types"""
    return request.param

@pytest.mark.asyncio
async def test_embedding_with_different_types(embedder_type):
    """Test that all embedder types work"""
    embedder = get_embedder(embedder_type)
    result = await embedder.embed("test text")
    assert len(result) > 0
```

## Testing Async Operations

### Testing Background Tasks
```python
import pytest
import asyncio
from backend.tasks import process_document_task

@pytest.mark.asyncio
async def test_document_processing_task():
    """Test document processing completes successfully"""
    result = await asyncio.to_thread(
        process_document_task.apply,
        args=[1]
    )

    assert result.successful()
    assert result.result["status"] == "completed"
```

## Coverage Best Practices

### Running Tests with Coverage
```bash
# Run all tests with coverage
pytest backend/tests/ --cov=backend --cov-report=html

# Run specific test file
pytest backend/tests/integration/test_api_documents.py -v

# Run with keyword filter
pytest backend/tests/ -k "document" -v

# Stop on first failure
pytest backend/tests/ -x
```

### What to Test
Priority levels:
1. **Critical path**: User flows (upload → process → search → answer)
2. **Business logic**: Parsers, embedders, retrievers, LLM integration
3. **Error handling**: Invalid inputs, edge cases, failures
4. **API contracts**: Request/response schemas, status codes
5. **Database operations**: CRUD, relationships, transactions

### What to Skip
- Third-party library internals
- Simple property getters/setters
- Config loading (unless complex logic)
- Pure pass-through code

## QueryBox-Specific Patterns

### Testing Client-Scoped Operations
```python
@pytest.mark.asyncio
async def test_clients_cannot_access_other_documents(
    client: AsyncClient,
    test_document
):
    """Test that client 1 cannot access client 2's documents"""
    # Create document for client 2
    other_doc_response = await client.post(
        "/api/v1/documents",
        json={"filename": "other.pdf", "client_id": 2}
    )
    other_doc_id = other_doc_response.json()["id"]

    # Try to access as client 1
    response = await client.get(
        f"/api/v1/clients/1/documents/{other_doc_id}"
    )

    assert response.status_code == 404
```

### Testing Configuration-Based Components
```python
@pytest.mark.parametrize("config,expected_type", [
    ({"embedder": "bge-m3"}, BGEEmbedder),
    ({"embedder": "openai"}, OpenAIEmbedder),
])
def test_component_factory(config, expected_type):
    """Test that factory returns correct component type"""
    embedder = create_embedder(config)
    assert isinstance(embedder, expected_type)
```

## Common Testing Pitfalls

1. **Not using async fixtures**: Must use `@pytest_asyncio.fixture` for async fixtures
2. **Not awaiting async calls**: All async operations need `await`
3. **Test pollution**: Always clean up database between tests
4. **Overmocking**: Mock external services, not your own code
5. **Brittle assertions**: Test behavior, not implementation details
6. **Slow tests**: Keep unit tests fast, isolate slow integration tests

## Continuous Integration

Tests should run on every commit:
```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    pytest backend/tests/ --cov=backend --cov-fail-under=80
```

---
*Auto-activated when working with: Test files, pytest fixtures, test patterns, or writing/reviewing tests*
