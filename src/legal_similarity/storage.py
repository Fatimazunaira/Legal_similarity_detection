from __future__ import annotations

import json
import sqlite3
import zlib
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    title TEXT,
    token_count INTEGER NOT NULL,
    shingle_count INTEGER NOT NULL,
    signature_json TEXT NOT NULL,
    shingles_blob BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS buckets (
    band INTEGER NOT NULL,
    bucket_key TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    PRIMARY KEY (band, bucket_key, doc_id)
);
CREATE INDEX IF NOT EXISTS idx_buckets_lookup ON buckets (band, bucket_key);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class SimilarityStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        try:
            yield con
        finally:
            con.close()

    def initialize(self) -> None:
        with self.connect() as con:
            con.executescript(SCHEMA)
            con.commit()

    def reset(self) -> None:
        with self.connect() as con:
            con.executescript("DROP TABLE IF EXISTS buckets; DROP TABLE IF EXISTS documents; DROP TABLE IF EXISTS meta;")
            con.commit()
        self.initialize()

    def set_meta(self, key: str, value: object) -> None:
        with self.connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                (key, json.dumps(value, sort_keys=True)),
            )
            con.commit()

    def get_meta(self, key: str) -> object | None:
        with self.connect() as con:
            row = con.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
            return json.loads(row["value"]) if row else None

    @staticmethod
    def pack_shingles(shingles: set[int]) -> bytes:
        return zlib.compress(json.dumps(sorted(shingles)).encode("ascii"), level=6)

    @staticmethod
    def unpack_shingles(blob: bytes) -> set[int]:
        return set(json.loads(zlib.decompress(blob).decode("ascii")))

    def count_documents(self) -> int:
        with self.connect() as con:
            return int(con.execute("SELECT COUNT(*) FROM documents").fetchone()[0])

    def fetch_document(self, doc_id: str) -> sqlite3.Row | None:
        with self.connect() as con:
            return con.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()

    def fetch_shingles(self, doc_id: str) -> set[int]:
        row = self.fetch_document(doc_id)
        if row is None:
            raise KeyError(doc_id)
        return self.unpack_shingles(row["shingles_blob"])

    def candidate_doc_ids(self, band_keys: list[tuple[int, str]]) -> set[str]:
        if not band_keys:
            return set()
        candidates: set[str] = set()
        with self.connect() as con:
            for band, key in band_keys:
                rows = con.execute(
                    "SELECT doc_id FROM buckets WHERE band = ? AND bucket_key = ?",
                    (band, key),
                ).fetchall()
                candidates.update(row["doc_id"] for row in rows)
        return candidates
