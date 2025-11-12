#!/usr/bin/env python3
"""
Docling Parser Performance Benchmark Script

Benchmarks Docling parser performance across different configurations:
- CPU vs GPU (if available)
- Standard vs Threaded pipeline
- Different batch sizes
- Small vs large PDFs

Usage:
    python backend/scripts/benchmark_docling.py
    python backend/scripts/benchmark_docling.py --samples ./test_pdfs/
    python backend/scripts/benchmark_docling.py --config-comparison

Outputs:
    - Console: Real-time progress and summary table
    - File: benchmark_results_TIMESTAMP.json (detailed results)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import tempfile

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.parsers.docling_parser import DoclingParser
from app.core.config import settings


class DoclingBenchmark:
    """Benchmark Docling parser performance."""

    def __init__(self, output_dir: str = "./benchmark_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = []

    def create_test_pdf(self, page_count: int) -> str:
        """
        Create a test PDF with specified page count.

        Args:
            page_count: Number of pages to create

        Returns:
            Path to temporary PDF file
        """
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            import io

            # Create PDF in memory
            pdf_buffer = io.BytesIO()
            c = canvas.Canvas(pdf_buffer, pagesize=letter)

            for page_num in range(1, page_count + 1):
                c.drawString(100, 750, f"QueryBox Docling Benchmark - Page {page_num}/{page_count}")
                c.drawString(100, 730, f"This is test content for benchmarking purposes.")
                c.drawString(100, 710, f"Generated at: {datetime.now().isoformat()}")

                # Add some varied content
                y_pos = 680
                for i in range(10):
                    c.drawString(100, y_pos, f"Line {i+1}: Sample text for parsing benchmark testing.")
                    y_pos -= 20

                c.showPage()

            c.save()
            pdf_buffer.seek(0)

            # Write to temp file
            temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, mode='wb')
            temp_file.write(pdf_buffer.getvalue())
            temp_file.close()

            return temp_file.name

        except ImportError:
            print("ERROR: reportlab not installed. Install with: pip install reportlab")
            sys.exit(1)

    def benchmark_config(
        self,
        config_name: str,
        pdf_path: str,
        page_count: int,
        device: str = "auto",
        use_threaded: bool = True,
        batch_size: int = 4,
        eager_init: bool = False
    ) -> Dict[str, Any]:
        """
        Benchmark a specific configuration.

        Args:
            config_name: Human-readable config name
            pdf_path: Path to PDF to parse
            page_count: Number of pages in PDF
            device: Device to use (auto, cpu, cuda, mps)
            use_threaded: Use threaded pipeline
            batch_size: OCR batch size
            eager_init: Use eager initialization

        Returns:
            Benchmark result dictionary
        """
        print(f"\n{'='*60}")
        print(f"Benchmarking: {config_name}")
        print(f"{'='*60}")

        # Temporarily override settings
        original_device = settings.DOCLING_DEVICE
        original_threaded = settings.DOCLING_USE_THREADED_PIPELINE
        original_batch_size = settings.DOCLING_OCR_BATCH_SIZE
        original_eager = settings.DOCLING_EAGER_INIT

        try:
            settings.DOCLING_DEVICE = device
            settings.DOCLING_USE_THREADED_PIPELINE = use_threaded
            settings.DOCLING_OCR_BATCH_SIZE = batch_size
            settings.DOCLING_EAGER_INIT = eager_init

            # Initialize parser
            init_start = time.time()
            parser = DoclingParser(eager_init=eager_init)
            init_duration = time.time() - init_start

            # Parse document
            parse_start = time.time()
            result = parser.parse(pdf_path)
            parse_duration = time.time() - parse_start

            # Calculate metrics
            pages_per_second = page_count / parse_duration if parse_duration > 0 else 0
            seconds_per_page = parse_duration / page_count if page_count > 0 else 0

            benchmark_result = {
                "config_name": config_name,
                "timestamp": datetime.now().isoformat(),
                "device": parser.device,
                "device_name": parser.device_name,
                "configuration": {
                    "device_setting": device,
                    "use_threaded_pipeline": use_threaded,
                    "ocr_batch_size": batch_size,
                    "eager_init": eager_init,
                    "num_threads": settings.DOCLING_NUM_THREADS,
                },
                "document_info": {
                    "page_count": page_count,
                    "text_length": result.metadata.get("text_length", 0),
                    "pages_with_ocr": result.metadata.get("pages_with_ocr", 0),
                },
                "performance": {
                    "init_time_seconds": round(init_duration, 3),
                    "parse_time_seconds": round(parse_duration, 3),
                    "total_time_seconds": round(init_duration + parse_duration, 3),
                    "seconds_per_page": round(seconds_per_page, 3),
                    "pages_per_second": round(pages_per_second, 2),
                },
                "success": result.error is None,
                "error": result.error,
            }

            # Print summary
            print(f"Device: {parser.device_name}")
            print(f"Initialization: {init_duration:.2f}s")
            print(f"Parse time: {parse_duration:.2f}s ({seconds_per_page:.3f}s/page)")
            print(f"Throughput: {pages_per_second:.2f} pages/sec")
            print(f"Text extracted: {result.metadata.get('text_length', 0)} chars")

            return benchmark_result

        except Exception as e:
            print(f"ERROR: {e}")
            return {
                "config_name": config_name,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e),
            }

        finally:
            # Restore settings
            settings.DOCLING_DEVICE = original_device
            settings.DOCLING_USE_THREADED_PIPELINE = original_threaded
            settings.DOCLING_OCR_BATCH_SIZE = original_batch_size
            settings.DOCLING_EAGER_INIT = original_eager

    def run_standard_benchmark(self, pdf_path: str = None, page_count: int = 10):
        """
        Run standard benchmark with current configuration.

        Args:
            pdf_path: Optional path to existing PDF
            page_count: Pages to generate if no PDF provided
        """
        print("\n" + "="*60)
        print("DOCLING PARSER STANDARD BENCHMARK")
        print("="*60)

        # Create or use provided PDF
        if pdf_path and os.path.exists(pdf_path):
            print(f"Using existing PDF: {pdf_path}")
            temp_pdf = pdf_path
            cleanup_pdf = False
        else:
            print(f"Creating test PDF with {page_count} pages...")
            temp_pdf = self.create_test_pdf(page_count)
            cleanup_pdf = True

        try:
            # Benchmark current configuration
            result = self.benchmark_config(
                config_name="Current Configuration",
                pdf_path=temp_pdf,
                page_count=page_count,
                device=settings.DOCLING_DEVICE,
                use_threaded=settings.DOCLING_USE_THREADED_PIPELINE,
                batch_size=settings.DOCLING_OCR_BATCH_SIZE,
                eager_init=settings.DOCLING_EAGER_INIT,
            )

            self.results.append(result)
            self.save_results()
            self.print_summary()

        finally:
            if cleanup_pdf:
                try:
                    os.unlink(temp_pdf)
                except Exception:
                    pass

    def run_comparison_benchmark(self, page_counts: List[int] = [5, 10, 50]):
        """
        Run comprehensive comparison across configurations.

        Args:
            page_counts: List of page counts to test
        """
        print("\n" + "="*60)
        print("DOCLING PARSER CONFIGURATION COMPARISON")
        print("="*60)

        configs = [
            ("CPU + Standard Pipeline", "cpu", False, 4, False),
            ("CPU + Threaded Pipeline", "cpu", True, 4, False),
            ("CPU + Threaded + Eager Init", "cpu", True, 4, True),
            ("Auto-detect + Threaded", "auto", True, 4, True),
        ]

        # Add GPU configs if available
        try:
            import torch
            if torch.cuda.is_available():
                configs.extend([
                    ("CUDA + Threaded + Large Batch", "cuda", True, 64, True),
                    ("CUDA + Threaded + Small Batch", "cuda", True, 4, True),
                ])
        except ImportError:
            pass

        for page_count in page_counts:
            print(f"\n\n{'#'*60}")
            print(f"# Testing with {page_count}-page PDF")
            print(f"{'#'*60}")

            temp_pdf = self.create_test_pdf(page_count)

            try:
                for config_name, device, threaded, batch_size, eager in configs:
                    result = self.benchmark_config(
                        config_name=f"{config_name} ({page_count}p)",
                        pdf_path=temp_pdf,
                        page_count=page_count,
                        device=device,
                        use_threaded=threaded,
                        batch_size=batch_size,
                        eager_init=eager,
                    )
                    self.results.append(result)

            finally:
                try:
                    os.unlink(temp_pdf)
                except Exception:
                    pass

        self.save_results()
        self.print_summary()
        self.print_comparison_table()

    def save_results(self):
        """Save benchmark results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"benchmark_results_{timestamp}.json"

        with open(output_file, 'w') as f:
            json.dump({
                "benchmark_date": datetime.now().isoformat(),
                "system_info": {
                    "device_setting": settings.DOCLING_DEVICE,
                    "num_threads": settings.DOCLING_NUM_THREADS,
                },
                "results": self.results,
            }, f, indent=2)

        print(f"\n✓ Results saved to: {output_file}")

    def print_summary(self):
        """Print summary of all benchmark results."""
        if not self.results:
            return

        print("\n" + "="*60)
        print("BENCHMARK SUMMARY")
        print("="*60)

        for result in self.results:
            if not result.get("success"):
                print(f"\n❌ {result['config_name']}: FAILED")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                continue

            perf = result.get("performance", {})
            print(f"\n✓ {result['config_name']}")
            print(f"  Device: {result.get('device_name', 'Unknown')}")
            print(f"  Speed: {perf.get('seconds_per_page', 0):.3f}s/page ({perf.get('pages_per_second', 0):.2f} pages/sec)")
            print(f"  Total: {perf.get('total_time_seconds', 0):.2f}s (init: {perf.get('init_time_seconds', 0):.2f}s)")

    def print_comparison_table(self):
        """Print formatted comparison table."""
        if not self.results:
            return

        print("\n" + "="*80)
        print("PERFORMANCE COMPARISON TABLE")
        print("="*80)

        # Header
        print(f"{'Configuration':<40} {'Device':<15} {'s/page':>10} {'pages/s':>10} {'Total(s)':>10}")
        print("-" * 80)

        # Sort by speed (fastest first)
        sorted_results = sorted(
            [r for r in self.results if r.get("success")],
            key=lambda x: x.get("performance", {}).get("seconds_per_page", 999)
        )

        for result in sorted_results:
            config = result['config_name'][:38]
            device = result.get('device_name', 'Unknown')[:13]
            perf = result.get("performance", {})

            print(
                f"{config:<40} "
                f"{device:<15} "
                f"{perf.get('seconds_per_page', 0):>10.3f} "
                f"{perf.get('pages_per_second', 0):>10.2f} "
                f"{perf.get('total_time_seconds', 0):>10.2f}"
            )

        # Calculate speedup
        if len(sorted_results) >= 2:
            baseline = sorted_results[-1]["performance"]["seconds_per_page"]
            fastest = sorted_results[0]["performance"]["seconds_per_page"]
            speedup = baseline / fastest if fastest > 0 else 0

            print("\n" + "="*80)
            print(f"Speedup: {speedup:.2f}x faster (fastest vs baseline)")
            print("="*80)


def main():
    parser = argparse.ArgumentParser(description="Benchmark Docling parser performance")
    parser.add_argument(
        "--samples",
        type=str,
        help="Path to directory with sample PDFs (optional)"
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=10,
        help="Number of pages for generated test PDF (default: 10)"
    )
    parser.add_argument(
        "--config-comparison",
        action="store_true",
        help="Run comprehensive comparison across multiple configurations"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./benchmark_results",
        help="Output directory for results (default: ./benchmark_results)"
    )

    args = parser.parse_args()

    benchmark = DoclingBenchmark(output_dir=args.output_dir)

    if args.config_comparison:
        benchmark.run_comparison_benchmark(page_counts=[5, 10, 50])
    else:
        pdf_path = None
        if args.samples and os.path.isdir(args.samples):
            # Use first PDF found in samples directory
            for file in os.listdir(args.samples):
                if file.lower().endswith('.pdf'):
                    pdf_path = os.path.join(args.samples, file)
                    break

        benchmark.run_standard_benchmark(pdf_path=pdf_path, page_count=args.pages)


if __name__ == "__main__":
    main()
