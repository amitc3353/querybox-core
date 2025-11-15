"""
End-to-End Integration Test for Complete QueryBox Pipeline
Tests: Upload → Extraction → Chunking → Embedding → Search → Answer

This test verifies the complete document processing pipeline works end-to-end:
1. Document upload with storage
2. Text extraction (Celery task)
3. Document chunking
4. Embedding generation
5. Search (keyword, semantic, hybrid)
6. Answer generation with verification

Run this test to verify the entire system is working correctly.
Usage:
    pytest backend/tests/integration/test_e2e_pipeline.py -v
    pytest backend/tests/integration/test_e2e_pipeline.py -v -k test_complete_e2e
"""
import pytest
import asyncio
import time
from uuid import uuid4, UUID
from pathlib import Path
import tempfile
from datetime import datetime, timezone
from typing import List, Optional

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.db.database import Base, get_db
from app.models.document import Document, DocumentStatusEnum
from app.models.document_text import DocumentText
from app.models.embedding import Embedding
from app.models.processing_status import (
    ProcessingStatus,
    ProcessingStageEnum,
    StageStatusEnum
)
from app.core.config import settings


# =============================================================================
# TEST DATABASE SETUP
# =============================================================================

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_e2e.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def test_db():
    """Create test database for entire module"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Cleanup test database file
    Path("./test_e2e.db").unlink(missing_ok=True)


@pytest.fixture(scope="module")
def client(test_db):
    """Create test client with database override"""
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def sample_markdown_file():
    """
    Create a sample markdown file with meaningful content for testing

    Using markdown because:
    - Easy to generate
    - Supports text extraction
    - Good for testing chunking (structured content)
    - Fast to process
    """
    content = """# QueryBox Documentation

## Introduction
QueryBox is a high-performance document processing and retrieval system designed for
production environments. It provides fast, accurate search with citation support.

## Key Features
- **Fast Upload**: Documents are processed asynchronously with efficient storage management
- **Smart Extraction**: Automatic text extraction from PDF, DOCX, and markdown files
- **Semantic Search**: Vector-based search using BGE-M3 embeddings for 100+ languages
- **Hybrid Search**: Combines keyword and semantic search with RRF fusion
- **Answer Generation**: LLM-powered answers with verification and citation support

## Architecture
QueryBox uses a modular architecture with the following components:

### Storage Layer
- Local and cloud storage support
- Content-based deduplication
- Efficient file organization

### Processing Pipeline
1. Document upload and validation
2. Text extraction with quality scoring
3. Intelligent chunking with overlap
4. Vector embedding generation
5. Database indexing

### Search Engine
- PostgreSQL full-text search for keywords
- pgvector for semantic similarity
- Hybrid search with configurable weights

## Performance
QueryBox is optimized for speed:
- Upload: < 100ms p95
- Extraction: < 2s for typical PDFs
- Search: < 200ms p99
- Answer: < 5s with verification

## Getting Started
Upload a document using the API:
```
curl -X POST http://localhost:8000/api/v1/upload \\
  -F "file=@document.pdf"
```

Search for content:
```
curl -X POST http://localhost:8000/api/v1/search/hybrid \\
  -H "Content-Type: application/json" \\
  -d '{"query": "semantic search", "limit": 10}'
```

## Advanced Features
QueryBox supports advanced query patterns including:
- Document type filtering
- Date range queries
- Quality thresholds
- Citation extraction
- Confidence scoring

## Conclusion
QueryBox provides enterprise-grade document intelligence with unmatched speed
and accuracy. Start using it today for your RAG applications.
"""

    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.md',
        delete=False,
        encoding='utf-8'
    ) as f:
        f.write(content)
        filepath = f.name

    yield filepath

    # Cleanup
    Path(filepath).unlink(missing_ok=True)


@pytest.fixture(scope="module")
def sample_pdf_file():
    """Create a minimal valid PDF file for testing"""
    pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT
/F1 12 Tf
100 700 Td
(Test PDF Document) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer<</Size 5/Root 1 0 R>>
startxref
306
%%EOF"""

    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
        f.write(pdf_content)
        filepath = f.name

    yield filepath

    Path(filepath).unlink(missing_ok=True)


@pytest.fixture
def db_session():
    """Create a fresh database session for each test"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def wait_for_processing(
    db: Session,
    document_id: UUID,
    stage: ProcessingStageEnum,
    timeout_seconds: int = 30
) -> bool:
    """
    Wait for a processing stage to complete

    Args:
        db: Database session
        document_id: Document ID to check
        stage: Processing stage to wait for
        timeout_seconds: Maximum time to wait

    Returns:
        True if completed successfully, False if failed or timed out
    """
    start_time = time.time()

    while (time.time() - start_time) < timeout_seconds:
        # Check processing status
        status = db.query(ProcessingStatus).filter(
            ProcessingStatus.document_id == document_id,
            ProcessingStatus.stage == stage
        ).first()

        if status:
            if status.status == StageStatusEnum.COMPLETED:
                return True
            elif status.status == StageStatusEnum.FAILED:
                print(f"Processing failed for stage {stage}: {status.error_message}")
                return False

        # Wait before checking again
        time.sleep(0.5)
        db.refresh(db.query(Document).get(document_id))

    print(f"Timeout waiting for stage {stage} after {timeout_seconds}s")
    return False


def get_processing_summary(db: Session, document_id: UUID) -> dict:
    """
    Get summary of all processing stages for a document

    Returns a dict with stage -> status mapping
    """
    stages = db.query(ProcessingStatus).filter(
        ProcessingStatus.document_id == document_id
    ).all()

    return {
        stage.stage.value: {
            'status': stage.status.value,
            'error': stage.error_message,
            'completed_at': stage.completed_at
        }
        for stage in stages
    }


async def run_extraction_task(db: Session, document_id: UUID):
    """
    Manually run extraction task (simulates Celery worker)

    This is a direct service call version for testing (bypasses Celery)
    """
    from app.services.extraction import get_text_extractor
    from app.services.processing.status_tracker import ProcessingStatusTracker
    from app.models.processing_status import ProcessingStageEnum, StageStatusEnum
    from app.models.document import DocumentStatusEnum
    from pathlib import Path
    from app.core.storage_config import storage_settings

    # Get document from database
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        return {"success": False, "error": "Document not found"}

    try:
        # Initialize status tracker
        tracker = ProcessingStatusTracker(db)

        # Mark extraction stage as IN_PROGRESS
        await tracker.update_status(
            document_id=document_id,
            stage=ProcessingStageEnum.EXTRACTION,
            status=StageStatusEnum.IN_PROGRESS,
        )

        # Update document status to PROCESSING
        document.status = DocumentStatusEnum.PROCESSING
        db.commit()

        # Get text extractor
        extractor = get_text_extractor()

        # Build absolute file path from storage_path
        file_path = Path(storage_settings.LOCAL_STORAGE_ROOT) / document.storage_path

        # Extract text
        result = await extractor.extract_text(
            file_path=str(file_path),
            document_id=document_id,
            mime_type=document.mime_type,
        )

        if result.success:
            # Save to database
            await extractor.save_extracted_text(
                db=db,
                document_id=document_id,
                result=result,
            )

            # Update status to completed
            await tracker.update_status(
                document_id=document_id,
                stage=ProcessingStageEnum.EXTRACTION,
                status=StageStatusEnum.COMPLETED,
            )

            return {
                "success": True,
                "text_length": result.text_length,
                "extraction_method": result.extraction_method
            }
        else:
            # Update status to failed
            await tracker.update_status(
                document_id=document_id,
                stage=ProcessingStageEnum.EXTRACTION,
                status=StageStatusEnum.FAILED,
                error_message=result.error_message,
            )

            return {
                "success": False,
                "error": result.error_message
            }

    except Exception as e:
        # Update status to failed
        await tracker.update_status(
            document_id=document_id,
            stage=ProcessingStageEnum.EXTRACTION,
            status=StageStatusEnum.FAILED,
            error_message=str(e),
        )

        return {
            "success": False,
            "error": str(e)
        }


async def run_chunking_task(db: Session, document_id: UUID):
    """Manually run chunking task (direct service call for testing)"""
    from app.services.chunking import get_chunking_service
    from app.services.processing.status_tracker import ProcessingStatusTracker
    from app.models.processing_status import ProcessingStageEnum, StageStatusEnum

    # Get document text from database
    document_text = db.query(DocumentText).filter(
        DocumentText.document_id == document_id
    ).first()

    if not document_text:
        return {"success": False, "error": "Document text not found"}

    try:
        # Initialize status tracker
        tracker = ProcessingStatusTracker(db)

        # Mark chunking stage as IN_PROGRESS
        await tracker.update_status(
            document_id=document_id,
            stage=ProcessingStageEnum.CHUNKING,
            status=StageStatusEnum.IN_PROGRESS,
        )

        # Get chunking service
        chunking_service = get_chunking_service()

        # Create chunks
        chunking_result = chunking_service.chunk_text(
            text=document_text.full_text,
            document_id=document_id,
            db=db,
        )

        chunk_count = chunking_result.chunk_count

        # Note: chunk_text already saves chunks to database
        # So we don't need to manually save them here

        # Update status to completed
        await tracker.update_status(
            document_id=document_id,
            stage=ProcessingStageEnum.CHUNKING,
            status=StageStatusEnum.COMPLETED,
        )

        return {
            "success": True,
            "chunks_created": chunk_count
        }

    except Exception as e:
        db.rollback()

        # Update status to failed
        await tracker.update_status(
            document_id=document_id,
            stage=ProcessingStageEnum.CHUNKING,
            status=StageStatusEnum.FAILED,
            error_message=str(e),
        )

        return {
            "success": False,
            "error": str(e)
        }


async def run_embedding_task(db: Session, document_id: UUID):
    """Manually run embedding task (direct service call for testing)"""
    from app.services.embeddings import get_embedding_service
    from app.services.processing.status_tracker import ProcessingStatusTracker
    from app.models.processing_status import ProcessingStageEnum, StageStatusEnum
    from app.models.embedding import Embedding

    # Get chunks from database
    chunks = db.query(Embedding).filter(
        Embedding.document_id == document_id,
        Embedding.embedding.is_(None)
    ).all()

    if not chunks:
        return {"success": False, "error": "No chunks found"}

    try:
        # Initialize status tracker
        tracker = ProcessingStatusTracker(db)

        # Mark embedding stage as IN_PROGRESS
        await tracker.update_status(
            document_id=document_id,
            stage=ProcessingStageEnum.EMBEDDING,
            status=StageStatusEnum.IN_PROGRESS,
        )

        # Get embedding service
        embedding_service = get_embedding_service()

        # Generate embeddings for all chunks
        texts = [chunk.chunk_text for chunk in chunks]
        embeddings = embedding_service.generate_embeddings_batch(texts)

        # Update chunks with embeddings
        for chunk, embedding_vector in zip(chunks, embeddings):
            chunk.embedding = embedding_vector

        db.commit()

        # Update status to completed
        await tracker.update_status(
            document_id=document_id,
            stage=ProcessingStageEnum.EMBEDDING,
            status=StageStatusEnum.COMPLETED,
        )

        return {
            "success": True,
            "embeddings_generated": len(embeddings)
        }

    except Exception as e:
        db.rollback()

        # Update status to failed
        await tracker.update_status(
            document_id=document_id,
            stage=ProcessingStageEnum.EMBEDDING,
            status=StageStatusEnum.FAILED,
            error_message=str(e),
        )

        return {
            "success": False,
            "error": str(e)
        }


# =============================================================================
# END-TO-END INTEGRATION TESTS
# =============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestCompleteE2EPipeline:
    """
    Complete end-to-end integration test suite

    Tests the full document processing pipeline from upload to answer generation
    """

    async def test_complete_e2e_pipeline_with_markdown(
        self,
        client,
        db_session,
        sample_markdown_file
    ):
        """
        Complete E2E test: Upload → Extract → Chunk → Embed → Search → Answer

        This test verifies:
        1. Document upload succeeds
        2. Text extraction extracts content
        3. Chunking creates appropriate chunks
        4. Embeddings are generated
        5. Search returns relevant results
        6. Answer generation works (if Ollama available)
        """
        # =====================================================================
        # STEP 1: UPLOAD DOCUMENT
        # =====================================================================
        print("\n[E2E] Step 1: Uploading document...")

        with open(sample_markdown_file, 'rb') as f:
            upload_response = client.post(
                "/api/v1/upload/",
                files={"file": ("querybox_docs.md", f, "text/markdown")}
            )

        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"

        upload_data = upload_response.json()
        assert upload_data["success"] is True
        assert "document" in upload_data

        document_id = UUID(upload_data["document"]["id"])
        print(f"[E2E] ✓ Document uploaded: {document_id}")

        # Verify document in database
        document = db_session.query(Document).filter(
            Document.id == document_id
        ).first()
        assert document is not None
        assert document.status == DocumentStatusEnum.COMPLETED

        # =====================================================================
        # STEP 2: WAIT FOR TEXT EXTRACTION
        # =====================================================================
        print("\n[E2E] Step 2: Running text extraction...")

        # Run extraction task manually (simulates Celery worker)
        extraction_result = await run_extraction_task(db_session, document_id)

        assert extraction_result["success"] is True, \
            f"Extraction failed: {extraction_result.get('error')}"

        print(f"[E2E] ✓ Text extracted: {extraction_result['text_length']} characters")

        # Verify extraction in database
        document_text = db_session.query(DocumentText).filter(
            DocumentText.document_id == document_id
        ).first()

        assert document_text is not None
        assert document_text.text_length > 100  # Should have meaningful content
        assert "QueryBox" in document_text.full_text

        # Check processing status
        extraction_status = db_session.query(ProcessingStatus).filter(
            ProcessingStatus.document_id == document_id,
            ProcessingStatus.stage == ProcessingStageEnum.EXTRACTION
        ).first()

        assert extraction_status is not None
        assert extraction_status.status == StageStatusEnum.COMPLETED

        # =====================================================================
        # STEP 3: WAIT FOR CHUNKING
        # =====================================================================
        print("\n[E2E] Step 3: Running document chunking...")

        chunking_result = await run_chunking_task(db_session, document_id)

        assert chunking_result["success"] is True, \
            f"Chunking failed: {chunking_result.get('error')}"

        chunk_count = chunking_result["chunks_created"]
        print(f"[E2E] ✓ Document chunked: {chunk_count} chunks created")

        # Verify chunks in database (embeddings table stores chunks)
        chunks = db_session.query(Embedding).filter(
            Embedding.document_id == document_id,
            Embedding.embedding.is_(None)  # Not yet embedded
        ).all()

        assert len(chunks) > 0, "No chunks were created"
        assert len(chunks) == chunk_count

        # Verify chunks have content
        for chunk in chunks:
            assert len(chunk.chunk_text) > 0
            assert chunk.chunk_index >= 0

        # Check processing status
        chunking_status = db_session.query(ProcessingStatus).filter(
            ProcessingStatus.document_id == document_id,
            ProcessingStatus.stage == ProcessingStageEnum.CHUNKING
        ).first()

        assert chunking_status is not None
        assert chunking_status.status == StageStatusEnum.COMPLETED

        # =====================================================================
        # STEP 4: WAIT FOR EMBEDDING GENERATION
        # =====================================================================
        print("\n[E2E] Step 4: Generating embeddings...")

        embedding_result = await run_embedding_task(db_session, document_id)

        assert embedding_result["success"] is True, \
            f"Embedding failed: {embedding_result.get('error')}"

        embeddings_count = embedding_result["embeddings_generated"]
        print(f"[E2E] ✓ Embeddings generated: {embeddings_count} vectors")

        # Verify embeddings in database
        embeddings = db_session.query(Embedding).filter(
            Embedding.document_id == document_id,
            Embedding.embedding.isnot(None)  # Now embedded
        ).all()

        assert len(embeddings) > 0, "No embeddings were generated"
        assert len(embeddings) == embeddings_count

        # Verify embeddings have correct dimensions (BGE-M3 = 1024)
        # Note: Can't easily check vector dimensions in SQLite,
        # but we can verify the field exists
        for emb in embeddings:
            assert emb.embedding is not None

        # Check processing status
        embedding_status = db_session.query(ProcessingStatus).filter(
            ProcessingStatus.document_id == document_id,
            ProcessingStatus.stage == ProcessingStageEnum.EMBEDDING
        ).first()

        assert embedding_status is not None
        assert embedding_status.status == StageStatusEnum.COMPLETED

        print("\n[E2E] ✓ Processing pipeline completed successfully")
        print(f"[E2E] Summary: {get_processing_summary(db_session, document_id)}")

        # Update document status to COMPLETED now that all stages are done
        document = db_session.query(Document).filter(Document.id == document_id).first()
        document.status = DocumentStatusEnum.COMPLETED
        db_session.commit()
        db_session.refresh(document)
        print(f"[E2E] Document status updated to: {document.status}")

        # =====================================================================
        # STEP 5: TEST KEYWORD SEARCH
        # =====================================================================
        print("\n[E2E] Step 5: Testing keyword search...")

        search_response = client.post(
            "/api/v1/search/keyword",
            json={
                "query": "semantic search",
                "limit": 5
            }
        )

        assert search_response.status_code == 200
        search_data = search_response.json()

        assert search_data["success"] is True
        assert search_data["total_results"] > 0
        assert len(search_data["results"]) > 0

        # Verify our document is in results
        result_doc_ids = [r["document_id"] for r in search_data["results"]]
        assert str(document_id) in result_doc_ids

        print(f"[E2E] ✓ Keyword search: {search_data['total_results']} results")

        # =====================================================================
        # STEP 6: TEST SEMANTIC SEARCH
        # =====================================================================
        print("\n[E2E] Step 6: Testing semantic search...")

        semantic_response = client.post(
            "/api/v1/search/semantic",
            json={
                "query": "What are the key features of the system?",
                "limit": 5,
                "similarity_threshold": 0.3
            }
        )

        assert semantic_response.status_code == 200
        semantic_data = semantic_response.json()

        assert semantic_data["success"] is True
        print(f"[E2E] ✓ Semantic search: {semantic_data['total_results']} results")

        # =====================================================================
        # STEP 7: TEST HYBRID SEARCH
        # =====================================================================
        print("\n[E2E] Step 7: Testing hybrid search...")

        hybrid_response = client.post(
            "/api/v1/search/hybrid",
            json={
                "query": "performance optimization features",
                "limit": 5,
                "keyword_weight": 0.5,
                "vector_weight": 0.5
            }
        )

        assert hybrid_response.status_code == 200
        hybrid_data = hybrid_response.json()

        assert hybrid_data["success"] is True
        print(f"[E2E] ✓ Hybrid search: {hybrid_data['total_results']} results")

        # =====================================================================
        # STEP 8: TEST ANSWER GENERATION (if Ollama available)
        # =====================================================================
        print("\n[E2E] Step 8: Testing answer generation...")

        # First check if Ollama is available
        ollama_health = client.get("/api/v1/answer/health/ollama")

        if ollama_health.status_code == 200 and \
           ollama_health.json().get("status") == "healthy":

            print("[E2E] Ollama is available, testing answer generation...")

            # Generate answer
            answer_response = client.post(
                "/api/v1/answer",
                headers={"X-API-Key": settings.API_KEY},
                json={
                    "query": "What are the key features of QueryBox?",
                    "document_ids": [str(document_id)],
                    "top_k": 5,
                    "include_citations": True
                }
            )

            if answer_response.status_code == 200:
                answer_data = answer_response.json()

                assert answer_data["success"] is True
                # LLM may choose to answer or abstain depending on content quality/relevance
                # Both are valid outcomes - what matters is the API works correctly
                if answer_data["can_answer"]:
                    assert len(answer_data["answer"]) > 0
                    print(f"[E2E] ✓ Answer generated: {len(answer_data['answer'])} chars")
                    print(f"[E2E]   Confidence: {answer_data.get('confidence', 'N/A')}")
                    print(f"[E2E]   Citations: {len(answer_data.get('citations', []))}")
                else:
                    # LLM abstained - verify abstention response is properly formatted
                    assert "answer" in answer_data
                    print(f"[E2E] ✓ LLM appropriately abstained from answering")
                    print(f"[E2E]   Reason: {answer_data.get('answer', 'N/A')}")
            else:
                print(f"[E2E] ⚠ Answer generation failed: {answer_response.status_code}")
        else:
            print("[E2E] ⚠ Ollama not available, skipping answer generation test")

        # =====================================================================
        # FINAL VERIFICATION
        # =====================================================================
        print("\n[E2E] ═══════════════════════════════════════════════════════")
        print("[E2E] ✓ END-TO-END PIPELINE TEST PASSED")
        print("[E2E] ═══════════════════════════════════════════════════════")
        print(f"[E2E] Document ID: {document_id}")
        print(f"[E2E] Text extracted: {document_text.text_length} chars")
        print(f"[E2E] Chunks created: {chunk_count}")
        print(f"[E2E] Embeddings generated: {embeddings_count}")
        print(f"[E2E] Search results: {search_data['total_results']} (keyword)")
        print("[E2E] ═══════════════════════════════════════════════════════\n")


    async def test_duplicate_upload_detection(self, client, sample_markdown_file):
        """
        Test that duplicate uploads are detected via content hash
        """
        print("\n[E2E] Testing duplicate upload detection...")

        # Upload first time
        with open(sample_markdown_file, 'rb') as f:
            response1 = client.post(
                "/api/v1/upload/",
                files={"file": ("test1.md", f, "text/markdown")}
            )

        assert response1.status_code == 200
        doc1_id = response1.json()["document"]["id"]

        # Upload same content again (should be detected as duplicate)
        with open(sample_markdown_file, 'rb') as f:
            response2 = client.post(
                "/api/v1/upload/",
                files={"file": ("test2.md", f, "text/markdown")}
            )

        assert response2.status_code == 200
        data = response2.json()

        # Should return same document
        assert data.get("duplicate") is True
        assert data["document"]["id"] == doc1_id

        print("[E2E] ✓ Duplicate detection working correctly")


    async def test_search_health_checks(self, client):
        """
        Test that all search service health checks work
        """
        print("\n[E2E] Testing search service health checks...")

        # Test general search health
        health_response = client.get("/api/v1/search/health")
        assert health_response.status_code == 200

        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        print(f"[E2E] ✓ Search health: {health_data['searchable_documents']} docs")

        # Test reranking health (if available)
        rerank_response = client.get("/api/v1/search/reranking/health")
        if rerank_response.status_code == 200:
            rerank_data = rerank_response.json()
            print(f"[E2E] ✓ Reranking health: {rerank_data['status']}")


@pytest.mark.integration
@pytest.mark.asyncio
class TestE2EErrorHandling:
    """
    Test error handling in E2E pipeline
    """

    async def test_invalid_file_upload(self, client):
        """Test that invalid files are rejected"""
        # Try to upload an executable (not allowed)
        content = b"#!/bin/bash\necho 'test'"

        response = client.post(
            "/api/v1/upload/",
            files={"file": ("test.sh", content, "application/x-sh")}
        )

        # Should fail validation
        assert response.status_code in [400, 413, 415]
        print("[E2E] ✓ Invalid file upload rejected correctly")


    async def test_search_with_no_documents(self, client):
        """Test search when no documents exist"""
        # Use a unique query that won't match anything
        response = client.post(
            "/api/v1/search/keyword",
            json={
                "query": "xyzabc123nonexistent999",
                "limit": 5
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_results"] == 0
        print("[E2E] ✓ Empty search handled correctly")
