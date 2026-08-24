# Reproducing the artifacts

Everything in this paper derives from three public corpora and one public
embedding model. Nothing needs to be downloaded from us, though the large
files are mirrored for convenience.

## What is committed and what is not

| | where | size |
|---|---|---|
| Code, poison corpora, target questions, all result JSON | this repository | < 5 MB |
| SHA-256 hashes of every large artifact | `ARTIFACT_MANIFEST.json` | 4 KB |
| Embeddings, FAISS indices, aligned metadata | rebuild, or download mirror | ~102 GB |

The 102 GB is not committed because it is fully derivable. The manifest is
committed so you can confirm your rebuild corresponds to the files the
measurements came from.

---

## Path A — download and verify

If you have downloaded our mirrored artifacts:

```bash
python3 verify_artifacts.py --exact
```

Every file is hashed and compared against the manifest. A mismatch here means
the download is corrupt or the file is not ours.

Expect one line per artifact:

```
embeddings/nq_embeddings.npy                     7.7 GB  ok
ragshield_2m.index                               7.7 GB  ok
...
9 verified, 0 mismatched, 0 absent
```

---

## Path B — rebuild from scratch

### 1. Environment

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

A GPU is strongly recommended. On an RTX PRO 6000 the three corpora took
66 min (HotpotQA, 5.2M passages), 151 min (MS-MARCO, 8.8M) and roughly 40 min
(NQ, 2.7M). CPU is possible but expect days.

### 2. Embeddings

```bash
python3 build_embeddings.py --corpus BeIR/nq   --out embeddings/nq_embeddings.npy
python3 build_scale_metadata.py --corpus BeIR/nq --out embeddings/nq_embeddings.meta.json
```

Two details matter and both are easy to get wrong.

**Embed the `text` field alone, not `title` + `text`.** We verified this by
re-embedding stored passages under both policies: text-only reproduces cosine
1.0000 against the stored vectors, title-concatenated gives 0.43--0.68 on longer
passages. Since a malicious document's retrieval rank depends on this choice,
mixing policies between index construction and query time silently changes every
number.

**Metadata row `i` must correspond to embedding row `i`.** An off-by-one in
shard concatenation produces an index that retrieves fluently and wrongly with
no error raised anywhere. `verify_artifacts.py --rebuild` checks this.

### 3. Index

```bash
python3 - <<'PY'
import numpy as np, faiss, math
v = np.load("embeddings/nq_embeddings.npy", mmap_mode="r")
N, d = v.shape
nlist = int(4 * math.sqrt(N))
idx = faiss.IndexIVFFlat(faiss.IndexFlatIP(d), d, nlist, faiss.METRIC_INNER_PRODUCT)
tr = np.array(v[np.random.default_rng(0).choice(N, min(N, 50*nlist), replace=False)])
idx.train(tr); del tr
for s in range(0, N, 200_000):
    idx.add(np.array(v[s:s+200_000]))
idx.nprobe = 16
faiss.write_index(idx, "ragshield_2m.index")
PY
```

`nlist = 4*sqrt(N)` gives 6,550 for NQ, 9,150 for HotpotQA, 11,894 for MS-MARCO.
Training samples are drawn under a fixed seed, so the index is deterministic
given the same embeddings.

### 4. Verify the rebuild

```bash
python3 verify_artifacts.py --rebuild --corpus nq --samples 200
```

This does three things: confirms metadata and embedding row counts match,
re-embeds a random sample and compares against the stored vectors by cosine, and
checks that metadata IDs line up with the corpus.

```
shape      : 2,681,468 x 768
metadata   : 2,681,468 records, count matches
norms over 200 sampled rows: min 1.000000, max 1.000000
cosine(stored, freshly embedded) over 200 rows:
  min  0.999998
  mean 0.999999
metadata id alignment: 200/200 rows match the corpus
PASS
```

### 5. Calibrate retrieval

```bash
python3 measure_recall.py
```

Computes exhaustive ground truth on the GPU and reports recall at each
`nprobe`. You should see 0.72 at nprobe=1 rising to 0.98 at 16 and flat
thereafter. We fix nprobe=16 for every experiment.

This step is not optional bookkeeping. A missed clean passage raises the
effective poison fraction the defense observes, and that fraction is the
quantity Proposition 1 concerns.

---

## Why the hash will probably not match your rebuild

`--exact` compares bytes. `--rebuild` compares meaning. They answer different
questions and you want the second one for a reproduction.

Embedding several million passages on a different GPU, CUDA version or PyTorch
build can differ in the low bits of each float without being wrong. The vectors
remain equivalent for retrieval; the SHA-256 does not. So a hash mismatch on a
rebuild is expected and is not evidence of an error, whereas a cosine below
0.999 or a metadata misalignment is.

Use `--exact` only to verify a download.

---

## Running the experiments

Once the corpus is built and calibrated:

```bash
# import the attack artifact and derive the adaptive variant
python3 load_poisonedrag_corpus.py \
  --src PoisonedRAG/results/adv_targeted_results/nq.json \
  --n-questions 100 --seed 42

# certify that the adaptive poison actually evades Ring 1
python3 verify_adaptive_poison.py --poison baseline/poison_adaptive_n100.jsonl

# end-to-end attack success, three arms
DEMO_MODE=2 python3 evaluation/run_experiments_3way.py

# the deterministic sweep, no model access required
DEMO_MODE=2 python3 rho_sweep.py --k 5
```

The evasion gate exits non-zero unless every malicious text falls below
$\vartheta_1$. No adaptive-attacker figure in the paper was produced without it
passing first, and we suggest keeping that discipline in any extension.
