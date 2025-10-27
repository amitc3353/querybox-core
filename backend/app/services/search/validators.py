"""
Vector Search Validators for Step 9.3

Validates vector search readiness including embeddings, indexes, and dimensions.
"""
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, text
import structlog

from app.models.embedding import Embedding
from app.models.document import Document
from app.core.config import settings

logger = structlog.get_logger()


class VectorSearchValidator:
    """
    Validates vector search readiness

    Checks:
    - Embeddings exist in database
    - Vector indexes are present
    - Embedding dimensions are correct
    - pgvector extension is installed
    """

    def __init__(self, db: Session):
        """Initialize validator with database session"""
        self.db = db

    def validate_embeddings_exist(self) -> Dict:
        """
        Check if embeddings exist in database

        Returns:
            Dict with embedding validation results including:
            - total_chunks: Total number of chunks
            - chunks_with_embeddings: Chunks that have embeddings
            - embedding_coverage: Percentage of chunks with embeddings
            - is_valid: Whether coverage is sufficient for search
            - issues: List of issues found
            - recommendations: List of recommendations
        """
        try:
            # Rollback any failed transaction first
            try:
                self.db.rollback()
            except:
                pass

            # Count total chunks
            total_chunks = self.db.query(func.count(Embedding.id)).scalar() or 0

            # Count chunks with embeddings
            chunks_with_embeddings = self.db.query(func.count(Embedding.id)).filter(
                Embedding.embedding.isnot(None)
            ).scalar() or 0

            # Calculate coverage
            coverage_percentage = (chunks_with_embeddings / total_chunks * 100) if total_chunks > 0 else 0.0

            # Validate
            issues = []
            recommendations = []
            is_valid = False

            if total_chunks == 0:
                issues.append("No chunks found in database")
                recommendations.append("Run document chunking (Step 9.1) to create chunks")
            elif chunks_with_embeddings == 0:
                issues.append("No embeddings found - all embeddings are NULL")
                recommendations.append("Run embedding generation (Step 9.2) to create embeddings")
            elif coverage_percentage < 80:
                issues.append(f"Low embedding coverage: {coverage_percentage:.1f}%")
                recommendations.append("Re-run embedding generation for documents with missing embeddings")
                is_valid = False
            else:
                is_valid = True
                recommendations.append("Embedding coverage is sufficient for vector search")

            logger.info(
                "embeddings_validation",
                total_chunks=total_chunks,
                chunks_with_embeddings=chunks_with_embeddings,
                coverage_percentage=coverage_percentage,
                is_valid=is_valid
            )

            return {
                "total_chunks": total_chunks,
                "chunks_with_embeddings": chunks_with_embeddings,
                "embedding_coverage": round(coverage_percentage, 2),
                "is_valid": is_valid,
                "issues": issues,
                "recommendations": recommendations
            }

        except Exception as e:
            logger.error(
                "embeddings_validation_failed",
                error=str(e),
                exc_info=True
            )
            return {
                "total_chunks": 0,
                "chunks_with_embeddings": 0,
                "embedding_coverage": 0.0,
                "is_valid": False,
                "issues": [f"Validation failed: {str(e)}"],
                "recommendations": ["Check database connection and embeddings table schema"]
            }

    def validate_vector_index_exists(self) -> Dict:
        """
        Check if vector index exists for performance

        Returns:
            Dict with index validation results including:
            - has_index: Whether vector index exists
            - index_type: Type of index (hnsw, ivfflat, or none)
            - index_name: Name of the index
            - index_size: Size of index in human-readable format
            - is_valid: Whether index exists
            - issues: List of issues found
            - recommendations: List of recommendations
        """
        try:
            # Rollback any failed transaction first
            try:
                self.db.rollback()
            except:
                pass

            # Query for vector indexes
            sql = text("""
                SELECT
                    indexname,
                    indexdef,
                    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
                FROM pg_indexes
                WHERE tablename = 'embeddings'
                  AND (indexdef LIKE '%hnsw%' OR indexdef LIKE '%ivfflat%')
            """)

            result = self.db.execute(sql).fetchall()

            issues = []
            recommendations = []
            has_index = False
            index_type = "none"
            index_name = None
            index_size = None

            if not result:
                issues.append("No vector index found on embeddings table")
                recommendations.append("Create HNSW or IVFFlat index for fast vector search")
                recommendations.append("Run: CREATE INDEX idx_embeddings_vector_hnsw ON embeddings USING hnsw (embedding vector_cosine_ops)")
            else:
                has_index = True
                index_info = result[0]
                index_name = index_info[0]
                index_def = index_info[1]
                index_size = index_info[2]

                # Determine index type
                if 'hnsw' in index_def.lower():
                    index_type = "hnsw"
                elif 'ivfflat' in index_def.lower():
                    index_type = "ivfflat"

                recommendations.append(f"Vector index found: {index_name} ({index_type}, {index_size})")
                recommendations.append("Vector search will use index for fast retrieval")

            logger.info(
                "vector_index_validation",
                has_index=has_index,
                index_type=index_type,
                index_name=index_name,
                index_size=index_size
            )

            return {
                "has_index": has_index,
                "index_type": index_type,
                "index_name": index_name,
                "index_size": index_size,
                "is_valid": has_index,
                "issues": issues,
                "recommendations": recommendations
            }

        except Exception as e:
            logger.error(
                "vector_index_validation_failed",
                error=str(e),
                exc_info=True
            )
            return {
                "has_index": False,
                "index_type": "none",
                "index_name": None,
                "index_size": None,
                "is_valid": False,
                "issues": [f"Index validation failed: {str(e)}"],
                "recommendations": ["Check pgvector extension is installed", "Verify database permissions"]
            }

    def validate_embedding_dimensions(self) -> Dict:
        """
        Validate embedding dimensions match configuration

        Returns:
            Dict with dimension validation results including:
            - expected_dimension: Expected dimension from config
            - actual_dimensions: Dict of model -> dimension mappings found
            - is_valid: Whether all dimensions match expected
            - issues: List of dimension mismatches
            - recommendations: List of recommendations
        """
        try:
            # Rollback any failed transaction first
            try:
                self.db.rollback()
            except:
                pass

            # Get expected dimension from config
            expected_dimension = settings.EMBEDDING_DIMENSION

            # Query for actual dimensions
            # Use vector_dims() function from pgvector or cast to array
            sql = text("""
                SELECT
                    embedding_model,
                    vector_dims(embedding) as dimension,
                    COUNT(*) as count
                FROM embeddings
                WHERE embedding IS NOT NULL
                GROUP BY embedding_model, vector_dims(embedding)
            """)

            results = self.db.execute(sql).fetchall()

            issues = []
            recommendations = []
            is_valid = True
            actual_dimensions = {}

            if not results:
                issues.append("No embeddings found to validate dimensions")
                recommendations.append("Generate embeddings first (Step 9.2)")
                is_valid = False
            else:
                for row in results:
                    model, dimension, count = row
                    actual_dimensions[model] = {
                        "dimension": dimension,
                        "count": count
                    }

                    # Check dimension match
                    if dimension != expected_dimension:
                        issues.append(
                            f"Dimension mismatch for {model}: found {dimension}, expected {expected_dimension}"
                        )
                        recommendations.append(
                            f"Re-generate embeddings for {model} with correct dimension"
                        )
                        is_valid = False

                if is_valid:
                    recommendations.append(
                        f"All embeddings have correct dimension ({expected_dimension})"
                    )

            logger.info(
                "embedding_dimensions_validation",
                expected_dimension=expected_dimension,
                actual_dimensions=actual_dimensions,
                is_valid=is_valid
            )

            return {
                "expected_dimension": expected_dimension,
                "actual_dimensions": actual_dimensions,
                "is_valid": is_valid,
                "issues": issues,
                "recommendations": recommendations
            }

        except Exception as e:
            logger.error(
                "embedding_dimensions_validation_failed",
                error=str(e),
                exc_info=True
            )
            return {
                "expected_dimension": settings.EMBEDDING_DIMENSION,
                "actual_dimensions": {},
                "is_valid": False,
                "issues": [f"Dimension validation failed: {str(e)}"],
                "recommendations": ["Check database schema and embeddings table"]
            }

    def validate_pgvector_extension(self) -> Dict:
        """
        Check if pgvector extension is installed

        Returns:
            Dict with pgvector validation results including:
            - is_installed: Whether pgvector is installed
            - version: pgvector version if available
            - is_valid: Whether extension is ready
            - issues: List of issues found
            - recommendations: List of recommendations
        """
        try:
            # Rollback any failed transaction first
            try:
                self.db.rollback()
            except:
                pass

            # Check if pgvector extension exists
            sql = text("""
                SELECT
                    extname,
                    extversion
                FROM pg_extension
                WHERE extname = 'vector'
            """)

            result = self.db.execute(sql).fetchone()

            issues = []
            recommendations = []
            is_installed = False
            version = None

            if not result:
                issues.append("pgvector extension not installed")
                recommendations.append("Install pgvector: CREATE EXTENSION vector;")
                recommendations.append("See: https://github.com/pgvector/pgvector")
            else:
                is_installed = True
                version = result[1] if len(result) > 1 else "unknown"
                recommendations.append(f"pgvector extension installed (version: {version})")

            logger.info(
                "pgvector_extension_validation",
                is_installed=is_installed,
                version=version
            )

            return {
                "is_installed": is_installed,
                "version": version,
                "is_valid": is_installed,
                "issues": issues,
                "recommendations": recommendations
            }

        except Exception as e:
            logger.error(
                "pgvector_extension_validation_failed",
                error=str(e),
                exc_info=True
            )
            return {
                "is_installed": False,
                "version": None,
                "is_valid": False,
                "issues": [f"pgvector validation failed: {str(e)}"],
                "recommendations": ["Check PostgreSQL connection and version (requires 11+)"]
            }

    def validate_all(self) -> Dict:
        """
        Run all vector search validations

        Returns:
            Dict with comprehensive validation results including:
            - is_ready: Whether vector search is ready to use
            - embeddings: Embeddings validation results
            - index: Index validation results
            - dimensions: Dimensions validation results
            - pgvector: pgvector extension validation results
            - overall_score: Overall readiness score (0.0-1.0)
            - issues: Combined list of all issues
            - recommendations: Combined list of all recommendations
        """
        # Run all validations
        embeddings_result = self.validate_embeddings_exist()
        index_result = self.validate_vector_index_exists()
        dimensions_result = self.validate_embedding_dimensions()
        pgvector_result = self.validate_pgvector_extension()

        # Calculate overall readiness
        validations = [
            embeddings_result["is_valid"],
            index_result["is_valid"],
            dimensions_result["is_valid"],
            pgvector_result["is_valid"]
        ]

        valid_count = sum(1 for v in validations if v)
        overall_score = valid_count / len(validations)
        is_ready = all(validations)

        # Combine issues and recommendations
        all_issues = (
            embeddings_result["issues"] +
            index_result["issues"] +
            dimensions_result["issues"] +
            pgvector_result["issues"]
        )

        all_recommendations = (
            embeddings_result["recommendations"] +
            index_result["recommendations"] +
            dimensions_result["recommendations"] +
            pgvector_result["recommendations"]
        )

        logger.info(
            "vector_search_validation_complete",
            is_ready=is_ready,
            overall_score=overall_score,
            issues_count=len(all_issues)
        )

        return {
            "is_ready": is_ready,
            "embeddings": embeddings_result,
            "index": index_result,
            "dimensions": dimensions_result,
            "pgvector": pgvector_result,
            "overall_score": round(overall_score, 2),
            "issues": all_issues,
            "recommendations": all_recommendations
        }


def get_vector_search_validator(db: Session) -> VectorSearchValidator:
    """
    Factory function to create VectorSearchValidator instance

    Args:
        db: Database session

    Returns:
        VectorSearchValidator instance
    """
    return VectorSearchValidator(db=db)
