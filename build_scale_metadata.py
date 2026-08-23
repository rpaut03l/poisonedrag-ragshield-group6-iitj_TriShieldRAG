"""
build_scale_metadata.py -- one-time setup to make Scale Mode
actually usable on this fresh machine:

  1. Downloads BeIR's `nq` corpus (2,681,468 clean plain-text
     passages -- confirmed as the real source of the embeddings via
     the shell history: measure_recall.py's own output JSON tags its
     ground truth as "BeIR/nq, 2681468 passages").
  2. VERIFIES alignment between that corpus and the actual embedding
     shards by re-embedding a handful of scattered passages and
     cosine-comparing against the real saved vectors at those exact
     indices. This is not optional -- trusting order-of-download to
     match order-of-embedding without checking is exactly the kind
     of assumption that produced the earlier corrupted
     scale_target_questions.json.
  3. Merges the 27 embedding shards into a single
     embeddings/nq_embeddings.npy (the path retriever.py expects,
     no env var override needed).
  4. Builds embeddings/nq_embeddings.meta.json covering the FULL
     corpus, in the SAME order, so any retrieved document -- not
     just the ones sampled for target questions -- has real text
     for Ring 1/2/3 to actually evaluate.
"""
import gc
import json
import os
import time
from pathlib import Path

import numpy as np
import torch
from datasets import load_dataset
from huggingface_hub import hf_hub_download
from sentence_transformers import SentenceTransformer

REPO = 'rpaut03l/trishieldrag-nq-mpnet-embeddings'
SHARD_OFFSETS = [0, 100000, 200000, 300000, 400000, 500000, 600000,
                  700000, 800000, 900000, 1000000, 1100000, 1200000,
                  1300000, 1400000, 1500000, 1600000, 1700000, 1800000,
                  1900000, 2000000, 2100000, 2200000, 2300000, 2400000,
                  2500000, 2600000]
EXPECTED_TOTAL = 2_681_468
TEXT_CAP = 2000  # matches the original build_embeddings.py's cap

EMB_OUT = Path("embeddings/nq_embeddings.npy")
META_OUT = Path("embeddings/nq_embeddings.meta.json")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
t0 = time.time()

print("Step 1/4: loading BeIR/nq corpus...", flush=True)
ds = load_dataset("BeIR/nq", "corpus", split="corpus")
print(f"  corpus size: {len(ds)}", flush=True)
assert len(ds) == EXPECTED_TOTAL, (
    f"BeIR/nq corpus has {len(ds)} entries, expected {EXPECTED_TOTAL}. "
    f"This is NOT the right source dataset -- STOP, do not proceed."
)
print(f"  MATCHES expected {EXPECTED_TOTAL} -- looks like the right corpus", flush=True)
first = ds[0]
print(f"  first entry fields: {list(first.keys())}", flush=True)
print(f"  first entry preview: { {k: str(v)[:100] for k, v in first.items()} }", flush=True)

print("\nStep 2/4: verifying alignment (re-embed + cosine compare)...", flush=True)
CHECK_INDICES = [0, 50_000, 300_000, 999_999, 1_500_000, 2_000_000, 2_681_467]
model = SentenceTransformer('all-mpnet-base-v2', device=DEVICE)

alignment_ok = True
for idx in CHECK_INDICES:
    shard_offset = (idx // 100_000) * 100_000
    within_shard = idx - shard_offset
    fname = 'emb_%09d.npy' % shard_offset
    p = hf_hub_download(REPO, fname, repo_type='dataset')
    shard = np.load(p, mmap_mode='r')
    saved_vec = np.array(shard[within_shard])
    del shard

    row = ds[idx]
    # CONFIRMED via diagnose_alignment.py: the original embeddings
    # were built from `text` ALONE, with no title prepended --
    # title+text gave cosine as low as 0.43-0.68 on longer passages
    # (title shifts real content out of the model's 512-token
    # truncation window), while text-only gave a perfect 1.0000 on
    # every index tested, including the two worst offenders from the
    # first (title+text) attempt.
    title = row.get("title", "")
    text = row.get("text", "")
    combined = text

    reembedded = model.encode([combined], normalize_embeddings=True)[0]
    cosine = float(np.dot(saved_vec, reembedded) /
                    (np.linalg.norm(saved_vec) * np.linalg.norm(reembedded) + 1e-12))
    status = "OK" if cosine > 0.99 else "MISMATCH"
    if cosine <= 0.99:
        alignment_ok = False
    print(f"  idx={idx:>9}  cosine={cosine:.4f}  [{status}]  title={title[:60]!r}", flush=True)

if not alignment_ok:
    raise SystemExit(
        "\nALIGNMENT VERIFICATION FAILED -- one or more indices did not "
        "match. DO NOT proceed with building meta.json from this corpus "
        "in this order; the embeddings and BeIR/nq are not aligned the "
        "way we assumed. Stop and investigate before spending more time."
    )
print("  ALL CHECKS PASSED -- BeIR/nq order matches the embedding shards.", flush=True)
del model
gc.collect()
if DEVICE == "cuda":
    torch.cuda.empty_cache()

print(f"\nStep 3/4: merging 27 shards into {EMB_OUT} ...", flush=True)
EMB_OUT.parent.mkdir(parents=True, exist_ok=True)
merged = np.empty((EXPECTED_TOTAL, 768), dtype=np.float32)
pos = 0
for i in SHARD_OFFSETS:
    fname = 'emb_%09d.npy' % i
    p = hf_hub_download(REPO, fname, repo_type='dataset')
    a = np.load(p)
    merged[pos:pos + a.shape[0]] = a
    pos += a.shape[0]
    print(f"  merged {fname}: {a.shape[0]} rows (running total: {pos})", flush=True)
    del a
    gc.collect()
assert pos == EXPECTED_TOTAL
np.save(EMB_OUT, merged)
print(f"  saved merged embeddings: {EMB_OUT} ({EMB_OUT.stat().st_size / 1e9:.2f} GB)", flush=True)
del merged
gc.collect()

print(f"\nStep 4/4: building full-corpus meta.json at {META_OUT} ...", flush=True)
meta = []
contaminated_count = 0
CONTAMINATION_MARKERS = ("<style", "<script", "position:absolute", "referencetooltip", "{position:")
for i, row in enumerate(ds):
    title = row.get("title", "")
    text = row.get("text", "")[:TEXT_CAP]
    if any(m in text.lower() for m in CONTAMINATION_MARKERS):
        contaminated_count += 1
    meta.append({
        "id": row.get("_id", f"nq_{i}"),
        "title": title,
        "text": text,
        "source": "beir_nq",
    })
    if (i + 1) % 500_000 == 0:
        print(f"  processed {i + 1} / {EXPECTED_TOTAL}...", flush=True)

print(f"  built {len(meta)} entries, {contaminated_count} flagged as "
      f"contaminated (expect ~0 -- BeIR/nq is pre-cleaned plain text)", flush=True)
META_OUT.write_text(json.dumps(meta))
print(f"  saved: {META_OUT} ({META_OUT.stat().st_size / 1e9:.2f} GB)", flush=True)

print(f"\nDone in {time.time() - t0:.0f}s.", flush=True)
print("Next: symlink the FAISS index to the default path, then re-run "
      "generate_scale_targets.py.")
