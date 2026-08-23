#!/usr/bin/env bash
#
# run_hotpotqa.sh -- second-dataset evaluation for TriShieldRAG.
#
# WHY: Eq. (5) states rho* ~= sigma_c / (sigma_p + sigma_c), where
# sigma_c is the mutual lexical overlap of clean corpus passages. That
# is a property of the CORPUS, not of the attack. The equation therefore
# makes a falsifiable prediction: a corpus whose clean passages are more
# lexically uniform than NQ's should show a DIFFERENT rho*.
#
# HotpotQA is multi-hop and its passages are Wikipedia intro paragraphs,
# which are more formulaic than NQ's mixed passages. We predict
# sigma_c(HotpotQA) > sigma_c(NQ), hence rho*(HotpotQA) > 0.21.
# Recording the prediction BEFORE the run is the point.
#
# STAGES (each checkpointed; re-running skips completed stages):
#   1. download BeIR/hotpotqa corpus            ~10 min
#   2. embed 5.2M passages, sharded             ~2-3 h on RTX 6000
#   3. build FAISS IVF index                    ~30 min
#   4. import PoisonedRAG hotpotqa poison       ~1 min
#   5. certify adaptive evasion                 ~2 min
#   6. deterministic rho sweep (NO LLM calls)   ~5 min
#
# Stage 6 is the actual experiment. Stages 1-3 are infrastructure.
#
# Usage:
#   chmod +x run_hotpotqa.sh
#   screen -S hotpot
#   ./run_hotpotqa.sh
#   # Ctrl-A then D to detach;  screen -r hotpot  to return
set -uo pipefail

REPO="$HOME/poisonedrag-ragshield-group6-iitj_TriShieldRAG"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG="$REPO/logs_hotpotqa_$STAMP"
EMB="$REPO/embeddings"
SHARDS="$EMB/hotpot_shards"

cd "$REPO" || { echo "repo missing"; exit 1; }
source .venv/bin/activate || { echo "venv failed"; exit 1; }
mkdir -p "$LOG" "$EMB" "$SHARDS"
SUM="$LOG/SUMMARY.txt"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$SUM"; }

log "=== HotpotQA second-dataset evaluation ==="
log "PREDICTION (recorded before the run): rho* > 0.21, because"
log "HotpotQA passages are Wikipedia intros and more lexically uniform"
log "than NQ's, so sigma_c is larger and Eq. (5) gives a higher rho*."
log ""

# ---------- stage 1+2: corpus + embeddings (sharded, resumable) ----------
if [ -f "$EMB/hotpotqa_embeddings.npy" ] && [ -f "$EMB/hotpotqa_embeddings.meta.json" ]; then
    log "stage 1-2: embeddings already present, skipping"
else
    log "stage 1-2: downloading + embedding (resumable, shards in $SHARDS)"
    python3 - <<'PY' 2>&1 | tee -a "$LOG/embed.log"
import json, os, numpy as np
from pathlib import Path
from datasets import load_dataset
from sentence_transformers import SentenceTransformer

SHARD = 200_000
OUT   = Path("embeddings"); SH = OUT/"hotpot_shards"; SH.mkdir(parents=True, exist_ok=True)

print("loading BeIR/hotpotqa corpus ...", flush=True)
ds = load_dataset("BeIR/hotpotqa", "corpus", split="corpus")
N = len(ds); print(f"corpus size: {N:,}", flush=True)

# metadata first: cheap, and lets a later stage proceed if embedding dies
meta_path = OUT/"hotpotqa_embeddings.meta.json"
if not meta_path.exists():
    print("writing metadata ...", flush=True)
    meta = [{"id": ds[i]["_id"], "title": ds[i]["title"],
             "text": ds[i]["text"], "source": "beir_hotpotqa"}
            for i in range(N)]
    meta_path.write_text(json.dumps(meta))
    del meta
    print(f"wrote {meta_path}", flush=True)

model = SentenceTransformer("all-mpnet-base-v2", device="cuda")
for start in range(0, N, SHARD):
    p = SH/f"emb_{start:09d}.npy"
    if p.exists():
        print(f"  shard {start:>9,} exists, skip", flush=True); continue
    end = min(start+SHARD, N)
    texts = ds[start:end]["text"]          # embeddings built from TEXT only,
                                           # matching the NQ build exactly
    v = model.encode(texts, batch_size=256, convert_to_numpy=True,
                     normalize_embeddings=True, show_progress_bar=False)
    np.save(p, v.astype(np.float32))
    print(f"  shard {start:>9,}-{end:>9,} done", flush=True)

print("merging shards ...", flush=True)
files = sorted(SH.glob("emb_*.npy"))
total = sum(np.load(f, mmap_mode="r").shape[0] for f in files)
assert total == N, f"shard total {total} != corpus {N}"
merged = np.lib.format.open_memmap(OUT/"hotpotqa_embeddings.npy", mode="w+",
                                   dtype=np.float32, shape=(N, 768))
off = 0
for f in files:
    a = np.load(f, mmap_mode="r"); merged[off:off+a.shape[0]] = a; off += a.shape[0]
merged.flush()
print(f"wrote embeddings/hotpotqa_embeddings.npy  ({N:,} x 768)", flush=True)
PY
    [ "${PIPESTATUS[0]}" -ne 0 ] && { log "STAGE 1-2 FAILED -- see $LOG/embed.log"; exit 1; }
fi

# ---------- stage 3: FAISS index ----------
if [ -f "$REPO/hotpotqa.index" ]; then
    log "stage 3: index present, skipping"
else
    log "stage 3: building FAISS IVF index"
    python3 - <<'PY' 2>&1 | tee -a "$LOG/index.log"
import numpy as np, faiss, math
v = np.load("embeddings/hotpotqa_embeddings.npy", mmap_mode="r")
N, d = v.shape
nlist = int(4*math.sqrt(N))            # same heuristic used for NQ
print(f"N={N:,} d={d} nlist={nlist}", flush=True)
quant = faiss.IndexFlatIP(d)
idx = faiss.IndexIVFFlat(quant, d, nlist, faiss.METRIC_INNER_PRODUCT)
train = np.array(v[np.random.default_rng(0).choice(N, min(N, 50*nlist), replace=False)])
idx.train(train); del train
for s in range(0, N, 200_000):
    idx.add(np.array(v[s:s+200_000]))
    print(f"  added {min(s+200_000,N):,}/{N:,}", flush=True)
idx.nprobe = 16
faiss.write_index(idx, "hotpotqa.index")
print("wrote hotpotqa.index", flush=True)
PY
    [ "${PIPESTATUS[0]}" -ne 0 ] && { log "STAGE 3 FAILED -- see $LOG/index.log"; exit 1; }
fi

# ---------- stage 4: poison from PoisonedRAG's hotpotqa artifact ----------
log "stage 4: importing PoisonedRAG HotpotQA poison"
python3 load_poisonedrag_corpus.py \
  --src "$HOME/PoisonedRAG/results/adv_targeted_results/hotpotqa.json" \
  --n-questions 100 --seed 42 \
  --targets-out evaluation/hotpotqa_targets.json \
  --poison-out baseline/hotpotqa_poison.jsonl 2>&1 | tail -6 | tee -a "$SUM"

python3 - <<'PY' 2>&1 | tee -a "$SUM"
import json, re
from pathlib import Path
src=[json.loads(l) for l in Path("baseline/hotpotqa_poison.jsonl").read_text().splitlines() if l.strip()]
out=[]
for d in src:
    q=d["target_q"]; t=d["text"]
    adapt=t[len(q):].strip() if t.startswith(q) else t
    w=re.sub(r"[^A-Za-z0-9 ]"," ",adapt).split()
    out.append({**d,"id":d["id"].replace("poison_","adaptive_"),"text":adapt,
                "title":" ".join(w[:6]) if w else "Reference note"})
Path("baseline/hotpotqa_adaptive.jsonl").write_text("\n".join(json.dumps(d) for d in out)+"\n")
print(f"wrote {len(out)} adaptive HotpotQA poison docs")
PY

# ---------- stage 5: certify evasion ----------
log "stage 5: certifying adaptive evasion"
python3 verify_adaptive_poison.py --poison baseline/hotpotqa_adaptive.jsonl 2>&1 \
  | tail -8 | tee -a "$SUM"

# ---------- stage 6: THE EXPERIMENT ----------
log ""
log "stage 6: deterministic rho sweep on HotpotQA"
export SCALE_EMBEDDINGS_PATH=embeddings/hotpotqa_embeddings.npy
export SCALE_FAISS_INDEX_PATH=hotpotqa.index
export SCALE_META_PATH=embeddings/hotpotqa_embeddings.meta.json
export SCALE_TARGETS_PATH=evaluation/hotpotqa_targets.json
export DEMO_MODE=2

python3 rho_sweep.py --k 5 \
  --poison baseline/hotpotqa_adaptive.jsonl \
  --targets evaluation/hotpotqa_targets.json \
  --out evaluation/results/rho_sweep_hotpotqa.json 2>&1 | tee -a "$SUM"

# ---------- comparison ----------
log ""
log "=== NQ vs HotpotQA ==="
python3 - <<'PY' 2>&1 | tee -a "$SUM"
import json
def cross(rows):
    p=[(r["rho"],r["consistency_poison"],r["consistency_clean"]) for r in rows
       if r["consistency_poison"] is not None and r["consistency_clean"] is not None]
    for (r1,p1,c1),(r2,p2,c2) in zip(p,p[1:]):
        g1,g2=c1-p1,c2-p2
        if g1>0>=g2: return r1+(r2-r1)*g1/(g1-g2)
for name,f in (("NQ (n=100)","evaluation/results/rho_sweep_n100.json"),
               ("HotpotQA (n=100)","evaluation/results/rho_sweep_hotpotqa.json")):
    try:
        r=cross(json.load(open(f))["rows"])
        print(f"  {name:20} rho* = {r:.3f}   implied sigma_p/sigma_c = {(1-r)/r:.2f}")
    except Exception as e:
        print(f"  {name:20} unavailable ({e})")
print()
print("Prediction was rho*(HotpotQA) > 0.21. Paste this back to update the paper.")
PY

log ""
log "=== done ==="
log "Summary: $SUM"
