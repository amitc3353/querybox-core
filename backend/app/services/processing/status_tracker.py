"""
Processing Status Tracker
Step 6: Enhanced status tracking with progress monitoring

Provides granular status tracking for document processing stages with
real-time progress updates and comprehensive metadata storage.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.processing_status import (
    ProcessingStatus,
    ProcessingStageEnum,
    StageStatusEnum
)
from app.schemas.metadata import ProcessingMetadata
from app.db.database import get_db


logger = logging.getLogger(__name__)


class ProcessingStatusTracker:
    """
    Tracks processing status for documents with detailed progress monitoring.
    
    Provides atomic status updates with proper state validation and
    comprehensive metadata tracking.
    """
    
    # Valid state transitions for processing stages
    VALID_TRANSITIONS = {
        StageStatusEnum.NOT_STARTED: [
            StageStatusEnum.IN_PROGRESS,
            StageStatusEnum.SKIPPED
        ],
        StageStatusEnum.IN_PROGRESS: [
            StageStatusEnum.COMPLETED,
            StageStatusEnum.FAILED
        ],
        StageStatusEnum.COMPLETED: [],  # Terminal state
        StageStatusEnum.FAILED: [
            StageStatusEnum.IN_PROGRESS  # Allow retry
        ],
        StageStatusEnum.SKIPPED: []  # Terminal state
    }
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def update_status(
        self,
        document_id: UUID,
        stage: ProcessingStageEnum,
        status: StageStatusEnum,
        processing_metadata: Optional[ProcessingMetadata] = None,
        error_message: Optional[str] = None
    ) -> ProcessingStatus:
        """
        Update processing status for a document stage.
        
        Args:
            document_id: Document UUID
            stage: Processing stage
            status: New status
            processing_metadata: Additional processing metadata
            error_message: Error message if status is FAILED
            
        Returns:
            Updated ProcessingStatus record
            
        Raises:
            ValueError: If status transition is invalid
            IntegrityError: If database constraint violated
        """
        try:
            # Get existing status record or create new one
            existing_status = self.db.query(ProcessingStatus).filter(
                ProcessingStatus.document_id == document_id,
                ProcessingStatus.stage == stage
            ).first()
            
            # Validate status transition
            if existing_status:
                self._validate_status_transition(existing_status.status, status)
            
            current_time = datetime.now(timezone.utc)
            
            if existing_status:
                # Update existing record
                old_status = existing_status.status
                existing_status.status = status
                existing_status.updated_at = current_time

                # Set completed_at and duration_ms for terminal states (must set both or neither per constraint)
                if status in [StageStatusEnum.COMPLETED, StageStatusEnum.FAILED]:
                    existing_status.completed_at = current_time
                    if existing_status.started_at:
                        duration = (current_time - existing_status.started_at).total_seconds() * 1000
                        existing_status.duration_ms = int(duration)

                # Handle error information
                if status == StageStatusEnum.FAILED:
                    existing_status.error_message = error_message
                    existing_status.attempt_number = (existing_status.attempt_number or 0) + 1
                elif status == StageStatusEnum.COMPLETED:
                    existing_status.error_message = None  # Clear previous errors
                
                # Update processing metadata
                if processing_metadata:
                    existing_status.status_metadata = self._merge_processing_metadata(
                        existing_status.status_metadata or {},
                        processing_metadata.dict()
                    )
                
                record = existing_status
                
            else:
                # Create new record
                # Note: For terminal states, must set BOTH completed_at and duration_ms (or neither) per DB constraint
                is_terminal = status in [StageStatusEnum.COMPLETED, StageStatusEnum.FAILED, StageStatusEnum.SKIPPED]
                record = ProcessingStatus(
                    document_id=document_id,
                    stage=stage,
                    status=status,
                    started_at=current_time if status == StageStatusEnum.IN_PROGRESS else None,
                    completed_at=current_time if is_terminal else None,
                    duration_ms=0 if is_terminal else None,  # Set to 0 for immediate terminal states
                    error_message=error_message if status == StageStatusEnum.FAILED else None,
                    attempt_number=1 if status == StageStatusEnum.FAILED else 1,
                    status_metadata=processing_metadata.dict() if processing_metadata else {},
                    created_at=current_time,
                    updated_at=current_time
                )
                self.db.add(record)
            
            # Commit changes
            self.db.commit()
            self.db.refresh(record)
            
            logger.info(
                f"Updated status for document {document_id}, "
                f"stage {stage.value} -> {status.value}"
            )
            
            return record
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update status: {e}")
            raise
    
    async def update_progress(
        self,
        document_id: UUID,
        stage: ProcessingStageEnum,
        percentage: float,
        current_operation: Optional[str] = None,
        estimated_completion: Optional[datetime] = None
    ) -> None:
        """
        Update progress for an in-progress stage.
        
        Args:
            document_id: Document UUID
            stage: Processing stage
            percentage: Completion percentage (0.0-100.0)
            current_operation: Description of current operation
            estimated_completion: Estimated completion time
        """
        try:
            # Validate percentage
            percentage = max(0.0, min(100.0, percentage))
            
            # Get existing status record
            status_record = self.db.query(ProcessingStatus).filter(
                ProcessingStatus.document_id == document_id,
                ProcessingStatus.stage == stage
            ).first()
            
            if not status_record:
                logger.warning(
                    f"Cannot update progress - no status record for document {document_id}, stage {stage.value}"
                )
                return
            
            if status_record.status != StageStatusEnum.IN_PROGRESS:
                logger.warning(
                    f"Cannot update progress - stage {stage.value} is not in progress"
                )
                return
            
            # Update progress metadata
            progress_metadata = ProcessingMetadata(
                percentage_complete=percentage,
                current_operation=current_operation,
                estimated_completion=estimated_completion
            )
            
            # Merge with existing metadata
            current_metadata = status_record.status_metadata or {}
            updated_metadata = self._merge_processing_metadata(
                current_metadata,
                progress_metadata.dict(exclude_none=True)
            )
            
            status_record.status_metadata = updated_metadata
            status_record.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            
            logger.debug(
                f"Updated progress for document {document_id}, "
                f"stage {stage.value}: {percentage:.1f}%"
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update progress: {e}")
            raise
    
    async def get_overall_progress(self, document_id: UUID) -> Dict[str, Any]:
        """
        Get overall processing progress for a document.
        
        Args:
            document_id: Document UUID
            
        Returns:
            Dictionary with overall progress information
        """
        try:
            # Get all status records for document
            statuses = self.db.query(ProcessingStatus).filter(
                ProcessingStatus.document_id == document_id
            ).all()
            
            if not statuses:
                return {
                    "overall_progress": 0.0,
                    "current_stage": None,
                    "stages": {},
                    "estimated_completion": None
                }
            
            # Calculate overall progress
            total_stages = len(ProcessingStageEnum)
            completed_stages = sum(
                1 for status in statuses
                if status.status == StageStatusEnum.COMPLETED
            )
            
            # Find current active stage
            current_stage = None
            current_progress = 0.0
            
            for status in statuses:
                if status.status == StageStatusEnum.IN_PROGRESS:
                    current_stage = status.stage.value
                    metadata = status.status_metadata or {}
                    current_progress = metadata.get("percentage_complete", 0.0)
                    break
            
            # Calculate overall percentage
            if current_stage:
                stage_weight = 1.0 / total_stages
                overall_progress = (completed_stages * stage_weight + 
                                 (current_progress / 100.0) * stage_weight) * 100.0
            else:
                overall_progress = (completed_stages / total_stages) * 100.0
            
            # Prepare stage details
            stages = {}
            estimated_completion = None
            
            for status in statuses:
                stage_info = {
                    "status": status.status.value,
                    "started_at": status.started_at.isoformat() if status.started_at else None,
                    "completed_at": status.completed_at.isoformat() if status.completed_at else None,
                    "duration_ms": status.duration_ms,
                    "error_message": status.error_message,
                    "attempt_number": status.attempt_number,
                    "metadata": status.status_metadata or {}
                }

                stages[status.stage.value] = stage_info
                
                # Get estimated completion from active stage
                if status.status == StageStatusEnum.IN_PROGRESS:
                    metadata = status.status_metadata or {}
                    if "estimated_completion" in metadata:
                        estimated_completion = metadata["estimated_completion"]
            
            return {
                "overall_progress": round(overall_progress, 1),
                "current_stage": current_stage,
                "completed_stages": completed_stages,
                "total_stages": total_stages,
                "stages": stages,
                "estimated_completion": estimated_completion
            }
            
        except Exception as e:
            logger.error(f"Failed to get overall progress: {e}")
            return {
                "overall_progress": 0.0,
                "current_stage": None,
                "error": str(e)
            }
    
    async def mark_stage_completed(
        self,
        document_id: UUID,
        stage: ProcessingStageEnum,
        processing_metadata: Optional[ProcessingMetadata] = None
    ) -> ProcessingStatus:
        """
        Mark a processing stage as completed.
        
        Args:
            document_id: Document UUID
            stage: Processing stage
            processing_metadata: Final processing metadata
            
        Returns:
            Updated ProcessingStatus record
        """
        return await self.update_status(
            document_id=document_id,
            stage=stage,
            status=StageStatusEnum.COMPLETED,
            processing_metadata=processing_metadata
        )
    
    async def mark_stage_failed(
        self,
        document_id: UUID,
        stage: ProcessingStageEnum,
        error_message: str,
        processing_metadata: Optional[ProcessingMetadata] = None
    ) -> ProcessingStatus:
        """
        Mark a processing stage as failed.
        
        Args:
            document_id: Document UUID
            stage: Processing stage
            error_message: Error description
            processing_metadata: Processing metadata at time of failure
            
        Returns:
            Updated ProcessingStatus record
        """
        return await self.update_status(
            document_id=document_id,
            stage=stage,
            status=StageStatusEnum.FAILED,
            processing_metadata=processing_metadata,
            error_message=error_message
        )
    
    def _validate_status_transition(
        self,
        current_status: StageStatusEnum,
        new_status: StageStatusEnum
    ) -> None:
        """Validate that status transition is allowed"""
        allowed_transitions = self.VALID_TRANSITIONS.get(current_status, [])
        
        if new_status not in allowed_transitions and new_status != current_status:
            raise ValueError(
                f"Invalid status transition from {current_status.value} to {new_status.value}. "
                f"Allowed transitions: {[s.value for s in allowed_transitions]}"
            )
    
    def _merge_processing_metadata(
        self,
        existing: Dict[str, Any],
        new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge processing metadata, preserving important fields"""
        merged = existing.copy()
        merged.update(new)
        
        # Ensure datetime fields are properly serialized
        for key, value in merged.items():
            if isinstance(value, datetime):
                merged[key] = value.isoformat()
        
        return merged


# Dependency to get status tracker
def get_status_tracker(db: Session = None) -> ProcessingStatusTracker:
    """
    Get ProcessingStatusTracker instance.
    
    Args:
        db: Database session (if None, will get from dependency)
        
    Returns:
        ProcessingStatusTracker instance
    """
    if db is None:
        db = next(get_db())
    
    return ProcessingStatusTracker(db)