#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure `src/` is on sys.path so `src/legal_similarity` can be imported
# when running the script directly (without installing the package).
# For `main.py` the package root is the file's parent (not two levels up).
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from legal_similarity.index import LSHIndex  # type: ignore[import-not-found]


def _sample_query_files(sample_dir: Path) -> list[Path]:
    return sorted(path for path in sample_dir.glob("*.txt") if path.is_file())


def _query_display_name(path: Path) -> str:
    friendly_title: str | None = None
    try:
        for line in path.read_text(encoding="utf-8").splitlines()[:5]:
            clean = line.strip()
            lower = clean.lower()
            if lower.startswith("query name:"):
                friendly_title = clean.split(":", 1)[1].strip()
                break
            if lower.startswith("title:"):
                friendly_title = clean.split(":", 1)[1].strip()
                break
            if clean.startswith("#") and clean.lstrip("#").strip():
                friendly_title = clean.lstrip("#").strip()
                break
    except UnicodeDecodeError:
        friendly_title = None
    return f"{path.name}  —  {friendly_title}" if friendly_title else path.name


def _print_menu(files: list[Path], sample_dir: Path) -> None:
    print("\n                User Interaction Centre               ")
    print("MinHash + LSH index is already made. Select a sample query to test.")

    for idx, path in enumerate(files, start=1):
        print(f"  {idx}. {_query_display_name(path)}")
    print("")


def _choose_query(sample_dir: Path, sample_index: int | None = None) -> Path:
    files = _sample_query_files(sample_dir)
    if not files:
        raise SystemExit(f"No .txt query files found in {sample_dir}")
    if sample_index is not None:
        if not 1 <= sample_index <= len(files):
            raise SystemExit(f"--sample-index must be between 1 and {len(files)}")
        return files[sample_index - 1]
    _print_menu(files, sample_dir)
    while True:
        choice = input(f"\nEnter choice [1-{len(files)}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(files):
            return files[int(choice) - 1]
        print("Invalid choice. Please enter one listed number.")


def _print_results(query_path: Path, results: list[dict[str, object]], stats: dict[str, object], threshold: float, max_results: int) -> None:
    print("\n                Similarity Results                ")
    print(f"Selected query     : {_query_display_name(query_path)}")
    print(f"Indexed documents  : {stats.get('documents', 'unknown')}")
    print(f"Threshold          : {threshold:.2f}")
    print(f"Max results        : {max_results}")
    print(f"Matches found      : {len(results)}")

    if not results:
        print("\nNo documents met the selected similarity threshold.")
        print("=========================================================")
        return

    for rank, item in enumerate(results, start=1):
        print(f"\n{rank}. {item.get('doc_id')}")
        print(f"   Score            : {item.get('score')}")
        print(f"   MinHash estimate : {item.get('estimated_minhash')}")
        print(f"   Title            : {item.get('title')}")
        print(f"   Corpus path      : {item.get('path')}")
    print("=========================================================")


def main() -> None:
    parser = argparse.ArgumentParser(description="Main user interaction centre for sample query testing.")
    parser.add_argument(
        "--db",
        default=str(ROOT / "outputs" / "legal_lsh.sqlite"),
        help="SQLite index made by scripts/build_minhash.py",
    )
    parser.add_argument(
        "--sample-dir",
        default=str(ROOT / "data" / "sample_queries"),
        help="Folder containing sample query .txt files",
    )
    parser.add_argument("--sample-index", type=int, help="Run a listed query by number without typing input")
    parser.add_argument("--threshold", type=float, default=0.30, help="Minimum exact Jaccard similarity")
    parser.add_argument("--max-results", type=int, default=25, help="Maximum results to print")
    parser.add_argument("--json", action="store_true", help="Print raw JSON results")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(
            f"Index not found: {db_path}\n"
            "Run this one-time step first:\n"
            "PYTHONPATH=src python scripts/build_minhash.py"
        )

    query_path = _choose_query(Path(args.sample_dir), args.sample_index)
    index = LSHIndex(db_path)
    results = index.query_file(query_path, threshold=args.threshold, max_results=args.max_results)
    if args.json:
        print(json.dumps(results, indent=2))
        return
    _print_results(query_path, results, index.stats(), args.threshold, args.max_results)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user.", file=sys.stderr)
        raise SystemExit(130)
