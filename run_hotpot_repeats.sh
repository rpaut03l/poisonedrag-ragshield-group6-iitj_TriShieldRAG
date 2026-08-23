#!/usr/bin/env bash
# Two further HotpotQA trials, so the second corpus has error bars like NQ.
# NQ is already stable at n=4; HotpotQA is n=1 and its adaptive figure
# (85% vs 86% undefended) decides whether the defense is "useless" or
# "harmful" on that corpus. That is the number worth repeating.
set -uo pipefail
REPO="$HOME/poisonedrag-ragshield-group6-iitj_TriShieldRAG"
LOG="$REPO/logs_hprepeat_$(date +%Y%m%d_%H%M%S)"
cd "$REPO" || exit 1; source .venv/bin/activate || exit 1
mkdir -p "$LOG"; SUM="$LOG/SUMMARY.txt"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$SUM"; }

export DEMO_MODE=2
export SCALE_EMBEDDINGS_PATH=embeddings/hotpotqa_embeddings.npy
export SCALE_FAISS_INDEX_PATH=hotpotqa.index
export SCALE_META_PATH=embeddings/hotpotqa_embeddings.meta.json
export SCALE_TARGETS_PATH=evaluation/hotpotqa_targets.json

log "preflight (credit check):"
python3 backends_status.py 2>&1 | grep -E "LIVE|DOWN" | tee -a "$SUM"
python3 backends_status.py 2>&1 | grep -q "\[LIVE\] Claude" || { log "Claude DOWN -- aborting"; exit 1; }

# rename the existing single runs as trial 1
for arm in nonadaptive adaptive; do
  f="evaluation/results/asr_3way_hotpotqa_${arm}.json"
  [ -f "$f" ] && [ ! -f "evaluation/results/asr_3way_hp_${arm}_t1.json" ] && \
    cp "$f" "evaluation/results/asr_3way_hp_${arm}_t1.json"
done

for trial in 2 3; do
  for arm in nonadaptive adaptive; do
    src=$([ "$arm" = adaptive ] && echo hotpotqa_adaptive.jsonl || echo hotpotqa_poison.jsonl)
    cp "baseline/$src" baseline/poison_corpus.jsonl
    log "HotpotQA trial $trial / $arm"
    if python3 evaluation/run_experiments_3way.py > "$LOG/hp_${arm}_t${trial}.log" 2>&1; then
        cp evaluation/results/asr_results_3way.json \
           "evaluation/results/asr_3way_hp_${arm}_t${trial}.json"
        grep -E "^ASR " "$LOG/hp_${arm}_t${trial}.log" | tee -a "$SUM"
    else
        log "  FAILED"; tail -3 "$LOG/hp_${arm}_t${trial}.log" | tee -a "$SUM"
    fi
  done
done

log ""
log "=== HotpotQA across trials ==="
python3 - <<'PY' 2>&1 | tee -a "$SUM"
import json, glob, statistics as st
def fmt(v):
    if not v: return "--"
    if len(v)==1: return f"{v[0]}%"
    return f"{st.mean(v):.0f} +/- {st.stdev(v):.1f}"
print(f"{'arm':<16}{'no defense':>16}{'prior def':>16}{'TriShield':>16}  n")
print("-"*68)
for arm in ("nonadaptive","adaptive"):
    r=[]
    for f in sorted(glob.glob(f"evaluation/results/asr_3way_hp_{arm}_t*.json")):
        s=json.load(open(f))["summary"]
        r.append((s["asr_none_pct"],s["asr_paper_defenses_pct"],s["asr_full_pipeline_pct"]))
    if not r: print(f"{arm:<16}{'no runs':>48}"); continue
    c=list(zip(*r))
    print(f"{arm:<16}{fmt(list(c[0])):>16}{fmt(list(c[1])):>16}{fmt(list(c[2])):>16}  {len(r)}")
PY
log "=== done ==="
