"""
Unit Tests for Task Queue Abstraction
Tests the queue abstraction layer without requiring actual Celery/Redis
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.queue.base import TaskQueue, TaskResult, TaskStatus
from app.queue import get_task_queue, reset_task_queue


class TestTaskQueueAbstraction:
    """Test task queue abstraction interface"""

    def setup_method(self):
        """Reset queue between tests"""
        reset_task_queue()

    def test_task_status_enum(self):
        """Test TaskStatus enum values"""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.SUCCESS == "success"
        assert TaskStatus.FAILURE == "failure"
        assert TaskStatus.CANCELLED == "cancelled"

    def test_task_result_creation(self):
        """Test TaskResult dataclass"""
        result = TaskResult(
            task_id="test-123",
            status=TaskStatus.SUCCESS,
            result={"data": "test"},
            progress=100.0
        )

        assert result.task_id == "test-123"
        assert result.status == TaskStatus.SUCCESS
        assert result.result == {"data": "test"}
        assert result.progress == 100.0
        assert result.error is None
        assert result.retry_count == 0

    def test_task_result_with_error(self):
        """Test TaskResult with error"""
        result = TaskResult(
            task_id="test-456",
            status=TaskStatus.FAILURE,
            error="Test error message",
            retry_count=2
        )

        assert result.status == TaskStatus.FAILURE
        assert result.error == "Test error message"
        assert result.retry_count == 2


class TestCeleryBackend:
    """Test Celery backend implementation"""

    def setup_method(self):
        """Reset queue between tests"""
        reset_task_queue()

    @patch('celery.result.AsyncResult')
    @patch('app.celery_app.celery_app')
    def test_celery_backend_initialization(self, mock_celery_app, mock_async_result):
        """Test Celery backend can be initialized"""
        from app.queue.celery_backend import CeleryTaskQueue

        queue = CeleryTaskQueue()
        assert queue.app == mock_celery_app

    @patch('celery.result.AsyncResult')
    @patch('app.celery_app.celery_app')
    def test_enqueue_task(self, mock_celery_app, mock_async_result):
        """Test enqueueing a task"""
        from app.queue.celery_backend import CeleryTaskQueue

        # Mock Celery task result
        mock_task = Mock()
        mock_task.id = "test-task-id-123"
        mock_celery_app.send_task.return_value = mock_task

        queue = CeleryTaskQueue()
        task_id = queue.enqueue_task(
            task_name="test_task",
            kwargs={"arg1": "value1"},
            queue="test_queue",
            priority=5
        )

        assert task_id == "test-task-id-123"
        mock_celery_app.send_task.assert_called_once()

        # Verify call arguments
        call_args = mock_celery_app.send_task.call_args
        assert call_args[0][0] == "app.tasks.metadata_tasks.test_task"
        assert call_args[1]["kwargs"] == {"arg1": "value1"}
        assert call_args[1]["queue"] == "test_queue"
        assert call_args[1]["priority"] == 5

    @patch('celery.result.AsyncResult')
    @patch('app.celery_app.celery_app')
    def test_get_task_status_success(self, mock_celery_app, mock_async_result_class):
        """Test getting task status for successful task"""
        from app.queue.celery_backend import CeleryTaskQueue

        # Mock successful task result
        mock_result = Mock()
        mock_result.state = "SUCCESS"
        mock_result.result = {"data": "completed"}
        mock_result.info = {"progress": 100.0}
        mock_async_result_class.return_value = mock_result

        queue = CeleryTaskQueue()
        status = queue.get_task_status("test-task-123")

        assert status.task_id == "test-task-123"
        assert status.status == TaskStatus.SUCCESS
        assert status.result == {"data": "completed"}
        assert status.progress == 100.0

    @patch('celery.result.AsyncResult')
    @patch('app.celery_app.celery_app')
    def test_get_task_status_failure(self, mock_celery_app, mock_async_result_class):
        """Test getting task status for failed task"""
        from app.queue.celery_backend import CeleryTaskQueue

        # Mock failed task result
        mock_result = Mock()
        mock_result.state = "FAILURE"
        mock_result.info = "Task failed with error"
        mock_async_result_class.return_value = mock_result

        queue = CeleryTaskQueue()
        status = queue.get_task_status("test-task-456")

        assert status.task_id == "test-task-456"
        assert status.status == TaskStatus.FAILURE
        assert status.error == "Task failed with error"

    @patch('celery.result.AsyncResult')
    @patch('app.celery_app.celery_app')
    def test_cancel_task(self, mock_celery_app, mock_async_result):
        """Test cancelling a task"""
        from app.queue.celery_backend import CeleryTaskQueue

        mock_control = Mock()
        mock_celery_app.control = mock_control

        queue = CeleryTaskQueue()
        result = queue.cancel_task("test-task-789", terminate=True)

        assert result is True
        mock_control.revoke.assert_called_once_with(
            "test-task-789",
            terminate=True,
            signal='SIGTERM'
        )

    @patch('celery.result.AsyncResult')
    @patch('app.celery_app.celery_app')
    def test_get_queue_info(self, mock_celery_app, mock_async_result):
        """Test getting queue information"""
        from app.queue.celery_backend import CeleryTaskQueue

        # Mock inspect results
        mock_inspect = Mock()
        mock_inspect.active.return_value = {
            "worker1": [{"id": "task1"}],
            "worker2": [{"id": "task2"}, {"id": "task3"}]
        }
        mock_inspect.scheduled.return_value = {"worker1": [{"id": "task4"}]}
        mock_inspect.reserved.return_value = {"worker2": [{"id": "task5"}]}

        mock_control = Mock()
        mock_control.inspect.return_value = mock_inspect
        mock_celery_app.control = mock_control

        queue = CeleryTaskQueue()
        info = queue.get_queue_info("test_queue")

        assert info["backend"] == "celery"
        assert info["active_tasks"] == 3
        assert info["scheduled_tasks"] == 1
        assert info["reserved_tasks"] == 1
        assert info["total_pending"] == 5
        assert info["workers"] == 2


class TestQueueFactory:
    """Test queue factory function"""

    def setup_method(self):
        """Reset queue between tests"""
        reset_task_queue()

    @patch('celery.result.AsyncResult')
    @patch('app.celery_app.celery_app')
    @patch('app.core.config.settings')
    def test_get_celery_queue(self, mock_settings, mock_celery_app, mock_async_result):
        """Test getting Celery queue from factory"""
        mock_settings.TASK_QUEUE_BACKEND = "celery"

        queue = get_task_queue()

        assert queue is not None
        assert hasattr(queue, 'enqueue_task')
        assert hasattr(queue, 'get_task_status')
        assert hasattr(queue, 'cancel_task')

    @patch('app.core.config.settings')
    def test_get_kafka_queue_not_implemented(self, mock_settings):
        """Test that Kafka queue raises NotImplementedError"""
        mock_settings.TASK_QUEUE_BACKEND = "kafka"

        with pytest.raises(NotImplementedError, match="Kafka backend not yet implemented"):
            get_task_queue()

    @patch('app.core.config.settings')
    def test_invalid_backend_raises_error(self, mock_settings):
        """Test that invalid backend raises ValueError"""
        mock_settings.TASK_QUEUE_BACKEND = "invalid_backend"

        with pytest.raises(ValueError, match="Unknown task queue backend"):
            get_task_queue()

    @patch('celery.result.AsyncResult')
    @patch('app.celery_app.celery_app')
    @patch('app.core.config.settings')
    def test_queue_singleton(self, mock_settings, mock_celery_app, mock_async_result):
        """Test that get_task_queue returns same instance"""
        mock_settings.TASK_QUEUE_BACKEND = "celery"

        queue1 = get_task_queue()
        queue2 = get_task_queue()

        assert queue1 is queue2  # Same instance

    @patch('celery.result.AsyncResult')
    @patch('app.celery_app.celery_app')
    @patch('app.core.config.settings')
    def test_reset_task_queue(self, mock_settings, mock_celery_app, mock_async_result):
        """Test resetting queue singleton"""
        mock_settings.TASK_QUEUE_BACKEND = "celery"

        queue1 = get_task_queue()
        reset_task_queue()
        queue2 = get_task_queue()

        # After reset, should be different instances
        assert queue1 is not queue2
