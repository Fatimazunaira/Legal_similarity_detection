from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from .config import LSHConfig
from .minhash import band_slices, bucket_key, exact_jaccard, minhash_signature, signature_similarity
from .storage import SimilarityStore
from .text import document_id_from_path, iter_document_paths, prepare_document, read_text_file

LOG = logging.getLogger(__name__)


class LSHIndex:
    def __init__(self, db_path: str | Path, config: LSHConfig | None = None) -> None:
        self.store = SimilarityStore(db_path)
        self.config = config or LSHConfig()
        self.store.initialize()

    def build(self, corpus_dir: str | Path, reset: bool = True, commit_every: int = 500) -> dict[str, int | float]:
        corpus_dir = Path(corpus_dir).resolve()
        if reset:
            self.store.reset()
        started = time.perf_counter()
        total = 0
        skipped = 0
        with self.store.connect() as con:
            con.execute("BEGIN")
            for path in iter_document_paths(corpus_dir):
                doc_id = document_id_from_path(path, corpus_dir)
                try:
                    text = read_text_file(path, self.config)
                    tokens, shingles = prepare_document(text, self.config)
                    if not shingles:
                        skipped += 1
                        LOG.warning("Skipping document with no shingles: %s", path)
                        continue
                    sig = minhash_signature(shingles, self.config)
                    title = next((line.strip("# ") for line in text.splitlines() if line.strip()), doc_id)
                    con.execute(
                        """
                        INSERT OR REPLACE INTO documents
                        (doc_id, path, title, token_count, shingle_count, signature_json, shingles_blob)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            doc_id,
                            doc_id,
                            title[:300],
                            len(tokens),
                            len(shingles),
                            json.dumps(sig),
                            self.store.pack_shingles(shingles),
                        ),
                    )
                    con.execute("DELETE FROM buckets WHERE doc_id = ?", (doc_id,))
                    con.executemany(
                        "INSERT OR REPLACE INTO buckets(band, bucket_key, doc_id) VALUES (?, ?, ?)",
                        [(band, bucket_key(values), doc_id) for band, values in band_slices(sig, self.config)],
                    )
                    total += 1
                    if total % commit_every == 0:
                        con.commit()
                        con.execute("BEGIN")
                except Exception:
                    skipped += 1
                    LOG.exception("Failed indexing %s", path)
            con.commit()
        elapsed = time.perf_counter() - started
        self.store.set_meta("config", self.config.__dict__)
        self.store.set_meta("last_build", {"documents": total, "skipped": skipped, "seconds": elapsed})
        return {"indexed": total, "skipped": skipped, "seconds": round(elapsed, 4)}

    def query_text(self, text: str, threshold: float = 0.30, max_results: int = 25) -> list[dict[str, object]]:
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")
        if max_results <= 0 or max_results > 1000:
            raise ValueError("max_results must be between 1 and 1000")
        tokens, shingles = prepare_document(text, self.config)
        if not shingles:
            return []
        sig = minhash_signature(shingles, self.config)
        band_keys = [(band, bucket_key(values)) for band, values in band_slices(sig, self.config)]
        candidate_ids = self.store.candidate_doc_ids(band_keys)
        results: list[dict[str, object]] = []
        with self.store.connect() as con:
            for doc_id in candidate_ids:
                row = con.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
                if row is None:
                    continue
                doc_shingles = self.store.unpack_shingles(row["shingles_blob"])
                score = exact_jaccard(shingles, doc_shingles)
                if score >= threshold:
                    doc_sig = json.loads(row["signature_json"])
                    results.append(
                        {
                            "doc_id": doc_id,
                            "title": row["title"],
                            "path": row["path"],
                            "score": round(score, 6),
                            "estimated_minhash": round(signature_similarity(sig, doc_sig), 6),
                            "token_count": row["token_count"],
                            "shingle_count": row["shingle_count"],
                        }
                    )
        results.sort(key=lambda x: (x["score"], x["estimated_minhash"], x["doc_id"]), reverse=True)
        return results[:max_results]

    def query_file(self, file_path: str | Path, threshold: float = 0.30, max_results: int = 25) -> list[dict[str, object]]:
        text = read_text_file(Path(file_path), self.config)
        return self.query_text(text, threshold=threshold, max_results=max_results)

    def stats(self) -> dict[str, object]:
        return {
            "documents": self.store.count_documents(),
            "config": self.store.get_meta("config") or self.config.__dict__,
            "last_build": self.store.get_meta("last_build"),
        }
