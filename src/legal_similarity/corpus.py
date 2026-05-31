from __future__ import annotations

from pathlib import Path


def corpus_paths(project_root: Path) -> dict[str, Path]:
    return {
        "legal_docs": project_root / "data" / "corpus" / "legal_docs",
        "testing_docs": project_root / "data" / "corpus" / "testing_docs",
        "queries": project_root / "data" / "sample_queries",
        "outputs": project_root / "outputs",
    }
