"""
Benchmark Script for Reranking Performance (Step 10.2 - Phase 5)

Tests reranking latency with:
- Different candidate counts (10, 50, 100, 200, 500)
- GPU vs CPU performance
- Individual stage performance (cross-encoder, deduplication, MMR)
- Full pipeline performance

Usage:
    python backend/scripts/benchmark_reranking.py
    python backend/scripts/benchmark_reranking.py --device cuda
    python backend/scripts/benchmark_reranking.py --iterations 10
    python backend/scripts/benchmark_reranking.py --output benchmark_results.json
"""

import time
import argparse
import json
import statistics
from typing import List, Dict
from uuid import uuid4
from datetime import datetime, timezone

# Add parent directory to path for imports
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.search.cross_encoder_service import CrossEncoderService
from app.services.search.mmr_ranker import MMRRanker
from app.services.search.deduplication_service import DeduplicationService
from app.services.search.reranking_pipeline import RerankingPipeline
from app.schemas.search import SearchResultItem


def generate_test_candidates(count: int) -> List[SearchResultItem]:
    """
    Generate test search result candidates

    Args:
        count: Number of candidates to generate

    Returns:
        List of SearchResultItem instances
    """
    doc_id = str(uuid4())
    candidates = []

    for i in range(count):
        candidate = SearchResultItem(
            document_id=doc_id,
            document_name=f"test_doc_{i}.pdf",
            relevance_score=0.9 - (i * 0.005),  # Gradually decreasing scores
            snippet=f"This is a test snippet for candidate {i}. " * 10,  # ~100 char snippet
            chunk_index=i,
            chunk_position=None,
            extraction_quality=0.95,
            document_type="application/pdf",
            created_at=datetime.now(timezone.utc)
        )
        candidates.append(candidate)

    return candidates


def benchmark_cross_encoder(
    cross_encoder: CrossEncoderService,
    candidate_counts: List[int],
    iterations: int = 5
) -> Dict:
    """
    Benchmark cross-encoder reranking performance

    Args:
        cross_encoder: CrossEncoderService instance
        candidate_counts: List of candidate counts to test
        iterations: Number of iterations per test

    Returns:
        Dict with benchmark results
    """
    print("\n=== Cross-Encoder Benchmarks ===")
    results = {}

    query = "What is machine learning and how does it work?"

    for count in candidate_counts:
        print(f"\nTesting with {count} candidates...")
        candidates = generate_test_candidates(count)

        latencies = []
        for i in range(iterations):
            start = time.time()
            reranked = cross_encoder.rerank(query, candidates, top_k=min(50, count))
            latency = (time.time() - start) * 1000
            latencies.append(latency)

            if i == 0:
                print(f"  Iteration 1: {latency:.2f}ms (warmup)")
            elif i == iterations - 1:
                print(f"  Iteration {iterations}: {latency:.2f}ms")

        results[f"{count}_candidates"] = {
            "count": count,
            "iterations": iterations,
            "mean_latency_ms": round(statistics.mean(latencies), 2),
            "median_latency_ms": round(statistics.median(latencies), 2),
            "min_latency_ms": round(min(latencies), 2),
            "max_latency_ms": round(max(latencies), 2),
            "stdev_latency_ms": round(statistics.stdev(latencies) if len(latencies) > 1 else 0, 2)
        }

        print(f"  Mean: {results[f'{count}_candidates']['mean_latency_ms']:.2f}ms")
        print(f"  Median: {results[f'{count}_candidates']['median_latency_ms']:.2f}ms")

    return results


def benchmark_deduplication(
    dedup_service: DeduplicationService,
    candidate_counts: List[int],
    iterations: int = 5
) -> Dict:
    """
    Benchmark deduplication performance

    Args:
        dedup_service: DeduplicationService instance
        candidate_counts: List of candidate counts to test
        iterations: Number of iterations per test

    Returns:
        Dict with benchmark results
    """
    print("\n=== Deduplication Benchmarks ===")
    results = {}

    for count in candidate_counts:
        print(f"\nTesting with {count} candidates...")
        candidates = generate_test_candidates(count)

        latencies = []
        dedup_rates = []

        for i in range(iterations):
            start = time.time()
            deduplicated = dedup_service.deduplicate(candidates)
            latency = (time.time() - start) * 1000
            latencies.append(latency)

            stats = dedup_service.calculate_deduplication_stats(candidates, deduplicated)
            dedup_rates.append(stats["deduplication_rate"])

            if i == 0:
                print(f"  Iteration 1: {latency:.2f}ms (warmup)")
            elif i == iterations - 1:
                print(f"  Iteration {iterations}: {latency:.2f}ms")

        results[f"{count}_candidates"] = {
            "count": count,
            "iterations": iterations,
            "mean_latency_ms": round(statistics.mean(latencies), 2),
            "median_latency_ms": round(statistics.median(latencies), 2),
            "min_latency_ms": round(min(latencies), 2),
            "max_latency_ms": round(max(latencies), 2),
            "stdev_latency_ms": round(statistics.stdev(latencies) if len(latencies) > 1 else 0, 2),
            "mean_dedup_rate": round(statistics.mean(dedup_rates), 4)
        }

        print(f"  Mean: {results[f'{count}_candidates']['mean_latency_ms']:.2f}ms")
        print(f"  Dedup Rate: {results[f'{count}_candidates']['mean_dedup_rate']:.2%}")

    return results


def benchmark_mmr(
    mmr_ranker: MMRRanker,
    candidate_counts: List[int],
    iterations: int = 5
) -> Dict:
    """
    Benchmark MMR reranking performance

    Args:
        mmr_ranker: MMRRanker instance
        candidate_counts: List of candidate counts to test
        iterations: Number of iterations per test

    Returns:
        Dict with benchmark results
    """
    print("\n=== MMR Benchmarks ===")
    results = {}

    for count in candidate_counts:
        print(f"\nTesting with {count} candidates...")
        candidates = generate_test_candidates(count)

        latencies = []
        diversity_scores = []

        for i in range(iterations):
            start = time.time()
            reranked = mmr_ranker.rerank_with_mmr(candidates, top_k=min(10, count))
            latency = (time.time() - start) * 1000
            latencies.append(latency)

            diversity = mmr_ranker.calculate_diversity_score(reranked)
            diversity_scores.append(diversity)

            if i == 0:
                print(f"  Iteration 1: {latency:.2f}ms (warmup)")
            elif i == iterations - 1:
                print(f"  Iteration {iterations}: {latency:.2f}ms")

        results[f"{count}_candidates"] = {
            "count": count,
            "iterations": iterations,
            "mean_latency_ms": round(statistics.mean(latencies), 2),
            "median_latency_ms": round(statistics.median(latencies), 2),
            "min_latency_ms": round(min(latencies), 2),
            "max_latency_ms": round(max(latencies), 2),
            "stdev_latency_ms": round(statistics.stdev(latencies) if len(latencies) > 1 else 0, 2),
            "mean_diversity_score": round(statistics.mean(diversity_scores), 4)
        }

        print(f"  Mean: {results[f'{count}_candidates']['mean_latency_ms']:.2f}ms")
        print(f"  Diversity: {results[f'{count}_candidates']['mean_diversity_score']:.4f}")

    return results


def benchmark_pipeline(
    pipeline: RerankingPipeline,
    candidate_counts: List[int],
    iterations: int = 5
) -> Dict:
    """
    Benchmark full reranking pipeline performance

    Args:
        pipeline: RerankingPipeline instance
        candidate_counts: List of candidate counts to test
        iterations: Number of iterations per test

    Returns:
        Dict with benchmark results
    """
    print("\n=== Full Pipeline Benchmarks ===")
    results = {}

    query = "What is machine learning and how does it work?"

    for count in candidate_counts:
        print(f"\nTesting with {count} candidates...")
        candidates = generate_test_candidates(count)

        latencies = []
        stage1_times = []
        stage2_times = []
        stage3_times = []

        for i in range(iterations):
            start = time.time()
            result = pipeline.process(
                query=query,
                candidates=candidates,
                final_top_k=10,
                rerank_top_k=min(50, count)
            )
            latency = (time.time() - start) * 1000
            latencies.append(latency)

            # Extract stage times
            stats = result["pipeline_stats"]
            stage1_times.append(stats.get("stage1_reranking", {}).get("processing_time_ms", 0))
            stage2_times.append(stats.get("stage2_deduplication", {}).get("processing_time_ms", 0))
            stage3_times.append(stats.get("stage3_mmr", {}).get("processing_time_ms", 0))

            if i == 0:
                print(f"  Iteration 1: {latency:.2f}ms (warmup)")
            elif i == iterations - 1:
                print(f"  Iteration {iterations}: {latency:.2f}ms")

        results[f"{count}_candidates"] = {
            "count": count,
            "iterations": iterations,
            "total_mean_latency_ms": round(statistics.mean(latencies), 2),
            "total_median_latency_ms": round(statistics.median(latencies), 2),
            "total_min_latency_ms": round(min(latencies), 2),
            "total_max_latency_ms": round(max(latencies), 2),
            "total_stdev_latency_ms": round(statistics.stdev(latencies) if len(latencies) > 1 else 0, 2),
            "stage1_mean_ms": round(statistics.mean(stage1_times), 2),
            "stage2_mean_ms": round(statistics.mean(stage2_times), 2),
            "stage3_mean_ms": round(statistics.mean(stage3_times), 2)
        }

        print(f"  Total Mean: {results[f'{count}_candidates']['total_mean_latency_ms']:.2f}ms")
        print(f"    Stage 1 (Reranking): {results[f'{count}_candidates']['stage1_mean_ms']:.2f}ms")
        print(f"    Stage 2 (Dedup): {results[f'{count}_candidates']['stage2_mean_ms']:.2f}ms")
        print(f"    Stage 3 (MMR): {results[f'{count}_candidates']['stage3_mean_ms']:.2f}ms")

    return results


def main():
    """Main benchmark runner"""
    parser = argparse.ArgumentParser(description="Benchmark reranking performance")
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=["cpu", "cuda"],
        help="Device to use (cpu or cuda)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Number of iterations per test"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (optional)"
    )
    parser.add_argument(
        "--candidate-counts",
        type=int,
        nargs="+",
        default=[10, 50, 100, 200, 500],
        help="Candidate counts to test"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Reranking Performance Benchmark (Step 10.2)")
    print("=" * 70)
    print(f"Device: {args.device}")
    print(f"Iterations: {args.iterations}")
    print(f"Candidate counts: {args.candidate_counts}")
    print("=" * 70)

    # Initialize services
    print("\nInitializing services...")
    cross_encoder = CrossEncoderService(
        model_name="cross-encoder/ms-marco-MiniLM-L6-v2",
        device=args.device,
        batch_size=32
    )
    mmr_ranker = MMRRanker(lambda_param=0.7)
    dedup_service = DeduplicationService()
    pipeline = RerankingPipeline(
        cross_encoder=cross_encoder,
        mmr_ranker=mmr_ranker,
        dedup_service=dedup_service,
        enable_reranking=True,
        enable_mmr=True,
        enable_dedup=True
    )
    print("Services initialized successfully!")

    # Run benchmarks
    benchmark_results = {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device": args.device,
            "iterations": args.iterations,
            "candidate_counts": args.candidate_counts
        },
        "cross_encoder": benchmark_cross_encoder(
            cross_encoder,
            args.candidate_counts,
            args.iterations
        ),
        "deduplication": benchmark_deduplication(
            dedup_service,
            args.candidate_counts,
            args.iterations
        ),
        "mmr": benchmark_mmr(
            mmr_ranker,
            args.candidate_counts,
            args.iterations
        ),
        "full_pipeline": benchmark_pipeline(
            pipeline,
            args.candidate_counts,
            args.iterations
        )
    }

    # Print summary
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)

    for count in args.candidate_counts:
        print(f"\n{count} Candidates:")
        print(f"  Cross-Encoder: {benchmark_results['cross_encoder'][f'{count}_candidates']['mean_latency_ms']:.2f}ms")
        print(f"  Deduplication: {benchmark_results['deduplication'][f'{count}_candidates']['mean_latency_ms']:.2f}ms")
        print(f"  MMR: {benchmark_results['mmr'][f'{count}_candidates']['mean_latency_ms']:.2f}ms")
        print(f"  Full Pipeline: {benchmark_results['full_pipeline'][f'{count}_candidates']['total_mean_latency_ms']:.2f}ms")

    # Save to file if requested
    if args.output:
        output_path = args.output
        with open(output_path, 'w') as f:
            json.dump(benchmark_results, f, indent=2)
        print(f"\nResults saved to: {output_path}")

    print("\n" + "=" * 70)
    print("Benchmark Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
