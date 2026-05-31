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
from legal_similarity.stages import build_minhash_lsh_once  # type: ignore[import-not-found]


def main() -> None:
    parser = argparse.ArgumentParser(description="build MinHash + LSH ")
    parser.add_argument(
        "--shingles",
        default=str(ROOT / "outputs" / "shingles" / "shingles.jsonl"),
        help="Shingles JSONL input",
    )
    parser.add_argument(
        "--db",
        default=str(ROOT / "outputs" / "legal_lsh.sqlite"),
        help="SQLite MinHash + LSH database output",
    )
    parser.add_argument("--t", type=int, default=100, help="MinHash signature length")
    parser.add_argument("--b", type=int, default=50, help="LSH number of bands")
    parser.add_argument("--k", type=int, default=3, help="Word shingle size used in stage 3")
    parser.add_argument("--append", action="store_true", help="Append/update documents instead of clearing the DB first")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_level)
    report = build_minhash_lsh_once(
        shingles_file=Path(args.shingles),
        db_path=Path(args.db),
        config=LSHConfig(t=args.t, b=args.b, k=args.k),
        reset=not args.append,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Cancelled by user.", file=sys.stderr)
        raise SystemExit(130)
