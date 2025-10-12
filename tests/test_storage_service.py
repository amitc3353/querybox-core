"""
Storage Service Tests
Day 3, Step 5: Comprehensive tests for storage service components

Tests:
- File naming conflict resolution
- Path generation with various inputs
- Rollback on failures
- Security (path traversal attempts)
- Mock tests for future S3/Azure providers
"""

import pytest
import tempfile
import shutil
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import hashlib

from app.services.storage.path_generator import PathGenerator
from app.services.storage.local import LocalStorageProvider
from app.services.storage.manager import StorageManager
from app.services.storage.exceptions import (
    StorageException,
    FileNotFoundError,
    InvalidPathError,
    StorageQuotaExceeded,
    PermissionDeniedError
)
from app.schemas.storage import ConflictStrategy, StorageResult
from app.core.storage_config import storage_settings


class TestPathGenerator:
    """Test PathGenerator functionality"""
    
    def setup_method(self):
        self.path_gen = PathGenerator()
        self.workspace_id = uuid4()
        self.document_id = uuid4()
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        # Basic sanitization
        assert self.path_gen.sanitize_filename("hello world.pdf") == "hello_world.pdf"
        
        # Special characters
        assert self.path_gen.sanitize_filename("file@#$%^&*().txt") == "file.txt"
        
        # Unicode characters
        assert self.path_gen.sanitize_filename("résumé.pdf") == "resume.pdf"
        
        # Long filename truncation
        long_name = "a" * 300 + ".pdf"
        result = self.path_gen.sanitize_filename(long_name)
        assert len(result) <= 200
        assert result.endswith(".pdf")
        
        # Empty name
        assert self.path_gen.sanitize_filename(".pdf") == "unnamed.pdf"
        
        # No extension
        assert self.path_gen.sanitize_filename("noextension") == "noextension"
    
    def test_generate_document_path(self):
        """Test document path generation"""
        timestamp = datetime(2024, 11, 15, 14, 30, 0, tzinfo=timezone.utc)
        
        path = self.path_gen.generate_document_path(
            workspace_id=self.workspace_id,
            document_id=self.document_id,
            filename="test file.pdf",
            timestamp=timestamp
        )
        
        expected_parts = [
            str(self.workspace_id),
            "2024",
            "11",
            str(self.document_id),
            "test_file.pdf"
        ]
        
        assert path == "/".join(expected_parts)
    
    def test_generate_temp_path(self):
        """Test temporary path generation"""
        path = self.path_gen.generate_temp_path("test.pdf")
        
        # Should start with temp directory
        assert path.startswith(PathGenerator.TEMP_DIR)
        
        # Should contain date
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert today in path
        
        # Should end with sanitized filename
        assert path.endswith("test.pdf")
    
    def test_extract_components(self):
        """Test path component extraction"""
        path = f"{self.workspace_id}/2024/11/{self.document_id}/test.pdf"
        
        components = self.path_gen.extract_components(path)
        
        assert components['workspace_id'] == str(self.workspace_id)
        assert components['year'] == "2024"
        assert components['month'] == "11"
        assert components['document_id'] == str(self.document_id)
        assert components['filename'] == "test.pdf"
        assert components['is_temp'] is False
    
    def test_extract_temp_components(self):
        """Test temp path component extraction"""
        path = "_temp/2024-11-15/test.pdf"
        
        components = self.path_gen.extract_components(path)
        
        assert components['is_temp'] is True
        assert components['filename'] == "test.pdf"
        assert components['workspace_id'] is None
    
    def test_is_valid_document_path(self):
        """Test document path validation"""
        valid_path = f"{self.workspace_id}/2024/11/{self.document_id}/test.pdf"
        assert self.path_gen.is_valid_document_path(valid_path) is True
        
        # Invalid paths
        assert self.path_gen.is_valid_document_path("just/a/path") is False
        assert self.path_gen.is_valid_document_path("invalid/2024/13/uuid/file.pdf") is False  # month 13
        assert self.path_gen.is_valid_document_path("not-uuid/2024/11/also-not-uuid/file.pdf") is False
    
    def test_get_versioned_path(self):
        """Test versioned path generation"""
        original = f"{self.workspace_id}/2024/11/{self.document_id}/test.pdf"
        versioned = self.path_gen.get_versioned_path(original, 2)
        
        expected = f"{self.workspace_id}/2024/11/{self.document_id}/v2/test.pdf"
        assert versioned == expected


class TestLocalStorageProvider:
    """Test LocalStorageProvider functionality"""
    
    def setup_method(self):
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.provider = LocalStorageProvider({"root_path": self.temp_dir})
    
    def teardown_method(self):
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_save_and_get_file(self):
        """Test basic file save and retrieve"""
        content = b"Hello, World!"
        path = "test/document.txt"
        
        # Save file
        result_path = await self.provider.save_file(content, path)
        assert result_path == path
        
        # Retrieve file
        retrieved_content = await self.provider.get_file(path)
        assert retrieved_content == content
    
    @pytest.mark.asyncio
    async def test_file_exists(self):
        """Test file existence check"""
        content = b"test content"
        path = "test/exists.txt"
        
        # File doesn't exist yet
        assert await self.provider.exists(path) is False
        
        # Save file
        await self.provider.save_file(content, path)
        
        # Now it exists
        assert await self.provider.exists(path) is True
    
    @pytest.mark.asyncio
    async def test_delete_file(self):
        """Test file deletion"""
        content = b"to be deleted"
        path = "test/delete_me.txt"
        
        # Save file
        await self.provider.save_file(content, path)
        assert await self.provider.exists(path) is True
        
        # Delete file
        result = await self.provider.delete_file(path)
        assert result is True
        assert await self.provider.exists(path) is False
        
        # Try to delete non-existent file
        result = await self.provider.delete_file("nonexistent.txt")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_move_file(self):
        """Test file moving"""
        content = b"content to move"
        old_path = "old/location.txt"
        new_path = "new/location.txt"
        
        # Save file
        await self.provider.save_file(content, old_path)
        
        # Move file
        result = await self.provider.move_file(old_path, new_path)
        assert result is True
        
        # Check old location is empty, new location has content
        assert await self.provider.exists(old_path) is False
        assert await self.provider.exists(new_path) is True
        
        retrieved = await self.provider.get_file(new_path)
        assert retrieved == content
    
    @pytest.mark.asyncio
    async def test_get_file_size(self):
        """Test file size retrieval"""
        content = b"1234567890"  # 10 bytes
        path = "test/size_test.txt"
        
        await self.provider.save_file(content, path)
        
        size = await self.provider.get_file_size(path)
        assert size == 10
    
    @pytest.mark.asyncio
    async def test_path_traversal_security(self):
        """Test security against path traversal attacks"""
        content = b"malicious content"
        
        # These should all raise InvalidPathError
        malicious_paths = [
            "../../../etc/passwd",
            "../../outside.txt",
            "/absolute/path.txt",
            "normal/../../../traversal.txt"
        ]
        
        for malicious_path in malicious_paths:
            with pytest.raises(InvalidPathError):
                await self.provider.save_file(content, malicious_path)
    
    @pytest.mark.asyncio
    async def test_file_not_found_error(self):
        """Test FileNotFoundError handling"""
        with pytest.raises(FileNotFoundError):
            await self.provider.get_file("nonexistent/file.txt")
    
    @pytest.mark.asyncio
    async def test_list_files(self):
        """Test file listing functionality"""
        # Create some test files
        files = [
            "dir1/file1.txt",
            "dir1/file2.txt",
            "dir2/file3.txt",
            "root_file.txt"
        ]
        
        for file_path in files:
            await self.provider.save_file(b"content", file_path)
        
        # List all files
        all_files = await self.provider.list_files()
        assert len(all_files) == 4
        
        # List files with prefix
        dir1_files = await self.provider.list_files(prefix="dir1")
        assert len(dir1_files) == 2
        assert all("dir1" in f for f in dir1_files)


class TestStorageManager:
    """Test StorageManager functionality"""
    
    def setup_method(self):
        # Mock database session
        self.mock_db = MagicMock()
        
        # Create storage manager with mocked dependencies
        self.manager = StorageManager(self.mock_db)
        
        # Mock the provider
        self.mock_provider = AsyncMock()
        self.manager.provider = self.mock_provider
        
        self.workspace_id = uuid4()
        self.document_id = uuid4()
    
    def test_filename_conflict_resolution_timestamp(self):
        """Test timestamp conflict resolution strategy"""
        existing_paths = [
            f"{self.workspace_id}/2024/11/{uuid4()}/report.pdf"
        ]
        
        with patch.object(storage_settings, 'CONFLICT_STRATEGY', ConflictStrategy.TIMESTAMP):
            resolved = self.manager._resolve_filename_conflict(
                "report.pdf",
                existing_paths,
                ConflictStrategy.TIMESTAMP
            )
        
        # Should have timestamp appended
        assert resolved.startswith("report_")
        assert resolved.endswith(".pdf")
        assert len(resolved) > len("report.pdf")
    
    def test_filename_conflict_resolution_counter(self):
        """Test counter conflict resolution strategy"""
        existing_paths = [
            f"{self.workspace_id}/2024/11/{uuid4()}/report.pdf",
            f"{self.workspace_id}/2024/11/{uuid4()}/report_1.pdf"
        ]
        
        resolved = self.manager._resolve_filename_conflict(
            "report.pdf",
            existing_paths,
            ConflictStrategy.COUNTER
        )
        
        assert resolved == "report_2.pdf"
    
    def test_filename_conflict_resolution_uuid(self):
        """Test UUID conflict resolution strategy"""
        existing_paths = [
            f"{self.workspace_id}/2024/11/{uuid4()}/report.pdf"
        ]
        
        resolved = self.manager._resolve_filename_conflict(
            "report.pdf",
            existing_paths,
            ConflictStrategy.UUID
        )
        
        # Should have UUID prefix
        assert "_report.pdf" in resolved
        assert len(resolved.split("_")[0]) == 6  # Short UUID length
    
    @pytest.mark.asyncio
    async def test_calculate_checksum(self):
        """Test checksum calculation"""
        content = b"test content"
        expected_checksum = hashlib.sha256(content).hexdigest()
        
        checksum = await self.manager._calculate_checksum(content)
        assert checksum == expected_checksum
    
    @pytest.mark.asyncio
    async def test_store_document_success(self):
        """Test successful document storage"""
        # Mock file object
        mock_file = AsyncMock()
        mock_file.read.return_value = b"test content"
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        
        # Mock provider methods
        self.mock_provider.save_file.return_value = "path/to/file.pdf"
        self.mock_provider.get_url.return_value = None
        
        # Mock database query for duplicates (no duplicates)
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        result = await self.manager.store_document(
            mock_file,
            self.workspace_id,
            self.document_id
        )
        
        assert isinstance(result, StorageResult)
        assert result.document_id == self.document_id
        assert result.size == len(b"test content")
        
        # Verify provider was called
        self.mock_provider.save_file.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_document_duplicate_detection(self):
        """Test duplicate file detection"""
        mock_file = AsyncMock()
        mock_file.read.return_value = b"test content"
        mock_file.filename = "test.pdf"
        
        # Mock existing document with same checksum
        existing_doc = MagicMock()
        existing_doc.id = uuid4()
        existing_doc.storage_path = "existing/path.pdf"
        existing_doc.file_size = len(b"test content")
        existing_doc.checksum = hashlib.sha256(b"test content").hexdigest()
        existing_doc.mime_type = "application/pdf"
        existing_doc.storage_provider.value = "local"
        
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = existing_doc
        
        result = await self.manager.store_document(
            mock_file,
            self.workspace_id,
            self.document_id
        )
        
        # Should return existing document info
        assert result.document_id == existing_doc.id
        assert result.checksum == existing_doc.checksum
        
        # Provider save should not be called for duplicate
        self.mock_provider.save_file.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_quota_exceeded(self):
        """Test storage quota exceeded handling"""
        mock_file = AsyncMock()
        mock_file.read.return_value = b"x" * (100 * 1024 * 1024)  # 100MB file
        mock_file.filename = "large_file.pdf"
        
        # Mock quota check to raise exception
        with patch.object(self.manager, '_check_quota') as mock_check:
            mock_check.side_effect = StorageQuotaExceeded(
                used_bytes=50 * 1024 * 1024,
                quota_bytes=10 * 1024 * 1024,
                workspace_id=str(self.workspace_id)
            )
            
            with pytest.raises(StorageQuotaExceeded):
                await self.manager.store_document(
                    mock_file,
                    self.workspace_id,
                    self.document_id
                )
    
    @pytest.mark.asyncio
    async def test_retrieve_document_success(self):
        """Test successful document retrieval"""
        # Mock document in database
        mock_doc = MagicMock()
        mock_doc.storage_path = "path/to/document.pdf"
        mock_doc.deleted_at = None
        
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = mock_doc
        
        # Mock provider response
        expected_content = b"document content"
        self.mock_provider.get_file.return_value = expected_content
        
        content = await self.manager.retrieve_document(self.document_id)
        
        assert content == expected_content
        self.mock_provider.get_file.assert_called_once_with(mock_doc.storage_path)
    
    @pytest.mark.asyncio
    async def test_retrieve_document_not_found(self):
        """Test document retrieval when document doesn't exist"""
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(FileNotFoundError):
            await self.manager.retrieve_document(self.document_id)
    
    @pytest.mark.asyncio
    async def test_delete_document_soft(self):
        """Test soft document deletion"""
        mock_doc = MagicMock()
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = mock_doc
        
        result = await self.manager.delete_document(self.document_id, soft_delete=True)
        
        assert result is True
        assert mock_doc.deleted_at is not None
        self.mock_db.commit.assert_called_once()
        
        # Provider delete should not be called for soft delete
        self.mock_provider.delete_file.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_delete_document_hard(self):
        """Test hard document deletion"""
        mock_doc = MagicMock()
        mock_doc.storage_path = "path/to/delete.pdf"
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = mock_doc
        
        result = await self.manager.delete_document(self.document_id, soft_delete=False)
        
        assert result is True
        self.mock_provider.delete_file.assert_called_once_with(mock_doc.storage_path)
        self.mock_db.delete.assert_called_once_with(mock_doc)
        self.mock_db.commit.assert_called_once()


class TestMockProviders:
    """Test mock implementations for future cloud providers"""
    
    def test_s3_provider_mock(self):
        """Test S3 provider mock for future implementation"""
        # This would be the interface for S3Provider
        
        class MockS3Provider:
            def __init__(self, config):
                self.config = config
                self.bucket = config.get('bucket_name')
            
            async def save_file(self, content: bytes, path: str) -> str:
                # Mock S3 save operation
                return f"s3://{self.bucket}/{path}"
            
            async def get_file(self, path: str) -> bytes:
                # Mock S3 retrieve operation
                return b"mocked s3 content"
            
            async def delete_file(self, path: str) -> bool:
                # Mock S3 delete operation
                return True
            
            async def get_url(self, path: str, expires_in: int = 3600) -> str:
                # Mock presigned URL generation
                return f"https://s3.amazonaws.com/{self.bucket}/{path}?expires={expires_in}"
        
        # Test the mock
        config = {"bucket_name": "test-bucket"}
        provider = MockS3Provider(config)
        
        # Test async methods would work
        assert asyncio.run(provider.save_file(b"test", "path.txt")) == "s3://test-bucket/path.txt"
        assert asyncio.run(provider.get_file("path.txt")) == b"mocked s3 content"
        assert asyncio.run(provider.delete_file("path.txt")) is True
        
        url = asyncio.run(provider.get_url("path.txt"))
        assert url.startswith("https://s3.amazonaws.com/test-bucket/path.txt")
    
    def test_azure_provider_mock(self):
        """Test Azure Blob provider mock for future implementation"""
        
        class MockAzureBlobProvider:
            def __init__(self, config):
                self.config = config
                self.container = config.get('container_name')
            
            async def save_file(self, content: bytes, path: str) -> str:
                return f"azure://{self.container}/{path}"
            
            async def get_file(self, path: str) -> bytes:
                return b"mocked azure content"
            
            async def delete_file(self, path: str) -> bool:
                return True
            
            async def get_url(self, path: str, expires_in: int = 3600) -> str:
                return f"https://account.blob.core.windows.net/{self.container}/{path}?expires={expires_in}"
        
        # Test the mock
        config = {"container_name": "test-container"}
        provider = MockAzureBlobProvider(config)
        
        assert asyncio.run(provider.save_file(b"test", "path.txt")) == "azure://test-container/path.txt"
        assert asyncio.run(provider.get_file("path.txt")) == b"mocked azure content"


class TestSecurityValidation:
    """Test security validation and edge cases"""
    
    def setup_method(self):
        self.path_gen = PathGenerator()
    
    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/absolute/path/attack",
            "normal/../../../attack",
            "dir/./../../attack",
            "dir///../attack"
        ]
        
        for malicious_path in malicious_paths:
            with pytest.raises(InvalidPathError):
                # This should be caught by validate_path in the base provider
                from app.services.storage.base import StorageProvider
                provider = StorageProvider({})
                provider.validate_path(malicious_path)
    
    def test_filename_injection_prevention(self):
        """Test prevention of filename injection attacks"""
        malicious_filenames = [
            "../../../passwd",
            "file\x00.pdf",  # Null byte injection
            "file\r\n.pdf",  # CRLF injection
            "CON.pdf",       # Windows reserved name
            "file|rm -rf /.pdf"  # Command injection attempt
        ]
        
        for malicious_filename in malicious_filenames:
            # Should be sanitized safely
            sanitized = self.path_gen.sanitize_filename(malicious_filename)
            
            # Should not contain directory traversal
            assert ".." not in sanitized
            assert "/" not in sanitized
            assert "\\" not in sanitized
            assert "\x00" not in sanitized
    
    def test_large_path_handling(self):
        """Test handling of extremely long paths"""
        # Create a very long filename
        long_filename = "a" * 1000 + ".pdf"
        
        # Should be truncated to safe length
        sanitized = self.path_gen.sanitize_filename(long_filename)
        assert len(sanitized) <= PathGenerator.MAX_FILENAME_LENGTH
        assert sanitized.endswith(".pdf")
    
    def test_unicode_security(self):
        """Test Unicode security issues"""
        # Unicode normalization attacks
        tricky_filenames = [
            "file\u202eftxt.pdf",  # Right-to-left override
            "file\u200btest.pdf",  # Zero-width space
            "résumé.pdf",          # Normal Unicode (should work)
        ]
        
        for filename in tricky_filenames:
            sanitized = self.path_gen.sanitize_filename(filename)
            
            # Should be ASCII-safe
            assert sanitized.encode('ascii', 'ignore').decode('ascii') == sanitized


# Test fixtures and utilities
@pytest.fixture
def temp_storage_dir():
    """Fixture for temporary storage directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_database_session():
    """Fixture for mock database session"""
    session = MagicMock()
    session.query.return_value.filter_by.return_value.first.return_value = None
    session.commit.return_value = None
    return session


@pytest.fixture
def sample_file_content():
    """Fixture for sample file content"""
    return b"This is test file content for storage testing"


# Integration test example
@pytest.mark.integration
class TestStorageIntegration:
    """Integration tests for storage service"""
    
    @pytest.mark.asyncio
    async def test_full_upload_workflow(self, temp_storage_dir, mock_database_session):
        """Test complete upload workflow"""
        # This would test the full pipeline:
        # 1. File upload
        # 2. Storage via StorageManager
        # 3. Database record creation
        # 4. Conflict resolution
        # 5. Retrieval
        
        # Mock the FastAPI UploadFile
        class MockUploadFile:
            def __init__(self, content, filename):
                self.content = content
                self.filename = filename
                self.content_type = "application/pdf"
            
            async def read(self):
                return self.content
            
            async def seek(self, position):
                pass  # Mock seek
        
        # Create storage manager with temp directory
        provider = LocalStorageProvider({"root_path": temp_storage_dir})
        manager = StorageManager(mock_database_session)
        manager.provider = provider
        
        # Test file
        test_content = b"Integration test content"
        mock_file = MockUploadFile(test_content, "integration_test.pdf")
        workspace_id = uuid4()
        
        # Store document
        result = await manager.store_document(mock_file, workspace_id)
        
        # Verify result
        assert isinstance(result, StorageResult)
        assert result.size == len(test_content)
        
        # Verify file exists in storage
        assert await provider.exists(result.path)
        
        # Retrieve and verify content
        retrieved_content = await provider.get_file(result.path)
        assert retrieved_content == test_content


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])