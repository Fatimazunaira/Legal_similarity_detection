from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Iterable

from .config import LSHConfig
from .minhash import band_slices, bucket_key, minhash_signature
from .storage import SimilarityStore
from .text import document_id_from_path, iter_document_paths, read_text_file, tokenize, generate_shingles

LOG = logging.getLogger(__name__)


def _jsonl_write(records: Iterable[dict], output_file: Path) -> int:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_file.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    return count


def process_corpus_once(corpus_dir: Path, output_file: Path, config: LSHConfig) -> dict[str, object]:
    """One-time processing stage: read corpus and save normalized tokens.

    Output JSONL fields:
      doc_id, path, title, token_count, tokens
    """
    corpus_dir = corpus_dir.resolve()
    started = time.perf_counter()
    skipped = 0

    def records() -> Iterable[dict]:
        nonlocal skipped
        for path in iter_document_paths(corpus_dir):
            doc_id = document_id_from_path(path, corpus_dir)
            try:
                text = read_text_file(path, config)
                tokens = tokenize(text)
                title = next((line.strip("# ") for line in text.splitlines() if line.strip()), doc_id)
                if not tokens:
                    skipped += 1
                    LOG.warning("Skipping empty token document: %s", path)
                    continue
                yield {
                    "doc_id": doc_id,
                    "path": str(path.relative_to(corpus_dir).as_posix()),
                    "title": title[:300],
                    "token_count": len(tokens),
                    "tokens": tokens,
                }
            except Exception:
                skipped += 1
                LOG.exception("Failed processing %s", path)

    processed = _jsonl_write(records(), output_file)
    return {
        "stage": "process_corpus_once",
        "processed": processed,
        "skipped": skipped,
        "output_file": str(output_file),
        "seconds": round(time.perf_counter() - started, 4),
    }


def make_shingles_once(processed_file: Path, output_file: Path, config: LSHConfig) -> dict[str, object]:
    """One-time shingle stage: read processed tokens and save hashed shingles."""
    started = time.perf_counter()
    total = 0
    skipped = 0
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with processed_file.open("r", encoding="utf-8") as src, output_file.open("w", encoding="utf-8") as dst:
        for line in src:
            if not line.strip():
                continue
            record = json.loads(line)
            tokens = record.get("tokens") or []
            shingles = generate_shingles(tokens, config.k)
            if not shingles:
                skipped += 1
                LOG.warning("Skipping document with no shingles: %s", record.get("doc_id"))
                continue
            out = {
                "doc_id": record["doc_id"],
                "path": record.get("path", record["doc_id"]),
                "title": record.get("title", record["doc_id"]),
                "token_count": int(record.get("token_count", len(tokens))),
                "shingle_count": len(shingles),
                "shingles": sorted(shingles),
            }
            dst.write(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
            total += 1
    return {
        "stage": "make_shingles_once",
        "documents": total,
        "skipped": skipped,
        "output_file": str(output_file),
        "seconds": round(time.perf_counter() - started, 4),
    }


def build_minhash_lsh_once(shingles_file: Path, db_path: Path, config: LSHConfig, reset: bool = True, commit_every: int = 500) -> dict[str, object]:
    """One-time index stage: read saved shingles, compute MinHash signatures and LSH buckets."""
    started = time.perf_counter()
    store = SimilarityStore(db_path)
    store.initialize()
    if reset:
        store.reset()

    total = 0
    skipped = 0
    with store.connect() as con, shingles_file.open("r", encoding="utf-8") as src:
        con.execute("BEGIN")
        for line in src:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                shingles = set(int(value) for value in record.get("shingles", []))
                if not shingles:
                    skipped += 1
                    continue
                sig = minhash_signature(shingles, config)
                doc_id = record["doc_id"]
                con.execute(
                    """
                    INSERT OR REPLACE INTO documents
                    (doc_id, path, title, token_count, shingle_count, signature_json, shingles_blob)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        record.get("path", doc_id),
                        str(record.get("title", doc_id))[:300],
                        int(record.get("token_count", 0)),
                        len(shingles),
                        json.dumps(sig),
                        store.pack_shingles(shingles),
                    ),
                )
                con.execute("DELETE FROM buckets WHERE doc_id = ?", (doc_id,))
                con.executemany(
                    "INSERT OR REPLACE INTO buckets(band, bucket_key, doc_id) VALUES (?, ?, ?)",
                    [(band, bucket_key(values), doc_id) for band, values in band_slices(sig, config)],
                )
                total += 1
                if total % commit_every == 0:
                    con.commit()
                    con.execute("BEGIN")
            except Exception:
                skipped += 1
                LOG.exception("Failed building MinHash/LSH for line in %s", shingles_file)
        con.commit()

    store.set_meta("config", config.__dict__)
    store.set_meta(
        "last_build",
        {
            "stage": "build_minhash_lsh_once",
            "documents": total,
            "skipped": skipped,
            "seconds": round(time.perf_counter() - started, 4),
            "source_shingles_file": str(shingles_file),
        },
    )
    return {
        "stage": "build_minhash_lsh_once",
        "indexed": total,
        "skipped": skipped,
        "db_path": str(db_path),
        "seconds": round(time.perf_counter() - started, 4),
    }
