#!/usr/bin/env bash
# run_msmarco.sh -- third corpus. GPU-bound, makes NO API calls, so it is
# safe to run alongside run_more_experiments.sh.
#
# MS-MARCO is web-passage text: noisier and more lexically varied than
# either NQ or HotpotQA. Eq. (5) says rho* = sigma_c/(sigma_p+sigma_c),
# so a corpus with MORE varied clean passages (smaller sigma_c) should
# give a LOWER rho*.
#
# PREDICTION, recorded before the run: rho*(MS-MARCO) < 0.214, i.e.
# below NQ. If it lands below NQ while HotpotQA landed above, Eq. (5)
# will have ordered three corpora correctly.
set -uo pipefail
REPO="$HOME/poisonedrag-ragshield-group6-iitj_TriShieldRAG"
LOG="$REPO/logs_msmarco_$(date +%Y%m%d_%H%M%S)"; EMB="$REPO/embeddings"
SH="$EMB/msmarco_shards"
cd "$REPO" || exit 1; source .venv/bin/activate || exit 1
mkdir -p "$LOG" "$SH"; SUM="$LOG/SUMMARY.txt"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$SUM"; }

log "=== MS-MARCO third-corpus evaluation ==="
log "PREDICTION (before the run): rho* < 0.214 (below NQ), because"
log "MS-MARCO web passages are more lexically varied than NQ's, so"
log "sigma_c is smaller and Eq. (5) gives a lower boundary."
log "Ordering predicted across all three: MS-MARCO < NQ < HotpotQA"
log ""

FREE=$(df -BG --output=avail "$REPO" | tail -1 | tr -dc 0-9)
log "free disk: ${FREE}G (need ~55G)"
[ "$FREE" -lt 55 ] && { log "INSUFFICIENT DISK -- aborting"; exit 1; }

if [ -f "$EMB/msmarco_embeddings.npy" ]; then
  log "stage 1-2: embeddings present, skipping"
else
  log "stage 1-2: download + embed (resumable)"
  python3 - <<'PY' 2>&1 | tee -a "$LOG/embed.log"
import json, numpy as np
from pathlib import Path
from datasets import load_dataset
from sentence_transformers import SentenceTransformer
SHARD=200_000; OUT=Path("embeddings"); SH=OUT/"msmarco_shards"; SH.mkdir(parents=True,exist_ok=True)
print("loading BeIR/msmarco corpus ...", flush=True)
ds=load_dataset("BeIR/msmarco","corpus",split="corpus")
N=len(ds); print(f"corpus size: {N:,}", flush=True)
mp=OUT/"msmarco_embeddings.meta.json"
if not mp.exists():
    print("writing metadata ...", flush=True)
    mp.write_text(json.dumps([{"id":ds[i]["_id"],"title":ds[i]["title"],
                               "text":ds[i]["text"],"source":"beir_msmarco"} for i in range(N)]))
model=SentenceTransformer("all-mpnet-base-v2", device="cuda")
for s in range(0,N,SHARD):
    p=SH/f"emb_{s:09d}.npy"
    if p.exists(): print(f"  shard {s:>9,} exists, skip", flush=True); continue
    e=min(s+SHARD,N)
    v=model.encode(ds[s:e]["text"], batch_size=256, convert_to_numpy=True,
                   normalize_embeddings=True, show_progress_bar=False)
    np.save(p, v.astype(np.float32)); print(f"  shard {s:>9,}-{e:>9,} done", flush=True)
print("merging ...", flush=True)
fs=sorted(SH.glob("emb_*.npy"))
tot=sum(np.load(f,mmap_mode="r").shape[0] for f in fs); assert tot==N, f"{tot}!={N}"
m=np.lib.format.open_memmap(OUT/"msmarco_embeddings.npy",mode="w+",dtype=np.float32,shape=(N,768))
o=0
for f in fs:
    a=np.load(f,mmap_mode="r"); m[o:o+a.shape[0]]=a; o+=a.shape[0]
m.flush(); print(f"wrote msmarco_embeddings.npy ({N:,} x 768)", flush=True)
PY
  [ "${PIPESTATUS[0]}" -ne 0 ] && { log "STAGE 1-2 FAILED"; exit 1; }
fi

if [ -f "$REPO/msmarco.index" ]; then
  log "stage 3: index present, skipping"
else
  log "stage 3: FAISS IVF index"
  python3 - <<'PY' 2>&1 | tee -a "$LOG/index.log"
import numpy as np, faiss, math
v=np.load("embeddings/msmarco_embeddings.npy",mmap_mode="r"); N,d=v.shape
nlist=int(4*math.sqrt(N)); print(f"N={N:,} nlist={nlist}",flush=True)
idx=faiss.IndexIVFFlat(faiss.IndexFlatIP(d),d,nlist,faiss.METRIC_INNER_PRODUCT)
tr=np.array(v[np.random.default_rng(0).choice(N,min(N,50*nlist),replace=False)])
idx.train(tr); del tr
for s in range(0,N,200_000):
    idx.add(np.array(v[s:s+200_000])); print(f"  added {min(s+200_000,N):,}/{N:,}",flush=True)
idx.nprobe=16; faiss.write_index(idx,"msmarco.index"); print("wrote msmarco.index",flush=True)
PY
  [ "${PIPESTATUS[0]}" -ne 0 ] && { log "STAGE 3 FAILED"; exit 1; }
fi

log "stage 4: poison import"
python3 load_poisonedrag_corpus.py \
  --src "$HOME/PoisonedRAG/results/adv_targeted_results/msmarco.json" \
  --n-questions 100 --seed 42 \
  --targets-out evaluation/msmarco_targets.json \
  --poison-out baseline/msmarco_poison.jsonl 2>&1 | tail -5 | tee -a "$SUM"

python3 - <<'PY' 2>&1 | tee -a "$SUM"
import json, re
from pathlib import Path
src=[json.loads(l) for l in Path("baseline/msmarco_poison.jsonl").read_text().splitlines() if l.strip()]
out=[]
for d in src:
    q=d["target_q"]; t=d["text"]
    a=t[len(q):].strip() if t.startswith(q) else t
    w=re.sub(r"[^A-Za-z0-9 ]"," ",a).split()
    out.append({**d,"id":d["id"].replace("poison_","adaptive_"),"text":a,
                "title":" ".join(w[:6]) if w else "Reference note"})
Path("baseline/msmarco_adaptive.jsonl").write_text("\n".join(json.dumps(d) for d in out)+"\n")
print(f"wrote {len(out)} adaptive MS-MARCO poison docs")
PY

log "stage 5: certify evasion"
python3 verify_adaptive_poison.py --poison baseline/msmarco_adaptive.jsonl 2>&1 | tail -8 | tee -a "$SUM"

log "stage 6: rho sweep"
export SCALE_EMBEDDINGS_PATH=embeddings/msmarco_embeddings.npy
export SCALE_FAISS_INDEX_PATH=msmarco.index
export SCALE_META_PATH=embeddings/msmarco_embeddings.meta.json
export SCALE_TARGETS_PATH=evaluation/msmarco_targets.json
export DEMO_MODE=2
python3 rho_sweep.py --k 5 --poison baseline/msmarco_adaptive.jsonl \
  --targets evaluation/msmarco_targets.json \
  --out evaluation/results/rho_sweep_msmarco.json 2>&1 | tee -a "$SUM"

log ""
log "=== three-corpus comparison ==="
python3 - <<'PY' 2>&1 | tee -a "$SUM"
import json
def cross(rows):
    p=[(r["rho"],r["consistency_poison"],r["consistency_clean"]) for r in rows
       if r["consistency_poison"] is not None and r["consistency_clean"] is not None]
    for (r1,p1,c1),(r2,p2,c2) in zip(p,p[1:]):
        g1,g2=c1-p1,c2-p2
        if g1>0>=g2: return r1+(r2-r1)*g1/(g1-g2)
rows=[]
for n,f in (("MS-MARCO","evaluation/results/rho_sweep_msmarco.json"),
            ("NQ","evaluation/results/rho_sweep_n100.json"),
            ("HotpotQA","evaluation/results/rho_sweep_hotpotqa.json")):
    try:
        r=cross(json.load(open(f))["rows"]); rows.append((n,r))
        print(f"  {n:10} rho* = {r:.3f}   sigma_p/sigma_c = {(1-r)/r:.2f}")
    except Exception as e: print(f"  {n:10} unavailable ({e})")
if len(rows)==3:
    order=[n for n,_ in sorted(rows,key=lambda x:x[1])]
    print(f"\n  observed ordering : {' < '.join(order)}")
    print(f"  predicted ordering: MS-MARCO < NQ < HotpotQA")
    print(f"  {'MATCH' if order==['MS-MARCO','NQ','HotpotQA'] else 'DOES NOT MATCH'}")
PY
log "=== done ==="
