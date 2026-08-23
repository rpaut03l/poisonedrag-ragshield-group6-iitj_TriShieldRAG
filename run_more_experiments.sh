#!/usr/bin/env bash
# run_more_experiments.sh -- API-bound work. Safe to run alongside
# run_msmarco.sh, which is GPU-bound and makes no API calls.
#
# Two jobs, sequential inside this screen so they do not contend on API
# rate limits with each other:
#   A. HotpotQA end-to-end ASR   (rho* is measured; attack success is not)
#   B. two further NQ trials     (takes 3 trials -> 5, tightening error bars)
set -uo pipefail
REPO="$HOME/poisonedrag-ragshield-group6-iitj_TriShieldRAG"
LOG="$REPO/logs_more_$(date +%Y%m%d_%H%M%S)"
cd "$REPO" || exit 1; source .venv/bin/activate || exit 1
mkdir -p "$LOG"; SUM="$LOG/SUMMARY.txt"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$SUM"; }
export DEMO_MODE=2

log "=== additional experiments ==="
log "preflight:"
python3 backends_status.py 2>&1 | grep -E "LIVE|DOWN" | tee -a "$SUM"
[ -f "$REPO/hotpotqa.index" ] || { log "hotpotqa.index missing -- run run_hotpotqa.sh first"; exit 1; }

# ---------- A. HotpotQA end-to-end ASR ----------
log ""
log "--- A: HotpotQA end-to-end attack success ---"
export SCALE_EMBEDDINGS_PATH=embeddings/hotpotqa_embeddings.npy
export SCALE_FAISS_INDEX_PATH=hotpotqa.index
export SCALE_META_PATH=embeddings/hotpotqa_embeddings.meta.json
export SCALE_TARGETS_PATH=evaluation/hotpotqa_targets.json

for arm in nonadaptive adaptive; do
  src=$([ "$arm" = adaptive ] && echo hotpotqa_adaptive.jsonl || echo hotpotqa_poison.jsonl)
  cp "baseline/$src" baseline/poison_corpus.jsonl
  log "  HotpotQA / $arm"
  t0=$(date +%s)
  if python3 evaluation/run_experiments_3way.py > "$LOG/hotpot_$arm.log" 2>&1; then
      cp evaluation/results/asr_results_3way.json \
         "evaluation/results/asr_3way_hotpotqa_${arm}.json"
      grep -E "^ASR |^Reduction" "$LOG/hotpot_$arm.log" | tee -a "$SUM"
  else
      log "    FAILED -- see $LOG/hotpot_$arm.log"; tail -4 "$LOG/hotpot_$arm.log" | tee -a "$SUM"
  fi
  log "    took $(( ($(date +%s)-t0)/60 ))m"
done

# ---------- B. two further NQ trials ----------
log ""
log "--- B: NQ trials 4 and 5 ---"
export SCALE_EMBEDDINGS_PATH=embeddings/nq_embeddings.npy
export SCALE_FAISS_INDEX_PATH=ragshield_2m.index
export SCALE_META_PATH=embeddings/nq_embeddings.meta.json
export SCALE_TARGETS_PATH=evaluation/scale_target_questions_n100.json

for trial in 4 5; do
  for arm in nonadaptive adaptive; do
    src=$([ "$arm" = adaptive ] && echo poison_adaptive_n100.jsonl || echo poison_corpus_n100.jsonl)
    cp "baseline/$src" baseline/poison_corpus.jsonl
    log "  NQ trial $trial / $arm"
    if python3 evaluation/run_experiments_3way.py > "$LOG/nq_${arm}_t${trial}.log" 2>&1; then
        cp evaluation/results/asr_results_3way.json \
           "evaluation/results/asr_3way_${arm}_t${trial}.json"
        grep -E "^ASR " "$LOG/nq_${arm}_t${trial}.log" | tee -a "$SUM"
    else
        log "    FAILED"; tail -4 "$LOG/nq_${arm}_t${trial}.log" | tee -a "$SUM"
    fi
  done
done

# ---------- aggregate ----------
log ""
log "=== aggregate over all completed trials ==="
python3 - <<'PY' 2>&1 | tee -a "$SUM"
import json, glob, statistics as st
def agg(pat):
    r=[]
    for f in sorted(glob.glob(pat)):
        s=json.load(open(f))["summary"]
        r.append((s["asr_none_pct"],s["asr_paper_defenses_pct"],s["asr_full_pipeline_pct"]))
    return r
def fmt(v):
    if not v: return "--"
    if len(v)==1: return f"{v[0]}%"
    return f"{st.mean(v):.0f} +/- {st.stdev(v):.1f}"
print(f"{'corpus / arm':<26}{'no defense':>16}{'prior def':>16}{'TriShield':>16}  n")
print("-"*78)
for label,pat in (("NQ nonadaptive","evaluation/results/asr_3way_nonadaptive_t*.json"),
                  ("NQ adaptive","evaluation/results/asr_3way_adaptive_t*.json"),
                  ("HotpotQA nonadaptive","evaluation/results/asr_3way_hotpotqa_nonadaptive.json"),
                  ("HotpotQA adaptive","evaluation/results/asr_3way_hotpotqa_adaptive.json")):
    r=agg(pat)
    if not r: print(f"{label:<26}{'no runs':>48}"); continue
    c=list(zip(*r))
    print(f"{label:<26}{fmt(list(c[0])):>16}{fmt(list(c[1])):>16}{fmt(list(c[2])):>16}  {len(r)}")
print("\nPaste this table back to update the papers.")
PY
log "=== done ==="
