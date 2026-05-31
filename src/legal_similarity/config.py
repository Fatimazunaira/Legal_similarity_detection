from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MERSENNE_PRIME = 2_305_843_009_213_693_951
MAX_DOCUMENT_BYTES = 5_000_000
SUPPORTED_EXTENSIONS = {".txt", ".md", ".docx"}


@dataclass(frozen=True)
class LSHConfig:
    """Configuration for MinHash + LSH.

    t: signature length / number of hash functions.
    b: number of LSH bands.
    k: word shingle size.
    seed: deterministic seed used to generate universal hash functions.
    """

    t: int = 100
    b: int = 50
    k: int = 3
    seed: int = 251_2025
    max_document_bytes: int = MAX_DOCUMENT_BYTES

    def __post_init__(self) -> None:
        if self.t <= 0 or self.b <= 0 or self.k <= 0:
            raise ValueError("t, b, and k must be positive integers")
        if self.t % self.b != 0:
            raise ValueError("t must be divisible by b so each band has equal rows")
        if self.max_document_bytes < 1024:
            raise ValueError("max_document_bytes is unrealistically small")

    @property
    def r(self) -> int:
        return self.t // self.b


def resolve_safe_path(path: str | Path, base_dir: str | Path | None = None) -> Path:
    """Resolve a path and optionally ensure it stays under base_dir.

    This prevents accidental path traversal in API and batch operations.
    """
    resolved = Path(path).expanduser().resolve()
    if base_dir is not None:
        base = Path(base_dir).expanduser().resolve()
        try:
            resolved.relative_to(base)
        except ValueError as exc:
            raise ValueError(f"Path {resolved} is outside allowed base directory {base}") from exc
    return resolved
