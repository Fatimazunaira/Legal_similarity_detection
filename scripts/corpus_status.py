#!/usr/bin/env python
from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    legal_dir = root / "data" / "corpus" / "legal_docs"
    test_dir = root / "data" / "corpus" / "testing_docs"
    query_dir = root / "data" / "sample_queries"
    legal_docs = sorted(legal_dir.glob("*.txt"))
    test_docs = sorted(test_dir.glob("*.txt"))
    sample_queries = sorted(query_dir.glob("*.txt"))

    print("================ Data Centre ================")
    print("Corpus is already created one time in this package.")
    print(f"Legal corpus folder : {legal_dir}")
    print(f"Legal documents     : {len(legal_docs)}")
    print(f"Sample query folder : {query_dir}")
    print(f"Sample queries      : {len(sample_queries)}")


if __name__ == "__main__":
    main()
