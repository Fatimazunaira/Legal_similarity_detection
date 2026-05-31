from __future__ import annotations

from pathlib import Path

from .config import LSHConfig, SUPPORTED_EXTENSIONS
from .text import iter_document_paths, read_text_file, tokenize


def validate_corpus(corpus_dir: str | Path, config: LSHConfig) -> dict[str, object]:
    corpus_dir = Path(corpus_dir)
    total = 0
    valid = 0
    invalid: list[dict[str, str]] = []
    for path in iter_document_paths(corpus_dir):
        total += 1
        try:
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                raise ValueError("unsupported extension")
            text = read_text_file(path, config)
            tokens = tokenize(text)
            if len(tokens) < config.k:
                raise ValueError(f"document has fewer than k={config.k} tokens")
            valid += 1
        except Exception as exc:
            invalid.append({"path": str(path), "error": str(exc)})
    return {"total_files": total, "valid_files": valid, "invalid_files": invalid}
