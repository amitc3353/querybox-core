"""
Verification Service Package

This package contains the Chain-of-Verification implementation for hallucination detection.
"""

from app.services.verification.verification_service import (
    VerificationService,
    get_verification_service
)
from app.services.verification.quote_matching_service import QuoteMatchingService
from app.services.verification.hallucination_detector import HallucinationDetector
from app.services.verification.verification_question_generator import VerificationQuestionGenerator

__all__ = [
    "VerificationService",
    "get_verification_service",
    "QuoteMatchingService",
    "HallucinationDetector",
    "VerificationQuestionGenerator",
]
