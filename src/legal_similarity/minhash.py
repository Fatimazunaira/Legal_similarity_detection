from __future__ import annotations

import hashlib
import json
import random
from functools import lru_cache
from typing import Iterable

from .config import LSHConfig, MERSENNE_PRIME

INF = MERSENNE_PRIME


@lru_cache(maxsize=32)
def hash_parameters(t: int, seed: int) -> tuple[tuple[int, int], ...]:
    rng = random.Random(seed)
    params: list[tuple[int, int]] = []
    used = set()
    while len(params) < t:
        a = rng.randrange(1, MERSENNE_PRIME - 1)
        b = rng.randrange(0, MERSENNE_PRIME - 1)
        if (a, b) not in used:
            used.add((a, b))
            params.append((a, b))
    return tuple(params)


def minhash_signature(shingles: set[int], config: LSHConfig) -> list[int]:
    """Compute a deterministic MinHash signature for a shingle set."""
    if not shingles:
        return []
    signature: list[int] = []
    params = hash_parameters(config.t, config.seed)
    for a, b in params:
        minimum = min(((a * shingle + b) % MERSENNE_PRIME) for shingle in shingles)
        signature.append(minimum)
    return signature


def signature_similarity(sig_a: list[int], sig_b: list[int]) -> float:
    if not sig_a or not sig_b or len(sig_a) != len(sig_b):
        return 0.0
    return sum(1 for a, b in zip(sig_a, sig_b) if a == b) / len(sig_a)


def exact_jaccard(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a.intersection(b))
    union = len(a) + len(b) - inter
    return inter / union if union else 0.0


def band_slices(signature: list[int], config: LSHConfig) -> Iterable[tuple[int, tuple[int, ...]]]:
    if len(signature) != config.t:
        raise ValueError(f"Expected signature length {config.t}; got {len(signature)}")
    for band in range(config.b):
        start = band * config.r
        end = start + config.r
        yield band, tuple(signature[start:end])


def bucket_key(band_values: tuple[int, ...]) -> str:
    raw = json.dumps(band_values, separators=(",", ":")).encode("ascii")
    return hashlib.blake2b(raw, digest_size=16).hexdigest()
