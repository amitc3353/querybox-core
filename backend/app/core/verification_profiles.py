"""
Verification Profiles for Configurable Verification Levels

Provides 5 preset verification levels (VERY_HIGH, HIGH, MEDIUM, LOW, VERY_LOW)
that control the strictness of the entire verification pipeline through a single setting.

Philosophy:
- VERY_HIGH: Maximum strictness for legal/medical domains (>98% accuracy)
- HIGH: Current production behavior (>95% accuracy) - DEFAULT
- MEDIUM: Balanced for internal tools (>90% accuracy)
- LOW: Lenient for exploratory queries (>85% accuracy)
- VERY_LOW: Minimal verification for speed-critical apps (>80% accuracy)

Usage:
    from app.core.verification_profiles import get_active_profile

    profile = get_active_profile()
    threshold = profile.quote_similarity_threshold
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class VerificationLevel(str, Enum):
    """
    Verification strictness levels.

    Controls all verification parameters through a single setting.
    """
    VERY_HIGH = "VERY_HIGH"  # Maximum strictness
    HIGH = "HIGH"            # Current production (default)
    MEDIUM = "MEDIUM"        # Balanced
    LOW = "LOW"              # Lenient
    VERY_LOW = "VERY_LOW"    # Minimal verification


@dataclass(frozen=True)
class VerificationProfile:
    """
    Complete verification configuration profile.

    All verification parameters bundled into a single profile
    for consistent behavior across the pipeline.
    """
    # Profile metadata
    level: VerificationLevel
    description: str

    # Quote Matching Configuration
    quote_similarity_threshold: float  # 0.55-0.92: Fuzzy match threshold
    quote_max_matches_per_proposition: int  # Top-k matches to store

    # Hallucination Detection Weights
    hallucination_quote_coverage_weight: float  # 0.5 default
    hallucination_verification_agreement_weight: float  # 0.3 default
    hallucination_semantic_contradiction_weight: float  # 0.2 default

    # Hallucination Thresholds
    hallucination_flag_threshold: float  # 0.3 default: Flag for review
    hallucination_auto_remove_threshold: float  # 0.5-1.0: Auto-remove claims

    # Confidence Calculation Weights (keeping consistent across levels for MVP)
    confidence_passage_relevance_weight: float  # 0.40 default
    confidence_quote_quality_weight: float  # 0.35 default
    confidence_verification_agreement_weight: float  # 0.15 default
    confidence_citation_count_weight: float  # 0.10 default

    # Abstention Thresholds
    low_confidence_threshold: float  # 0.15-0.40: Abstain if below
    high_hallucination_threshold: float  # 0.60-0.95: Abstain if above

    # LLM Parameters
    verification_temperature: float  # 0.05-0.30: LLM creativity

    # Behavioral Flags
    enable_contradiction_check: bool  # LLM-based contradiction detection
    strict_mode: bool  # True: remove on suspicion, False: flag only

    def __post_init__(self):
        """Validate profile parameters are within acceptable ranges."""
        # Validate quote similarity threshold
        if not 0.0 <= self.quote_similarity_threshold <= 1.0:
            raise ValueError(
                f"quote_similarity_threshold must be in [0,1], got {self.quote_similarity_threshold}"
            )

        # Validate hallucination weights sum to 1.0
        weight_sum = (
            self.hallucination_quote_coverage_weight +
            self.hallucination_verification_agreement_weight +
            self.hallucination_semantic_contradiction_weight
        )
        if abs(weight_sum - 1.0) > 0.01:
            raise ValueError(
                f"Hallucination weights must sum to 1.0, got {weight_sum}"
            )

        # Validate confidence weights sum to 1.0
        conf_weight_sum = (
            self.confidence_passage_relevance_weight +
            self.confidence_quote_quality_weight +
            self.confidence_verification_agreement_weight +
            self.confidence_citation_count_weight
        )
        if abs(conf_weight_sum - 1.0) > 0.01:
            raise ValueError(
                f"Confidence weights must sum to 1.0, got {conf_weight_sum}"
            )

        # Validate thresholds
        if not 0.0 <= self.hallucination_flag_threshold <= 1.0:
            raise ValueError("hallucination_flag_threshold must be in [0,1]")
        if not 0.0 <= self.hallucination_auto_remove_threshold <= 1.0:
            raise ValueError("hallucination_auto_remove_threshold must be in [0,1]")
        if not 0.0 <= self.low_confidence_threshold <= 1.0:
            raise ValueError("low_confidence_threshold must be in [0,1]")
        if not 0.0 <= self.high_hallucination_threshold <= 1.0:
            raise ValueError("high_hallucination_threshold must be in [0,1]")
        if not 0.0 <= self.verification_temperature <= 1.0:
            raise ValueError("verification_temperature must be in [0,1]")


# =============================================================================
# PRESET PROFILES
# =============================================================================

VERY_HIGH_PROFILE = VerificationProfile(
    level=VerificationLevel.VERY_HIGH,
    description="Maximum strictness for legal/medical domains - >98% accuracy, highest abstention rate",

    # Quote Matching: Near-exact matches only
    quote_similarity_threshold=0.92,
    quote_max_matches_per_proposition=5,

    # Hallucination Detection: Keep default weights
    hallucination_quote_coverage_weight=0.5,
    hallucination_verification_agreement_weight=0.3,
    hallucination_semantic_contradiction_weight=0.2,

    # Thresholds: Very aggressive removal
    hallucination_flag_threshold=0.25,  # Flag early
    hallucination_auto_remove_threshold=0.50,  # Remove on moderate suspicion

    # Confidence Weights: Keep standard
    confidence_passage_relevance_weight=0.40,
    confidence_quote_quality_weight=0.35,
    confidence_verification_agreement_weight=0.15,
    confidence_citation_count_weight=0.10,

    # Abstention: High bar for answering
    low_confidence_threshold=0.40,  # Abstain if confidence < 0.40
    high_hallucination_threshold=0.60,  # Abstain if hallucination > 0.60

    # LLM: Very deterministic
    verification_temperature=0.05,

    # Behavior: Strict mode with all checks
    enable_contradiction_check=True,
    strict_mode=True
)

HIGH_PROFILE = VerificationProfile(
    level=VerificationLevel.HIGH,
    description="Current production behavior (DEFAULT) - >95% accuracy, balanced performance",

    # Quote Matching: Current production values
    quote_similarity_threshold=0.85,
    quote_max_matches_per_proposition=5,

    # Hallucination Detection: Current weights
    hallucination_quote_coverage_weight=0.5,
    hallucination_verification_agreement_weight=0.3,
    hallucination_semantic_contradiction_weight=0.2,

    # Thresholds: Current production values
    hallucination_flag_threshold=0.30,
    hallucination_auto_remove_threshold=0.70,

    # Confidence Weights: Current production values
    confidence_passage_relevance_weight=0.40,
    confidence_quote_quality_weight=0.35,
    confidence_verification_agreement_weight=0.15,
    confidence_citation_count_weight=0.10,

    # Abstention: Current production values
    low_confidence_threshold=0.30,
    high_hallucination_threshold=0.70,

    # LLM: Current production temperature
    verification_temperature=0.10,

    # Behavior: Strict mode enabled
    enable_contradiction_check=True,
    strict_mode=True
)

MEDIUM_PROFILE = VerificationProfile(
    level=VerificationLevel.MEDIUM,
    description="Balanced for internal tools - >90% accuracy, moderate strictness",

    # Quote Matching: Allow paraphrasing
    quote_similarity_threshold=0.75,
    quote_max_matches_per_proposition=5,

    # Hallucination Detection: Keep standard weights
    hallucination_quote_coverage_weight=0.5,
    hallucination_verification_agreement_weight=0.3,
    hallucination_semantic_contradiction_weight=0.2,

    # Thresholds: More conservative removal
    hallucination_flag_threshold=0.35,
    hallucination_auto_remove_threshold=0.80,

    # Confidence Weights: Keep standard
    confidence_passage_relevance_weight=0.40,
    confidence_quote_quality_weight=0.35,
    confidence_verification_agreement_weight=0.15,
    confidence_citation_count_weight=0.10,

    # Abstention: More lenient
    low_confidence_threshold=0.25,
    high_hallucination_threshold=0.75,

    # LLM: Slightly more creative
    verification_temperature=0.15,

    # Behavior: Flag-only mode, keep contradiction check
    enable_contradiction_check=True,
    strict_mode=False  # Flag only, don't auto-remove
)

LOW_PROFILE = VerificationProfile(
    level=VerificationLevel.LOW,
    description="Lenient for exploratory queries - >85% accuracy, low abstention rate",

    # Quote Matching: Accept loose matches
    quote_similarity_threshold=0.65,
    quote_max_matches_per_proposition=5,

    # Hallucination Detection: Keep standard weights
    hallucination_quote_coverage_weight=0.5,
    hallucination_verification_agreement_weight=0.3,
    hallucination_semantic_contradiction_weight=0.2,

    # Thresholds: Rarely remove
    hallucination_flag_threshold=0.40,
    hallucination_auto_remove_threshold=0.90,

    # Confidence Weights: Keep standard
    confidence_passage_relevance_weight=0.40,
    confidence_quote_quality_weight=0.35,
    confidence_verification_agreement_weight=0.15,
    confidence_citation_count_weight=0.10,

    # Abstention: Answer more often
    low_confidence_threshold=0.20,
    high_hallucination_threshold=0.85,

    # LLM: More creative
    verification_temperature=0.20,

    # Behavior: Disable expensive contradiction check
    enable_contradiction_check=False,
    strict_mode=False
)

VERY_LOW_PROFILE = VerificationProfile(
    level=VerificationLevel.VERY_LOW,
    description="Minimal verification for speed-critical apps - >80% accuracy, almost never abstains",

    # Quote Matching: Very loose
    quote_similarity_threshold=0.55,
    quote_max_matches_per_proposition=3,  # Fewer matches for speed

    # Hallucination Detection: Keep standard weights
    hallucination_quote_coverage_weight=0.5,
    hallucination_verification_agreement_weight=0.3,
    hallucination_semantic_contradiction_weight=0.2,

    # Thresholds: Never auto-remove
    hallucination_flag_threshold=0.50,
    hallucination_auto_remove_threshold=1.00,  # Never remove (warnings only)

    # Confidence Weights: Keep standard
    confidence_passage_relevance_weight=0.40,
    confidence_quote_quality_weight=0.35,
    confidence_verification_agreement_weight=0.15,
    confidence_citation_count_weight=0.10,

    # Abstention: Almost always answer
    low_confidence_threshold=0.15,
    high_hallucination_threshold=0.95,

    # LLM: Most creative
    verification_temperature=0.30,

    # Behavior: Minimal verification
    enable_contradiction_check=False,
    strict_mode=False
)

# Profile registry
VERIFICATION_PROFILES: dict[VerificationLevel, VerificationProfile] = {
    VerificationLevel.VERY_HIGH: VERY_HIGH_PROFILE,
    VerificationLevel.HIGH: HIGH_PROFILE,
    VerificationLevel.MEDIUM: MEDIUM_PROFILE,
    VerificationLevel.LOW: LOW_PROFILE,
    VerificationLevel.VERY_LOW: VERY_LOW_PROFILE,
}


# =============================================================================
# PROFILE LOADING
# =============================================================================

_active_profile: Optional[VerificationProfile] = None


def get_active_profile() -> VerificationProfile:
    """
    Get the currently active verification profile.

    Loads profile based on VERIFICATION_LEVEL env var (defaults to HIGH).
    Profile is cached for performance.

    Returns:
        VerificationProfile: Active profile configuration

    Raises:
        ValueError: If VERIFICATION_LEVEL is invalid

    Example:
        >>> profile = get_active_profile()
        >>> threshold = profile.quote_similarity_threshold
        >>> print(f"Using {profile.level} verification")
    """
    global _active_profile

    import os

    # Return cached profile if already loaded
    if _active_profile is not None:
        return _active_profile

    # Load directly from environment variable (supports test mocking)
    level_str = os.environ.get("VERIFICATION_LEVEL", "HIGH")

    try:
        level = VerificationLevel(level_str)
    except ValueError:
        logger.error(
            "Invalid VERIFICATION_LEVEL in environment",
            level=level_str,
            valid_levels=[l.value for l in VerificationLevel]
        )
        raise ValueError(
            f"Invalid VERIFICATION_LEVEL: {level_str}. "
            f"Must be one of: {[l.value for l in VerificationLevel]}"
        )

    _active_profile = VERIFICATION_PROFILES[level]

    logger.info(
        "Loaded verification profile",
        level=_active_profile.level.value,
        description=_active_profile.description,
        quote_threshold=_active_profile.quote_similarity_threshold,
        auto_remove_threshold=_active_profile.hallucination_auto_remove_threshold,
    )

    return _active_profile


def reload_profile() -> VerificationProfile:
    """
    Force reload of verification profile from settings.

    Useful for testing or when settings change at runtime.

    Returns:
        VerificationProfile: Newly loaded profile
    """
    global _active_profile
    _active_profile = None
    return get_active_profile()


def get_profile_summary() -> dict:
    """
    Get human-readable summary of active profile.

    Returns:
        dict: Profile summary with key parameters

    Example:
        >>> summary = get_profile_summary()
        >>> print(f"Level: {summary['level']}")
        >>> print(f"Quote threshold: {summary['quote_similarity_threshold']}")
    """
    profile = get_active_profile()

    return {
        "level": profile.level.value,
        "description": profile.description,
        "quote_similarity_threshold": profile.quote_similarity_threshold,
        "hallucination_auto_remove_threshold": profile.hallucination_auto_remove_threshold,
        "low_confidence_threshold": profile.low_confidence_threshold,
        "high_hallucination_threshold": profile.high_hallucination_threshold,
        "verification_temperature": profile.verification_temperature,
        "enable_contradiction_check": profile.enable_contradiction_check,
        "strict_mode": profile.strict_mode,
    }
