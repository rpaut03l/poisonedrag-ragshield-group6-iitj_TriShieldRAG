#!/usr/bin/env bash
#
# run_overnight.sh -- repeated-trial evaluation for TriShieldRAG.
#
# Runs the three-way harness N times per attacker arm so that every
# number in the paper can be reported as mean +/- std rather than as a
# single draw from a stochastic panel. The N=10 pilot varied by 15
# points across identical inputs, which is why this matters.
#
# Designed to survive a disconnected SSH session. Everything is logged;
# each run's result JSON is preserved separately; a summary is written
# at the end and also after every individual run, so a partial run is
# still usable.
#
# Usage:
#   chmod +x run_overnight.sh
#   screen -S trials
#   ./run_overnight.sh
#   # detach with Ctrl-A then D
#   # reattach later with:  screen -r trials
#
# Or without screen:
#   nohup ./run_overnight.sh > /dev/null 2>&1 &

set -uo pipefail          # NOT -e: one failed run must not kill the batch

TRIALS="${TRIALS:-3}"
REPO="$HOME/poisonedrag-ragshield-group6-iitj_TriShieldRAG"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOGDIR="$REPO/logs_trials_$STAMP"
RESULTS="$REPO/evaluation/results"
SUMMARY="$LOGDIR/SUMMARY.txt"

cd "$REPO" || { echo "repo not found: $REPO"; exit 1; }
# shellcheck disable=SC1091
source .venv/bin/activate || { echo "venv activation failed"; exit 1; }

export SCALE_TARGETS_PATH=evaluation/scale_target_questions_n100.json
export DEMO_MODE=2

mkdir -p "$LOGDIR" "$RESULTS"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$SUMMARY"; }

# ---- preflight: fail loudly now rather than silently in three hours ----
log "=== preflight ==="
python3 - <<'PY' 2>&1 | tee -a "$SUMMARY"
import os, sys, json
from pathlib import Path
ok = True
p = os.getenv("SCALE_TARGETS_PATH", "")
n = len(json.loads(Path(p).read_text())) if Path(p).exists() else 0
print(f"  targets file      : {p}")
print(f"  targets loaded    : {n} (want 100)")
ok &= (n == 100)
for f in ["baseline/poison_corpus_n100.jsonl", "baseline/poison_adaptive_n100.jsonl"]:
    c = sum(1 for _ in open(f)) if Path(f).exists() else 0
    print(f"  {f:42} {c} docs (want 500)")
    ok &= (c == 500)
for f in ["embeddings/nq_embeddings.npy", "ragshield_2m.index"]:
    e = Path(f).exists()
    print(f"  {f:42} {'present' if e else 'MISSING'}")
    ok &= e
sys.exit(0 if ok else 1)
PY
if [ "${PIPESTATUS[0]}" -ne 0 ]; then
    log "PREFLIGHT FAILED -- nothing was run. Fix the above and retry."
    exit 1
fi

log "backends:"
python3 backends_status.py 2>&1 | grep -E "LIVE|DOWN" | tee -a "$SUMMARY"

log ""
log "=== starting $TRIALS trials x 2 arms ==="
log "logs     -> $LOGDIR"
log "results  -> $RESULTS/asr_3way_<arm>_t<n>.json"
log ""

START=$(date +%s)
for trial in $(seq 1 "$TRIALS"); do
  for arm in nonadaptive adaptive; do
    if [ "$arm" = "adaptive" ]; then
      src="poison_adaptive_n100.jsonl"
    else
      src="poison_corpus_n100.jsonl"
    fi
    cp "baseline/$src" baseline/poison_corpus.jsonl

    RUNLOG="$LOGDIR/${arm}_t${trial}.log"
    log "--- trial $trial / $arm  (started) ---"
    t0=$(date +%s)

    if python3 evaluation/run_experiments_3way.py > "$RUNLOG" 2>&1; then
        cp evaluation/results/asr_results_3way.json \
           "$RESULTS/asr_3way_${arm}_t${trial}.json" 2>/dev/null
        grep -E "^ASR |^Reduction" "$RUNLOG" | tee -a "$SUMMARY"
    else
        log "    RUN FAILED -- see $RUNLOG"
        tail -5 "$RUNLOG" | tee -a "$SUMMARY"
    fi

    t1=$(date +%s)
    log "    took $(( (t1-t0)/60 ))m $(( (t1-t0)%60 ))s"
    log ""
  done
done

# ---- aggregate whatever completed ----
log "=== aggregate ==="
python3 - <<'PY' 2>&1 | tee -a "$SUMMARY"
import json, glob, statistics as st

def agg(arm):
    rows = []
    for f in sorted(glob.glob(f"evaluation/results/asr_3way_{arm}_t*.json")):
        s = json.load(open(f))["summary"]
        rows.append((s["asr_none_pct"], s["asr_paper_defenses_pct"],
                     s["asr_full_pipeline_pct"]))
    return rows

def fmt(vals):
    if not vals: return "--"
    if len(vals) == 1: return f"{vals[0]}%"
    return f"{st.mean(vals):.0f}% +/- {st.stdev(vals):.1f}"

print(f"{'arm':<14}{'no defense':>18}{'prior defenses':>18}{'TriShieldRAG':>18}  n")
print("-" * 72)
for arm in ("nonadaptive", "adaptive"):
    r = agg(arm)
    if not r:
        print(f"{arm:<14}{'no completed runs':>54}")
        continue
    cols = list(zip(*r))
    print(f"{arm:<14}{fmt(list(cols[0])):>18}{fmt(list(cols[1])):>18}"
          f"{fmt(list(cols[2])):>18}  {len(r)}")
print()
print("Paste this table back into the conversation to update the paper.")
PY

END=$(date +%s)
log ""
log "=== done in $(( (END-START)/60 )) minutes ==="
log "Summary written to: $SUMMARY"
