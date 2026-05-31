from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from pathlib import Path
from typing import Iterable

try:
    from docx import Document
except Exception:  # pragma: no cover - dependency may be missing in some environments
    Document = None

from .config import SUPPORTED_EXTENSIONS, LSHConfig

LOG = logging.getLogger(__name__)
TOKEN_RE = re.compile(r"[\w]+", flags=re.UNICODE)


def normalize_text(text: str) -> str:
    """Normalize Unicode text for stable matching across legal documents."""
    text = unicodedata.normalize("NFKC", text)
    text = text.casefold()
    return text


def tokenize(text: str) -> list[str]:
    """Tokenize Unicode text into lowercase word tokens."""
    return TOKEN_RE.findall(normalize_text(text))


def stable_hash64(value: str | bytes) -> int:
    """Return a deterministic 64-bit integer hash using BLAKE2b.

    Built-in hash() is intentionally randomized between Python processes and
    must not be used for persistent MinHash signatures.
    """
    raw = value if isinstance(value, bytes) else value.encode("utf-8", errors="ignore")
    return int.from_bytes(hashlib.blake2b(raw, digest_size=8).digest(), "big")


def generate_shingles(tokens: list[str], k: int) -> set[int]:
    """Generate hashed k-word shingles from token list."""
    if len(tokens) < k:
        return set()
    return {stable_hash64(" ".join(tokens[i : i + k])) for i in range(0, len(tokens) - k + 1)}


def read_text_file(path: Path, config: LSHConfig) -> str:
    """Read .txt, .md, or .docx files with size checks and safe decoding."""
    path = path.resolve()
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {path.suffix}")
    size = path.stat().st_size
    if size > config.max_document_bytes:
        raise ValueError(f"File too large: {path} ({size} bytes)")
    if path.suffix.lower() == ".docx":
        if Document is None:
            raise ModuleNotFoundError(
                "Missing dependency 'python-docx'. Install it (pip install python-docx) "
                "or run the project in a virtualenv as described in README_RUN.md"
            )
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    return path.read_text(encoding="utf-8", errors="replace")


def iter_document_paths(corpus_dir: Path) -> Iterable[Path]:
    """Yield supported corpus documents in stable lexical order."""
    if not corpus_dir.exists() or not corpus_dir.is_dir():
        raise FileNotFoundError(f"Corpus directory not found: {corpus_dir}")
    for path in sorted(corpus_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def document_id_from_path(path: Path, root: Path) -> str:
    rel = path.resolve().relative_to(root.resolve())
    return rel.as_posix()


def prepare_document(text: str, config: LSHConfig) -> tuple[list[str], set[int]]:
    tokens = tokenize(text)
    shingles = generate_shingles(tokens, config.k)
    return tokens, shingles
