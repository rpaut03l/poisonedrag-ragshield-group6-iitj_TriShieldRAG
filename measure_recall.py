import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "8")
os.environ.setdefault("OMP_NUM_THREADS", "8")
os.environ.setdefault("MKL_NUM_THREADS", "8")

import gc
import json
import time
from pathlib import Path

import numpy as np
import torch
import faiss
from huggingface_hub import hf_hub_download
from sentence_transformers import SentenceTransformer

faiss.omp_set_num_threads(8)

QUESTIONS = [
    "Who founded Tesla Motors?",
    "Who designed the Eiffel Tower?",
    "Who developed the theory of relativity?",
    "Who created the Python programming language?",
    "Who wrote Hamlet?",
    "What is the highest mountain on Earth?",
    "Who painted the Mona Lisa?",
    "What is the capital of Australia?",
    "Who discovered penicillin?",
    "What year did World War II end?",
]

REPO = 'rpaut03l/trishieldrag-nq-mpnet-embeddings'
SHARD_OFFSETS = [0, 100000, 200000, 300000, 400000, 500000, 600000,
                  700000, 800000, 900000, 1000000, 1100000, 1200000,
                  1300000, 1400000, 1500000, 1600000, 1700000, 1800000,
                  1900000, 2000000, 2100000, 2200000, 2300000, 2400000,
                  2500000, 2600000]
EXPECTED_TOTAL = 2_681_468

GT_CACHE = Path("ground_truth_top5.npy")
RESULTS_PATH = Path("recall_results.json")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
if DEVICE != "cuda":
    print("WARNING: CUDA not available, falling back to CPU for the exact "
          "search -- this will be much slower.", flush=True)

t0 = time.time()

print(f'encoding questions (device={DEVICE})...', flush=True)
model = SentenceTransformer('all-mpnet-base-v2', device=DEVICE)
qs_np = model.encode(QUESTIONS, normalize_embeddings=True).astype('float32')
del model
gc.collect()
if DEVICE == "cuda":
    torch.cuda.empty_cache()

if GT_CACHE.exists():
    print(f'found cached ground truth at {GT_CACHE}, loading (skipping full rebuild)...', flush=True)
    gt = np.load(GT_CACHE)
else:
    print(f'building exact ground truth over FULL corpus via {DEVICE} matmul...', flush=True)
    qs_t = torch.from_numpy(qs_np).to(DEVICE)

    best_scores = torch.full((len(QUESTIONS), 5), -1e9, device=DEVICE)
    best_idx = torch.zeros((len(QUESTIONS), 5), dtype=torch.long, device=DEVICE)

    global_offset = 0
    for i in SHARD_OFFSETS:
        fname = 'emb_%09d.npy' % i
        print(f'  downloading {fname}...', flush=True)
        p = hf_hub_download(REPO, fname, repo_type='dataset')
        a = np.load(p)
        shard_t = torch.from_numpy(a).to(DEVICE)

        sims = qs_t @ shard_t.T

        combined_scores = torch.cat([best_scores, sims], dim=1)
        combined_idx = torch.cat([
            best_idx,
            torch.arange(global_offset, global_offset + shard_t.shape[0],
                         device=DEVICE).unsqueeze(0).expand(len(QUESTIONS), -1)
        ], dim=1)
        top_scores, top_pos = torch.topk(combined_scores, k=5, dim=1)
        best_scores = top_scores
        best_idx = torch.gather(combined_idx, 1, top_pos)

        global_offset += shard_t.shape[0]
        print(f'  processed {fname}: {shard_t.shape[0]} vectors '
              f'(running total: {global_offset})', flush=True)
        del shard_t, sims, combined_scores, combined_idx, a
        gc.collect()
        if DEVICE == "cuda":
            torch.cuda.empty_cache()

    assert global_offset == EXPECTED_TOTAL, (
        f"Processed {global_offset} vectors, expected {EXPECTED_TOTAL}. "
        f"A shard silently failed to load -- DO NOT trust recall numbers "
        f"computed from this run."
    )
    print(f'exact ground truth verified: {global_offset} vectors processed '
          f'(matches expected {EXPECTED_TOTAL})', flush=True)

    gt = best_idx.cpu().numpy()
    np.save(GT_CACHE, gt)
    print(f'ground truth computed and cached to {GT_CACHE}', flush=True)
    del qs_t, best_scores, best_idx
    gc.collect()
    if DEVICE == "cuda":
        torch.cuda.empty_cache()

print('loading approximate index (faiss, CPU)...', flush=True)
approx = faiss.read_index('embeddings/nq_ivf_nlist6550.index')
print('  %d vectors' % approx.ntotal, flush=True)
assert approx.ntotal == EXPECTED_TOTAL, (
    f"Approximate index has {approx.ntotal} vectors, expected {EXPECTED_TOTAL}."
)

print('')
print('nprobe   recall@5', flush=True)
print('----------------------', flush=True)

rows = []
done_nprobes = set()
if RESULTS_PATH.exists():
    try:
        prior = json.load(open(RESULTS_PATH))
        rows = prior.get('results', [])
        done_nprobes = {r['nprobe'] for r in rows}
        if done_nprobes:
            print(f'  (resuming: already have results for nprobe={sorted(done_nprobes)})', flush=True)
    except Exception:
        pass

for npb in (1, 8, 16, 32, 64, 128, 256, 512, 1024, 2048):
    if npb in done_nprobes:
        print(f'{npb:6d}   (cached) {[r["recall_at_5"] for r in rows if r["nprobe"] == npb][0]:.4f}', flush=True)
        continue
    approx.nprobe = npb
    _, ap = approx.search(qs_np, 5)
    r = float(np.mean([len(set(g) & set(a)) / 5 for g, a in zip(gt, ap)]))
    rows.append({'nprobe': npb, 'recall_at_5': round(r, 4)})
    print('%6d   %.4f' % (npb, r), flush=True)

    json.dump({
        'corpus': 'BeIR/nq, 2681468 passages',
        'ground_truth': 'exact search via GPU torch matmul over full corpus (verified count)',
        'index': 'IndexIVFFlat, nlist=6550, inner product',
        'n_queries': len(QUESTIONS),
        'results': rows,
    }, open(RESULTS_PATH, 'w'), indent=2)

print('saved (%ds)' % (time.time() - t0), flush=True)
