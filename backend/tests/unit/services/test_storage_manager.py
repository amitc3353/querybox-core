"""
Unit Tests for Storage Manager Service
Tests StorageManager operations with mocked dependencies
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock, call
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta
from pathlib import Path
from io import BytesIO

from app.services.storage.manager import StorageManager
from app.services.storage.exceptions import (
    StorageException,
    FileNotFoundError,
    StorageQuotaExceeded,
    InvalidPathError
)
from app.schemas.storage import (
    StorageResult,
    StorageStats,
    ConflictStrategy,
    StorageProviderType
)
from app.models.document import Document, StorageProviderEnum, DocumentStatusEnum
from app.core.storage_config import storage_settings


class TestStorageManagerInitialization:
    """Test StorageManager initialization and provider factory"""

    def test_init_creates_manager(self):
        """Test StorageManager initializes correctly"""
        mock_db = Mock()
        manager = StorageManager(mock_db)

        assert manager.db == mock_db
        assert manager.path_generator is not None
        assert manager.provider is not None

    def test_provider_caching(self):
        """Test provider is cached and not recreated"""
        mock_db = Mock()
        manager = StorageManager(mock_db)

        provider1 = manager._get_provider()
        provider2 = manager._get_provider()

        assert provider1 is provider2  # Same instance

    @patch('app.services.storage.manager.storage_settings')
    def test_unsupported_provider_raises_error(self, mock_settings):
        """Test initialization fails for unsupported storage provider"""
        mock_db = Mock()
        mock_settings.STORAGE_PROVIDER = "unsupported_provider"

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            manager = StorageManager(mock_db)
            manager._get_provider()


class TestFilenameConflictResolution:
    """Test filename conflict resolution strategies"""

    @pytest.fixture
    def manager(self):
        """Create StorageManager with mocked dependencies"""
        mock_db = Mock()
        with patch('app.services.storage.manager.LocalStorageProvider'):
            manager = StorageManager(mock_db)
            return manager

    def test_no_conflict_returns_original(self, manager):
        """Test filename is returned as-is when no conflict exists"""
        filename = "report.pdf"
        existing_paths = []

        result = manager._resolve_filename_conflict(filename, existing_paths)

        assert result == filename

    def test_conflict_timestamp_strategy(self, manager):
        """Test timestamp strategy appends timestamp to filename"""
        filename = "report.pdf"
        existing_paths = [
            "workspace_id/2024/11/report.pdf"
        ]

        # Extract component should return the filename
        manager.path_generator.extract_components = Mock(
            return_value={'filename': 'report.pdf'}
        )

        result = manager._resolve_filename_conflict(
            filename,
            existing_paths,
            ConflictStrategy.TIMESTAMP
        )

        # Should have timestamp format: report_YYYYMMDD_HHMMSS.pdf
        assert result.startswith("report_")
        assert result.endswith(".pdf")
        assert "_" in result
        assert len(result) > len(filename)  # Has timestamp appended

    def test_conflict_counter_strategy(self, manager):
        """Test counter strategy appends incrementing number"""
        filename = "report.pdf"
        existing_paths = [
            "workspace_id/2024/11/report.pdf",
            "workspace_id/2024/11/report_1.pdf"
        ]

        # Mock extract_components to return filenames
        def mock_extract(path):
            components = path.split('/')
            return {'filename': components[-1]}

        manager.path_generator.extract_components = mock_extract

        result = manager._resolve_filename_conflict(
            filename,
            existing_paths,
            ConflictStrategy.COUNTER
        )

        assert result == "report_2.pdf"  # Next available counter

    def test_conflict_counter_strategy_first_conflict(self, manager):
        """Test counter strategy starts at 1 for first conflict"""
        filename = "report.pdf"
        existing_paths = ["workspace_id/2024/11/report.pdf"]

        manager.path_generator.extract_components = Mock(
            return_value={'filename': 'report.pdf'}
        )

        result = manager._resolve_filename_conflict(
            filename,
            existing_paths,
            ConflictStrategy.COUNTER
        )

        assert result == "report_1.pdf"

    def test_conflict_counter_safety_fallback(self, manager):
        """Test counter strategy falls back to UUID after 1000 iterations"""
        filename = "report.pdf"
        # Create 1001 existing files
        existing_paths = [f"workspace_id/2024/11/report_{i}.pdf" for i in range(1001)]
        existing_paths.insert(0, "workspace_id/2024/11/report.pdf")

        def mock_extract(path):
            components = path.split('/')
            return {'filename': components[-1]}

        manager.path_generator.extract_components = mock_extract

        result = manager._resolve_filename_conflict(
            filename,
            existing_paths,
            ConflictStrategy.COUNTER
        )

        # Should fall back to UUID strategy
        assert result != filename
        assert result.endswith("_report.pdf")  # UUID prefix format

    def test_conflict_uuid_strategy(self, manager):
        """Test UUID strategy prepends short UUID"""
        filename = "report.pdf"
        existing_paths = ["workspace_id/2024/11/report.pdf"]

        manager.path_generator.extract_components = Mock(
            return_value={'filename': 'report.pdf'}
        )

        result = manager._resolve_filename_conflict(
            filename,
            existing_paths,
            ConflictStrategy.UUID
        )

        # Should have format: 7f3e4a_report.pdf (6-char UUID prefix)
        assert result.endswith("_report.pdf")
        assert len(result) == len("7f3e4a_report.pdf")

    def test_filename_without_extension(self, manager):
        """Test conflict resolution for filename without extension"""
        filename = "readme"
        existing_paths = ["workspace_id/2024/11/readme"]

        manager.path_generator.extract_components = Mock(
            return_value={'filename': 'readme'}
        )

        result = manager._resolve_filename_conflict(
            filename,
            existing_paths,
            ConflictStrategy.COUNTER
        )

        assert result == "readme_1"  # No extension preserved


class TestChecksumCalculation:
    """Test checksum calculation"""

    @pytest.fixture
    def manager(self):
        mock_db = Mock()
        with patch('app.services.storage.manager.LocalStorageProvider'):
            return StorageManager(mock_db)

    @pytest.mark.asyncio
    async def test_calculate_checksum_returns_sha256(self, manager):
        """Test checksum calculation returns valid SHA256 hash"""
        content = b"Sample file content"
        checksum = await manager._calculate_checksum(content)

        # SHA256 hash is 64 hex characters
        assert len(checksum) == 64
        assert all(c in "0123456789abcdef" for c in checksum)

    @pytest.mark.asyncio
    async def test_calculate_checksum_consistent(self, manager):
        """Test same content produces same checksum"""
        content = b"Test content"

        checksum1 = await manager._calculate_checksum(content)
        checksum2 = await manager._calculate_checksum(content)

        assert checksum1 == checksum2

    @pytest.mark.asyncio
    async def test_calculate_checksum_different_content(self, manager):
        """Test different content produces different checksums"""
        checksum1 = await manager._calculate_checksum(b"Content A")
        checksum2 = await manager._calculate_checksum(b"Content B")

        assert checksum1 != checksum2


class TestQuotaManagement:
    """Test storage quota checking"""

    @pytest.fixture
    def manager(self):
        mock_db = Mock()
        with patch('app.services.storage.manager.LocalStorageProvider'):
            manager = StorageManager(mock_db)
            return manager

    @pytest.mark.asyncio
    async def test_check_quota_passes_when_under_limit(self, manager):
        """Test quota check passes when usage is under limit"""
        workspace_id = uuid4()

        # Mock get_storage_stats to return usage under limit
        mock_stats = StorageStats(
            workspace_id=workspace_id,
            used_bytes=100 * 1024 * 1024,  # 100 MB
            file_count=10,
            quota_bytes=storage_settings.DEFAULT_WORKSPACE_QUOTA_BYTES,
            quota_percentage=1.0,
            usage_by_type={},
            average_file_size=10.0
        )

        with patch.object(manager, 'get_storage_stats', return_value=mock_stats):
            # Should not raise exception
            await manager._check_quota(workspace_id, 10 * 1024 * 1024)  # 10 MB file

    @pytest.mark.asyncio
    async def test_check_quota_raises_when_exceeds_limit(self, manager):
        """Test quota check raises exception when quota would be exceeded"""
        workspace_id = uuid4()

        # Mock get_storage_stats to return usage near limit
        mock_stats = StorageStats(
            workspace_id=workspace_id,
            used_bytes=storage_settings.DEFAULT_WORKSPACE_QUOTA_BYTES - 1024,  # Almost at limit
            file_count=100,
            quota_bytes=storage_settings.DEFAULT_WORKSPACE_QUOTA_BYTES,
            quota_percentage=99.9,
            usage_by_type={},
            average_file_size=10.0
        )

        with patch.object(manager, 'get_storage_stats', return_value=mock_stats):
            with pytest.raises(StorageQuotaExceeded) as exc_info:
                await manager._check_quota(workspace_id, 10 * 1024 * 1024)  # 10 MB file

            assert workspace_id == UUID(exc_info.value.workspace_id)
            assert exc_info.value.quota_bytes == storage_settings.DEFAULT_WORKSPACE_QUOTA_BYTES


class TestStoreDocument:
    """Test document storage operations"""

    @pytest.fixture
    def manager(self):
        mock_db = Mock()
        with patch('app.services.storage.manager.LocalStorageProvider'):
            manager = StorageManager(mock_db)
            # Mock provider methods
            manager.provider.save_file = AsyncMock()
            manager.provider.get_url = AsyncMock(return_value="http://storage/file.pdf")
            manager.provider.delete_file = AsyncMock()
            return manager

    @pytest.fixture
    def mock_file(self):
        """Create mock UploadFile"""
        mock = AsyncMock()
        mock.filename = "test.pdf"
        mock.content_type = "application/pdf"
        mock.read = AsyncMock(return_value=b"PDF content")
        return mock

    @pytest.mark.asyncio
    async def test_store_document_success(self, manager, mock_file):
        """Test successful document storage"""
        workspace_id = uuid4()
        document_id = uuid4()

        # Mock dependencies
        manager._check_quota = AsyncMock()
        manager._log_operation = AsyncMock()
        manager.path_generator.generate_document_path = Mock(
            return_value=f"{workspace_id}/2024/11/{document_id}/test.pdf"
        )
        manager.path_generator.extract_components = Mock(
            return_value={
                'workspace_id': str(workspace_id),
                'year': '2024',
                'month': '11',
                'filename': 'test.pdf'
            }
        )

        # Mock database query for conflict checking
        manager.db.query.return_value.filter.return_value.all.return_value = []

        result = await manager.store_document(
            file=mock_file,
            workspace_id=workspace_id,
            document_id=document_id
        )

        # Assertions
        assert isinstance(result, StorageResult)
        assert result.document_id == document_id
        assert result.size == len(b"PDF content")
        assert result.mime_type == "application/pdf"
        assert result.checksum is not None
        assert len(result.checksum) == 64  # SHA256 hash
        assert result.operation_time_ms > 0

        # Verify provider.save_file was called
        manager.provider.save_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_document_generates_id_if_not_provided(self, manager, mock_file):
        """Test document storage generates UUID if not provided"""
        workspace_id = uuid4()

        # Mock dependencies
        manager._check_quota = AsyncMock()
        manager._log_operation = AsyncMock()
        manager.path_generator.generate_document_path = Mock(
            return_value=f"{workspace_id}/2024/11/some_id/test.pdf"
        )
        manager.path_generator.extract_components = Mock(
            return_value={
                'workspace_id': str(workspace_id),
                'year': '2024',
                'month': '11',
                'filename': 'test.pdf'
            }
        )
        manager.db.query.return_value.filter.return_value.all.return_value = []

        result = await manager.store_document(
            file=mock_file,
            workspace_id=workspace_id,
            document_id=None  # No ID provided
        )

        # Should generate a UUID
        assert result.document_id is not None
        assert isinstance(result.document_id, UUID)

    @pytest.mark.asyncio
    async def test_store_document_quota_exceeded(self, manager, mock_file):
        """Test storage fails when quota exceeded"""
        workspace_id = uuid4()

        # Mock quota check to raise exception
        manager._check_quota = AsyncMock(
            side_effect=StorageQuotaExceeded(
                used_bytes=1000000000,
                quota_bytes=500000000,
                workspace_id=str(workspace_id)
            )
        )

        with pytest.raises(StorageQuotaExceeded):
            await manager.store_document(
                file=mock_file,
                workspace_id=workspace_id
            )

    @pytest.mark.asyncio
    async def test_store_document_provider_failure_cleanup(self, manager, mock_file):
        """Test cleanup occurs when provider save fails"""
        workspace_id = uuid4()
        document_id = uuid4()

        # Mock dependencies
        manager._check_quota = AsyncMock()
        manager._log_operation = AsyncMock()
        manager.path_generator.generate_document_path = Mock(
            return_value=f"{workspace_id}/2024/11/{document_id}/test.pdf"
        )
        manager.path_generator.extract_components = Mock(
            return_value={
                'workspace_id': str(workspace_id),
                'year': '2024',
                'month': '11',
                'filename': 'test.pdf'
            }
        )
        manager.db.query.return_value.filter.return_value.all.return_value = []

        # Make save_file fail
        manager.provider.save_file.side_effect = Exception("Storage failure")

        with pytest.raises(StorageException, match="Failed to store document"):
            await manager.store_document(
                file=mock_file,
                workspace_id=workspace_id,
                document_id=document_id
            )

        # Verify cleanup was attempted
        manager.provider.delete_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_document_handles_filename_conflicts(self, manager, mock_file):
        """Test storage resolves filename conflicts"""
        workspace_id = uuid4()
        document_id = uuid4()

        # Mock dependencies
        manager._check_quota = AsyncMock()
        manager._log_operation = AsyncMock()
        manager.path_generator.generate_document_path = Mock(
            side_effect=[
                f"{workspace_id}/2024/11/{document_id}/test.pdf",  # Initial path
                f"{workspace_id}/2024/11/{document_id}/test_1.pdf"  # Resolved path
            ]
        )
        manager.path_generator.extract_components = Mock(
            return_value={
                'workspace_id': str(workspace_id),
                'year': '2024',
                'month': '11',
                'filename': 'test.pdf'
            }
        )

        # Mock existing document with same filename
        existing_doc = Mock(spec=Document)
        existing_doc.storage_path = f"{workspace_id}/2024/11/other_id/test.pdf"
        manager.db.query.return_value.filter.return_value.all.return_value = [existing_doc]

        result = await manager.store_document(
            file=mock_file,
            workspace_id=workspace_id,
            document_id=document_id
        )

        # Should successfully store with resolved filename
        assert result.document_id == document_id
        assert manager.provider.save_file.called


class TestRetrieveDocument:
    """Test document retrieval operations"""

    @pytest.fixture
    def manager(self):
        mock_db = Mock()
        with patch('app.services.storage.manager.LocalStorageProvider'):
            manager = StorageManager(mock_db)
            manager.provider.get_file = AsyncMock(return_value=b"Document content")
            return manager

    @pytest.mark.asyncio
    async def test_retrieve_document_success(self, manager):
        """Test successful document retrieval"""
        document_id = uuid4()

        # Mock database document
        mock_doc = Mock(spec=Document)
        mock_doc.id = document_id
        mock_doc.storage_path = "workspace/2024/11/test.pdf"
        mock_doc.deleted_at = None

        manager.db.query.return_value.filter_by.return_value.first.return_value = mock_doc
        manager._log_operation = AsyncMock()

        content = await manager.retrieve_document(document_id)

        assert content == b"Document content"
        manager.provider.get_file.assert_called_once_with(mock_doc.storage_path)

    @pytest.mark.asyncio
    async def test_retrieve_document_not_found_in_db(self, manager):
        """Test retrieval fails when document not in database"""
        document_id = uuid4()

        # Mock no document found
        manager.db.query.return_value.filter_by.return_value.first.return_value = None

        with pytest.raises(FileNotFoundError, match="not found in database"):
            await manager.retrieve_document(document_id)

    @pytest.mark.asyncio
    async def test_retrieve_document_deleted(self, manager):
        """Test retrieval fails for deleted documents"""
        document_id = uuid4()

        # Mock deleted document
        mock_doc = Mock(spec=Document)
        mock_doc.id = document_id
        mock_doc.deleted_at = datetime.now(timezone.utc)

        manager.db.query.return_value.filter_by.return_value.first.return_value = mock_doc

        with pytest.raises(FileNotFoundError, match="has been deleted"):
            await manager.retrieve_document(document_id)

    @pytest.mark.asyncio
    async def test_retrieve_document_provider_failure(self, manager):
        """Test retrieval handles provider errors"""
        document_id = uuid4()

        # Mock database document
        mock_doc = Mock(spec=Document)
        mock_doc.id = document_id
        mock_doc.storage_path = "workspace/2024/11/test.pdf"
        mock_doc.deleted_at = None

        manager.db.query.return_value.filter_by.return_value.first.return_value = mock_doc
        manager._log_operation = AsyncMock()

        # Make provider fail
        manager.provider.get_file.side_effect = Exception("Storage read error")

        with pytest.raises(StorageException, match="Failed to retrieve document"):
            await manager.retrieve_document(document_id)


class TestDeleteDocument:
    """Test document deletion operations"""

    @pytest.fixture
    def manager(self):
        mock_db = Mock()
        with patch('app.services.storage.manager.LocalStorageProvider'):
            manager = StorageManager(mock_db)
            manager.provider.delete_file = AsyncMock()
            return manager

    @pytest.mark.asyncio
    async def test_soft_delete_document(self, manager):
        """Test soft delete marks document as deleted"""
        document_id = uuid4()

        # Mock database document
        mock_doc = Mock(spec=Document)
        mock_doc.id = document_id
        mock_doc.storage_path = "workspace/2024/11/test.pdf"

        manager.db.query.return_value.filter_by.return_value.first.return_value = mock_doc
        manager._log_operation = AsyncMock()

        result = await manager.delete_document(document_id, soft_delete=True)

        assert result is True
        assert mock_doc.deleted_at is not None
        manager.db.commit.assert_called_once()
        # Provider delete should NOT be called for soft delete
        manager.provider.delete_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_hard_delete_document(self, manager):
        """Test hard delete removes document from storage and database"""
        document_id = uuid4()

        # Mock database document
        mock_doc = Mock(spec=Document)
        mock_doc.id = document_id
        mock_doc.storage_path = "workspace/2024/11/test.pdf"

        manager.db.query.return_value.filter_by.return_value.first.return_value = mock_doc
        manager._log_operation = AsyncMock()

        result = await manager.delete_document(document_id, soft_delete=False)

        assert result is True
        manager.provider.delete_file.assert_called_once_with(mock_doc.storage_path)
        manager.db.delete.assert_called_once_with(mock_doc)
        manager.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, manager):
        """Test delete returns False when document not found"""
        document_id = uuid4()

        # Mock no document found
        manager.db.query.return_value.filter_by.return_value.first.return_value = None

        result = await manager.delete_document(document_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_document_handles_errors(self, manager):
        """Test delete handles provider errors"""
        document_id = uuid4()

        # Mock database document
        mock_doc = Mock(spec=Document)
        mock_doc.id = document_id
        mock_doc.storage_path = "workspace/2024/11/test.pdf"

        manager.db.query.return_value.filter_by.return_value.first.return_value = mock_doc
        manager._log_operation = AsyncMock()

        # Make provider fail
        manager.provider.delete_file.side_effect = Exception("Storage delete error")

        with pytest.raises(StorageException, match="Failed to delete document"):
            await manager.delete_document(document_id, soft_delete=False)


class TestMoveToPermenant:
    """Test moving files from temporary to permanent storage"""

    @pytest.fixture
    def manager(self):
        mock_db = Mock()
        with patch('app.services.storage.manager.LocalStorageProvider'):
            manager = StorageManager(mock_db)
            manager.provider.move_file = AsyncMock()
            return manager

    @pytest.mark.asyncio
    async def test_move_to_permanent_success(self, manager):
        """Test successful move from temp to permanent storage"""
        temp_path = "temp/upload_12345.pdf"
        workspace_id = uuid4()
        document_id = uuid4()
        filename = "document.pdf"

        # Mock path generation
        permanent_path = f"{workspace_id}/2024/11/{document_id}/document.pdf"
        manager.path_generator.generate_document_path = Mock(return_value=permanent_path)
        manager._log_operation = AsyncMock()

        result = await manager.move_to_permanent(
            temp_path=temp_path,
            document_id=document_id,
            workspace_id=workspace_id,
            filename=filename
        )

        assert result == permanent_path
        manager.provider.move_file.assert_called_once_with(temp_path, permanent_path)

    @pytest.mark.asyncio
    async def test_move_to_permanent_failure(self, manager):
        """Test move handles provider errors"""
        temp_path = "temp/upload_12345.pdf"
        workspace_id = uuid4()
        document_id = uuid4()
        filename = "document.pdf"

        # Mock path generation
        manager.path_generator.generate_document_path = Mock(
            return_value=f"{workspace_id}/2024/11/{document_id}/document.pdf"
        )
        manager._log_operation = AsyncMock()

        # Make provider fail
        manager.provider.move_file.side_effect = Exception("Move operation failed")

        with pytest.raises(StorageException, match="Failed to move to permanent storage"):
            await manager.move_to_permanent(
                temp_path=temp_path,
                document_id=document_id,
                workspace_id=workspace_id,
                filename=filename
            )


class TestGetStorageStats:
    """Test storage statistics calculation"""

    @pytest.fixture
    def manager(self):
        mock_db = Mock()
        with patch('app.services.storage.manager.LocalStorageProvider'):
            return StorageManager(mock_db)

    @pytest.mark.asyncio
    async def test_get_storage_stats_with_documents(self, manager):
        """Test storage stats calculation with existing documents"""
        workspace_id = uuid4()

        # Mock documents in database
        mock_docs = [
            Mock(
                file_size=1024 * 1024,  # 1 MB
                file_extension=".pdf",
                created_at=datetime.now(timezone.utc)
            ),
            Mock(
                file_size=2 * 1024 * 1024,  # 2 MB
                file_extension=".pdf",
                created_at=datetime.now(timezone.utc) - timedelta(days=1)
            ),
            Mock(
                file_size=500 * 1024,  # 500 KB
                file_extension=".docx",
                created_at=datetime.now(timezone.utc) - timedelta(days=2)
            ),
        ]

        manager.db.query.return_value.filter.return_value.all.return_value = mock_docs

        stats = await manager.get_storage_stats(workspace_id)

        assert isinstance(stats, StorageStats)
        assert stats.workspace_id == workspace_id
        assert stats.file_count == 3
        assert stats.used_bytes == (1024 * 1024) + (2 * 1024 * 1024) + (500 * 1024)
        assert stats.quota_bytes == storage_settings.DEFAULT_WORKSPACE_QUOTA_BYTES
        assert stats.quota_percentage > 0
        assert ".pdf" in stats.usage_by_type
        assert ".docx" in stats.usage_by_type
        assert stats.last_upload is not None
        assert stats.oldest_file is not None
        assert stats.average_file_size > 0

    @pytest.mark.asyncio
    async def test_get_storage_stats_empty_workspace(self, manager):
        """Test storage stats for workspace with no documents"""
        workspace_id = uuid4()

        # Mock no documents
        manager.db.query.return_value.filter.return_value.all.return_value = []

        stats = await manager.get_storage_stats(workspace_id)

        assert stats.workspace_id == workspace_id
        assert stats.file_count == 0
        assert stats.used_bytes == 0
        assert stats.quota_percentage == 0.0
        assert stats.usage_by_type == {}
        assert stats.average_file_size == 0.0

    @pytest.mark.asyncio
    async def test_get_storage_stats_handles_errors(self, manager):
        """Test storage stats handles database errors"""
        workspace_id = uuid4()

        # Make database query fail
        manager.db.query.side_effect = Exception("Database error")

        with pytest.raises(StorageException, match="Failed to get storage stats"):
            await manager.get_storage_stats(workspace_id)


class TestCleanupTempFiles:
    """Test temporary file cleanup"""

    @pytest.fixture
    def manager(self):
        mock_db = Mock()
        with patch('app.services.storage.manager.LocalStorageProvider'):
            manager = StorageManager(mock_db)
            manager.provider.list_files = AsyncMock()
            manager.provider.delete_file = AsyncMock()
            return manager

    @pytest.mark.asyncio
    async def test_cleanup_temp_files_success(self, manager):
        """Test successful cleanup of temporary files"""
        # Mock temp files
        temp_files = [
            "temp/upload_12345.pdf",
            "temp/upload_67890.docx",
            "temp/old_file.txt"
        ]
        manager.provider.list_files.return_value = temp_files

        deleted_count = await manager.cleanup_temp_files()

        assert deleted_count == 3
        assert manager.provider.delete_file.call_count == 3

    @pytest.mark.asyncio
    async def test_cleanup_temp_files_no_files(self, manager):
        """Test cleanup when no temp files exist"""
        manager.provider.list_files.return_value = []

        deleted_count = await manager.cleanup_temp_files()

        assert deleted_count == 0
        manager.provider.delete_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_temp_files_handles_individual_failures(self, manager):
        """Test cleanup continues even if individual deletes fail"""
        temp_files = [
            "temp/file1.pdf",
            "temp/file2.pdf",
            "temp/file3.pdf"
        ]
        manager.provider.list_files.return_value = temp_files

        # Make second delete fail
        manager.provider.delete_file.side_effect = [
            None,  # First succeeds
            Exception("Delete failed"),  # Second fails
            None  # Third succeeds
        ]

        deleted_count = await manager.cleanup_temp_files()

        # Should continue and count only successful deletions
        assert deleted_count == 2

    @pytest.mark.asyncio
    async def test_cleanup_temp_files_handles_list_failure(self, manager):
        """Test cleanup handles errors when listing fails"""
        manager.provider.list_files.side_effect = Exception("List operation failed")

        with pytest.raises(StorageException, match="Failed to cleanup temp files"):
            await manager.cleanup_temp_files()


class TestOperationLogging:
    """Test storage operation logging"""

    @pytest.fixture
    def manager(self):
        mock_db = Mock()
        with patch('app.services.storage.manager.LocalStorageProvider'):
            return StorageManager(mock_db)

    @pytest.mark.asyncio
    async def test_log_operation_success(self, manager):
        """Test successful operation logging"""
        workspace_id = uuid4()
        document_id = uuid4()

        # Should not raise exception
        await manager._log_operation(
            operation_type="store",
            path="workspace/2024/11/test.pdf",
            success=True,
            duration_ms=150.5,
            workspace_id=workspace_id,
            document_id=document_id,
            error_message=None
        )

        # Logging should complete without errors
        # Note: Currently logs to file only, not database

    @pytest.mark.asyncio
    async def test_log_operation_failure(self, manager):
        """Test logging for failed operations"""
        workspace_id = uuid4()
        document_id = uuid4()

        # Should not raise exception even for failed operations
        await manager._log_operation(
            operation_type="retrieve",
            path="workspace/2024/11/missing.pdf",
            success=False,
            duration_ms=50.0,
            workspace_id=workspace_id,
            document_id=document_id,
            error_message="File not found"
        )

        # Logging should complete without errors

    @pytest.mark.asyncio
    async def test_log_operation_handles_logging_errors(self, manager):
        """Test logging doesn't break even if logging itself fails"""
        workspace_id = uuid4()

        # Even if logging internals fail, it should be caught
        with patch('app.services.storage.manager.logger') as mock_logger:
            mock_logger.info.side_effect = Exception("Logging failure")

            # Should not raise exception
            await manager._log_operation(
                operation_type="store",
                path="test.pdf",
                success=True,
                duration_ms=100.0,
                workspace_id=workspace_id
            )

            # Error should be caught and logged
            mock_logger.error.assert_called()
