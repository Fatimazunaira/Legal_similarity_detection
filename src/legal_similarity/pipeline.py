from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from .config import LSHConfig
from .index import LSHIndex
from .validation import validate_corpus

LOG = logging.getLogger(__name__)


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def run_pipeline(corpus_dir: Path, db_path: Path, output_dir: Path, config: LSHConfig) -> dict[str, object]:
    """End-to-end batch pipeline: validate -> index -> report stats."""
    output_dir.mkdir(parents=True, exist_ok=True)
    validation = validate_corpus(corpus_dir, config)
    index = LSHIndex(db_path, config)
    build = index.build(corpus_dir, reset=True)
    stats = index.stats()
    report = {
        "pipeline": "validate_build_index",
        "config": asdict(config),
        "validation": validation,
        "build": build,
        "stats": stats,
        "monitoring_points": [
            "input_file_count",
            "skipped_documents",
            "documents_per_second",
            "candidate_count_per_query",
            "p50_p95_query_latency_ms",
            "sqlite_db_size_bytes",
        ],
        "stages": [
            "ingest supported .txt/.md/.docx files",
            "normalize Unicode and tokenize",
            "generate k-word shingles",
            "compute MinHash signatures",
            "write signatures and compressed shingles to SQLite",
            "write band bucket rows and indexes",
            "query by LSH candidates and exact Jaccard verification",
        ],
    }
    (output_dir / "pipeline_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
