#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure `src/` is on sys.path so `src/legal_similarity` can be imported
# when running the script directly (without installing the package).
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from legal_similarity.config import LSHConfig  # type: ignore[import-not-found]
from legal_similarity.pipeline import configure_logging  # type: ignore[import-not-found]
from legal_similarity.stages import make_shingles_once  # type: ignore[import-not-found]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create shingles ")
    parser.add_argument(
        "--processed",
        default=str(ROOT / "outputs" / "processed" / "processed_docs.jsonl"),
        help="Processed token JSONL input",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "outputs" / "shingles" / "shingles.jsonl"),
        help="Shingles JSONL output",
    )
    parser.add_argument("--k", type=int, default=3, help="Word shingle size")
    parser.add_argument("--t", type=int, default=100, help="MinHash signature length used later")
    parser.add_argument("--b", type=int, default=50, help="LSH bands used later")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_level)
    report = make_shingles_once(
        processed_file=Path(args.processed),
        output_file=Path(args.output),
        config=LSHConfig(k=args.k, t=args.t, b=args.b),
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Cancelled by user.", file=sys.stderr)
        raise SystemExit(130)
