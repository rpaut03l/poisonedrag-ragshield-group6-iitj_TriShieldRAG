#!/usr/bin/env python3
"""
verify_artifacts.py -- check a local rebuild against ARTIFACT_MANIFEST.json.

Two modes, because they answer different questions.

  --exact   SHA-256 comparison. Answers "is this byte-identical to the file
            the paper's numbers were produced from?" Use it when you have
            downloaded our artifacts. A mismatch here means the download is
            corrupt or the file is not ours.

  --rebuild Numerical comparison against a freshly computed sample. Answers
            "did my rebuild produce equivalent vectors?" Use it when you have
            regenerated the embeddings yourself.

The second mode exists because SHA-256 is the wrong tool for a rebuild.
Embedding several million passages on a different GPU, CUDA version or
PyTorch build can differ in the low bits of each float without being wrong;
the hash then differs while the vectors are equivalent for every practical
purpose. Requiring an exact hash match on a rebuild would report failure on a
correct reproduction.

Usage
    python3 verify_artifacts.py --exact
    python3 verify_artifacts.py --rebuild --corpus nq --samples 200
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path

MANIFEST = "ARTIFACT_MANIFEST.json"
CORPORA = {
    "nq":       ("BeIR/nq",       "embeddings/nq_embeddings.npy",
                 "embeddings/nq_embeddings.meta.json"),
    "hotpotqa": ("BeIR/hotpotqa", "embeddings/hotpotqa_embeddings.npy",
                 "embeddings/hotpotqa_embeddings.meta.json"),
    "msmarco":  ("BeIR/msmarco",  "embeddings/msmarco_embeddings.npy",
                 "embeddings/msmarco_embeddings.meta.json"),
}


def sha256(path: Path, chunk: int = 1 << 24) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(chunk), b""):
            h.update(c)
    return h.hexdigest()


def human(n: float) -> str:
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.1f} {u}"
        n /= 1024


def mode_exact() -> int:
    man = json.loads(Path(MANIFEST).read_text())
    ok = miss = bad = 0
    print(f"{'file':46} {'size':>10}  result")
    print("-" * 74)
    for f, meta in man.items():
        p = Path(f)
        if not p.exists():
            print(f"{f:46} {'--':>10}  not present")
            miss += 1
            continue
        size = p.stat().st_size
        if size != meta["bytes"]:
            print(f"{f:46} {human(size):>10}  SIZE MISMATCH "
                  f"(expected {human(meta['bytes'])})")
            bad += 1
            continue
        got = sha256(p)
        if got == meta["sha256"]:
            print(f"{f:46} {human(size):>10}  ok")
            ok += 1
        else:
            print(f"{f:46} {human(size):>10}  HASH MISMATCH")
            print(f"{'':46} {'':>10}  expected {meta['sha256'][:32]}...")
            print(f"{'':46} {'':>10}  got      {got[:32]}...")
            bad += 1
    print("-" * 74)
    print(f"{ok} verified, {bad} mismatched, {miss} absent")
    if bad:
        print("\nA mismatch means the file differs from ours. If you rebuilt it\n"
              "yourself rather than downloading it, use --rebuild instead: bitwise\n"
              "equality is not expected across different hardware.")
    return 1 if bad else 0


def mode_rebuild(corpus: str, n_samples: int, tol: float) -> int:
    try:
        import numpy as np
        from datasets import load_dataset
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        sys.exit(f"missing dependency: {e}\n"
                 "  pip install numpy datasets sentence-transformers")

    beir, emb_path, meta_path = CORPORA[corpus]
    for f in (emb_path, meta_path):
        if not Path(f).exists():
            sys.exit(f"not found: {f}\nBuild it first with build_embeddings.py.")

    print(f"corpus     : {beir}")
    print(f"embeddings : {emb_path}")
    v = np.load(emb_path, mmap_mode="r")
    meta = json.loads(Path(meta_path).read_text())
    N, d = v.shape
    print(f"shape      : {N:,} x {d}")

    if len(meta) != N:
        print(f"\nFAIL: metadata has {len(meta):,} records but embeddings have "
              f"{N:,} rows.\nThese must correspond one-to-one; a mismatch means "
              "the shards were\nconcatenated in a different order or a shard is "
              "missing.")
        return 1
    print(f"metadata   : {len(meta):,} records, count matches")

    # norms: every vector should be unit length under our build
    rng = np.random.default_rng(0)
    idx = np.sort(rng.choice(N, size=min(n_samples, N), replace=False))
    norms = np.linalg.norm(np.array(v[idx]), axis=1)
    print(f"\nnorms over {len(idx)} sampled rows: "
          f"min {norms.min():.6f}, max {norms.max():.6f}")
    if abs(norms.mean() - 1.0) > 1e-3:
        print("WARNING: vectors are not unit-normalised. Our build sets "
              "normalize_embeddings=True;\nwithout it, inner product and cosine "
              "similarity diverge and Ring 2's relevance\nterm is on a different "
              "scale.")

    print(f"\nre-embedding {len(idx)} sampled passages to compare...")
    ds = load_dataset(beir, "corpus", split="corpus")
    model = SentenceTransformer("all-mpnet-base-v2", device="cpu")

    # text field only, matching the build: title is deliberately excluded
    texts = [ds[int(i)]["text"] for i in idx]
    fresh = model.encode(texts, batch_size=32, convert_to_numpy=True,
                         normalize_embeddings=True, show_progress_bar=False)
    stored = np.array(v[idx], dtype=np.float32)
    cos = np.sum(fresh * stored, axis=1)

    print(f"\ncosine(stored, freshly embedded) over {len(idx)} rows:")
    print(f"  min  {cos.min():.6f}")
    print(f"  mean {cos.mean():.6f}")
    print(f"  <{tol:.4f}: {(cos < tol).sum()} row(s)")

    # metadata alignment: does row i correspond to meta[i]?
    mis = [int(i) for i, j in enumerate(idx)
           if meta[int(j)]["id"] != ds[int(j)]["_id"]]
    print(f"\nmetadata id alignment: "
          f"{len(idx)-len(mis)}/{len(idx)} rows match the corpus")

    fail = (cos.min() < tol) or bool(mis)
    print()
    if fail:
        if cos.min() < tol:
            print("FAIL: some rows do not match a fresh embedding. Likely causes:\n"
                  "  - embeddings built from title+text rather than text alone\n"
                  "  - a different embedding model\n"
                  "  - shards concatenated out of order")
        if mis:
            print("FAIL: metadata rows do not correspond to embedding rows.\n"
                  "  Rebuild metadata with build_scale_metadata.py over the same\n"
                  "  corpus snapshot used for the embeddings.")
    else:
        print("PASS: rebuild is numerically equivalent to ours.\n"
              "Bitwise hashes may still differ across hardware; that is expected\n"
              "and does not indicate an error.")
    return 1 if fail else 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exact", action="store_true",
                    help="SHA-256 check against the manifest")
    ap.add_argument("--rebuild", action="store_true",
                    help="numerical check of a local rebuild")
    ap.add_argument("--corpus", choices=sorted(CORPORA), default="nq")
    ap.add_argument("--samples", type=int, default=200)
    ap.add_argument("--tol", type=float, default=0.999,
                    help="minimum acceptable cosine (default 0.999)")
    a = ap.parse_args()
    if not (a.exact or a.rebuild):
        ap.error("choose --exact or --rebuild")
    rc = 0
    if a.exact:
        rc |= mode_exact()
    if a.rebuild:
        if a.exact: print()
        rc |= mode_rebuild(a.corpus, a.samples, a.tol)
    sys.exit(rc)


if __name__ == "__main__":
    main()
