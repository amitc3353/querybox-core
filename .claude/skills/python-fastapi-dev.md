# Python FastAPI Development - QueryBox Patterns

## Core Principles
- **Async-first**: All routes use `async def`, database sessions via `AsyncSession`
- **Pydantic validation**: All request/response models inherit from `BaseModel`
- **Dependency injection**: Use FastAPI's `Depends()` for database sessions, auth, etc.
- **Structured logging**: Use `structlog` for all logging operations
- **Error handling**: Catch exceptions and return appropriate HTTP status codes

## FastAPI Route Patterns

### Basic CRUD Route Structure
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

router = APIRouter(prefix="/api/v1/resource", tags=["resource"])

@router.post("/", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    resource: ResourceCreate,
    db: AsyncSession = Depends(get_db)
) -> ResourceResponse:
    """Create a new resource.

    Args:
        resource: Resource data
        db: Database session

    Returns:
        Created resource with ID

    Raises:
        HTTPException: If validation fails or resource exists
    """
    try:
        # Implementation here
        db_resource = await create_resource_in_db(db, resource)
        return ResourceResponse.from_orm(db_resource)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## Pydantic Models

### Request/Response Pattern
```python
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional

class ResourceBase(BaseModel):
    """Base fields shared between create/update/response"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

class ResourceCreate(ResourceBase):
    """Fields required for creation"""
    pass

class ResourceUpdate(BaseModel):
    """Fields that can be updated (all optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None

class ResourceResponse(ResourceBase):
    """Response model with additional fields"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Allows .from_orm()
```

## SQLAlchemy Async Patterns

### Database Operations
```python
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

async def get_resource_by_id(db: AsyncSession, resource_id: int):
    """Get single resource by ID"""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id)
    )
    return result.scalar_one_or_none()

async def get_resources_paginated(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
):
    """Get paginated list of resources"""
    result = await db.execute(
        select(Resource)
        .offset(skip)
        .limit(limit)
        .order_by(Resource.created_at.desc())
    )
    return result.scalars().all()

async def update_resource(
    db: AsyncSession,
    resource_id: int,
    updates: dict
):
    """Update resource fields"""
    await db.execute(
        update(Resource)
        .where(Resource.id == resource_id)
        .values(**updates)
    )
    await db.commit()
```

## Celery Task Patterns

### Background Task Definition
```python
from backend.celery_app import celery_app
from celery import Task
import structlog

logger = structlog.get_logger(__name__)

class CallbackTask(Task):
    """Custom task with callbacks"""
    def on_success(self, retval, task_id, args, kwargs):
        logger.info("task_completed", task_id=task_id)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("task_failed", task_id=task_id, error=str(exc))

@celery_app.task(
    bind=True,
    base=CallbackTask,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def process_document_task(self, document_id: int):
    """Process document asynchronously.

    Args:
        document_id: ID of document to process

    Returns:
        dict with processing results
    """
    logger.info("processing_document", document_id=document_id)

    try:
        # Processing logic here
        result = {"status": "completed", "document_id": document_id}
        logger.info("document_processed", document_id=document_id)
        return result
    except Exception as e:
        logger.error("processing_failed", document_id=document_id, error=str(e))
        raise
```

### Triggering from API
```python
@router.post("/{document_id}/process")
async def trigger_processing(
    document_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Trigger async document processing"""
    # Verify document exists
    doc = await get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Queue task
    task = process_document_task.delay(document_id)

    return {
        "task_id": task.id,
        "status": "queued",
        "document_id": document_id
    }
```

## Error Handling

### Structured Exception Handling
```python
from fastapi import HTTPException, status
import structlog

logger = structlog.get_logger(__name__)

@router.get("/{resource_id}")
async def get_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get resource by ID with proper error handling"""
    try:
        resource = await get_resource_by_id(db, resource_id)

        if not resource:
            logger.warning("resource_not_found", resource_id=resource_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resource {resource_id} not found"
            )

        return ResourceResponse.from_orm(resource)

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error("unexpected_error", resource_id=resource_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
```

## Dependency Injection

### Database Session
```python
from backend.database import AsyncSessionLocal

async def get_db() -> AsyncSession:
    """Provide database session for route dependencies"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

## QueryBox-Specific Patterns

### Client-Scoped Operations
```python
@router.get("/clients/{client_id}/documents")
async def get_client_documents(
    client_id: int,
    db: AsyncSession = Depends(get_db)
):
    """All operations are scoped to client_id"""
    result = await db.execute(
        select(Document)
        .where(Document.client_id == client_id)
        .order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()
    return [DocumentResponse.from_orm(doc) for doc in documents]
```

### Configuration-Based Components
```python
# When implementing modular components, use config pattern
from backend.config import settings

def get_embedder(client_config: dict):
    """Get embedder based on client configuration"""
    embedder_type = client_config.get("embedder_type", "bge-m3")

    if embedder_type == "bge-m3":
        return BGEEmbedder()
    elif embedder_type == "openai":
        return OpenAIEmbedder()
    else:
        raise ValueError(f"Unknown embedder: {embedder_type}")
```

## Common Pitfalls to Avoid

1. **Don't mix sync/async**: Always use `async def` and `await` for database operations
2. **Don't forget `await db.commit()`**: Transactions won't persist without commit
3. **Don't use `.first()` with async**: Use `.scalar_one_or_none()` instead
4. **Don't forget error handling**: Always catch and log exceptions appropriately
5. **Don't skip Pydantic validation**: Use models for all inputs/outputs
6. **Don't hardcode values**: Use settings/config for environment-specific values

## Testing Considerations

When writing code with this skill:
- Include docstrings with Args/Returns/Raises
- Log important operations with structlog
- Use type hints for all parameters and return values
- Consider how the code will be tested (see testing-patterns skill)
- Think about retry logic for external operations

---
*Auto-activated when working with: FastAPI routes, Pydantic models, SQLAlchemy queries, Celery tasks, or backend API files*
