"""
rho_sweep_llm.py -- Phase 2 of the rho sweep: does END-TO-END ASR
follow the consistency-inversion boundary measured in Phase 1?

Phase 1 (rho_sweep.py) showed Ring 2's consistency signal inverts at
rho* ~= 0.27. That is a mechanism. This script asks whether the
OUTCOME tracks it: at each rho we run the real Ring 2 -> Ring 3 path
with the live panel and measure attack success.

If ASR stays low below rho* and rises above it, mechanism and effect
are linked and the paper has a causal account rather than two
separate observations.

Design notes:
  * Poison is the ADAPTIVE corpus by default, i.e. Ring 1 is bypassed
    (certified by verify_adaptive_poison.py). That is the regime where
    Rings 2 and 3 actually have to do the work; with non-adaptive
    poison Ring 1 blocks everything at every rho and the sweep is
    uninformative. Use --control to add a non-adaptive row for contrast.
  * The top-k is CONSTRUCTED to contain exactly n_poison poison docs,
    so rho is an independent variable rather than whatever FAISS
    happens to return.
  * We record what Ring 3's bounded re-retrieval actually dropped
    (clean vs poison), since Finding 3 traces the failure to
    re-retrieval discarding the clean evidence.

Usage:
    python3 rho_sweep_llm.py                    # adaptive, rho .1-.5
    python3 rho_sweep_llm.py --rhos 0.2,0.4,0.6,0.8
    python3 rho_sweep_llm.py --control          # + non-adaptive row
"""
import argparse, json, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("DEMO_MODE", "2")

from ragshield_core.ring2_retrieval import RetrievalScorer          # noqa: E402
from ragshield_core.ring3_consensus import CrossLLMConsensus        # noqa: E402
from ragshield_core.llm_backends import make_consensus_panel        # noqa: E402
from ragshield_core.retriever import Retriever                      # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent / "evaluation"))


def _load_scorer():
    """Reuse the refusal-aware ASR scorer from the 3-way harness."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "m3", str(Path(__file__).resolve().parent
                 / "evaluation" / "run_experiments_3way.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.attack_succeeded


def load_jsonl(p: Path):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poison", default="baseline/poison_adaptive.jsonl")
    ap.add_argument("--control-poison", default="baseline/poison_corpus.nonadaptive.jsonl")
    ap.add_argument("--targets", default="evaluation/scale_target_questions.json")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--rhos", default="0.0,0.2,0.4,0.6,0.8,1.0")
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--out", default="evaluation/results/rho_sweep_llm.json")
    args = ap.parse_args()

    attack_succeeded = _load_scorer()
    targets = json.loads(Path(args.targets).read_text())
    rhos = [float(x) for x in args.rhos.split(",")]

    def by_question(path):
        d = {}
        for p in load_jsonl(Path(path)):
            d.setdefault(p["target_q"], []).append(p)
        return d

    poison_by_q = by_question(args.poison)
    control_by_q = by_question(args.control_poison) if args.control else {}

    print("Loading corpus...")
    r = Retriever(backend="scale").load_kb()
    scorer = RetrievalScorer()
    panel = make_consensus_panel()
    consensus = CrossLLMConsensus(panel)
    print(f"Panel: {[l.name for l in panel]}\n")

    # cache clean retrievals so we do it once per question, not per rho
    clean_cache = {}
    for t in targets:
        q = t["question"]
        clean_cache[q] = [d for d in r.retrieve(q, args.k * 4)
                          if d.get("source") != "POISONED"][: args.k]

    def run_arm(pois_by_q, label):
        rows = []
        for rho in rhos:
            n_p = int(round(rho * args.k))
            fooled = total = 0
            rr_fired = rr_dropped_clean = 0
            agreements = []
            for t in targets:
                q, wrong = t["question"], t["wrong_answer"]
                pois = pois_by_q.get(q, [])
                clean = clean_cache.get(q, [])
                if len(pois) < n_p or len(clean) < args.k - n_p:
                    continue
                topk = [dict(p) for p in pois[:n_p]] + \
                       [dict(c) for c in clean[: args.k - n_p]]
                for d in topk:
                    d.setdefault("score",
                                 0.80 if d.get("source") == "POISONED" else 0.72)
                kept, _ = scorer.filter(topk)
                if not kept:
                    kept = topk

                def reretrieve(suspects, _kept=kept):
                    ids = {s.get("id") for s in suspects}
                    return [d for d in _kept if d.get("id") not in ids]

                v = consensus.run(q, kept, [t["true_answer"], wrong], reretrieve)
                agreements.append(v.get("agreement", 0))
                if v.get("reretrieved"):
                    rr_fired += 1
                    dropped = set(v.get("dropped_suspects") or [])
                    if any(d.get("id") in dropped
                           and d.get("source") != "POISONED" for d in kept):
                        rr_dropped_clean += 1
                ok, _why = attack_succeeded(v["answer"], wrong)
                fooled += ok
                total += 1

            asr = round(100 * fooled / total) if total else None
            mean_ag = round(sum(agreements) / len(agreements), 2) if agreements else None
            rows.append({"rho": rho, "n_poison": n_p, "n_questions": total,
                         "asr_pct": asr, "mean_agreement": mean_ag,
                         "reretrieval_fired": rr_fired,
                         "reretrieval_dropped_clean": rr_dropped_clean})
            print(f"{label:>12} rho={rho:<5} n_p={n_p}  ASR={asr}%  "
                  f"mean_agree={mean_ag}  re-retrieve={rr_fired}"
                  f" (dropped clean: {rr_dropped_clean})", flush=True)
        return rows

    t0 = time.time()
    print(f"{'arm':>12} {'sweep':<38}")
    print("-" * 78)
    adaptive_rows = run_arm(poison_by_q, "adaptive")
    control_rows = run_arm(control_by_q, "non-adapt") if args.control else []

    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "k": args.k, "poison": args.poison,
        "phase1_measured_boundary": 0.27,
        "proposition_1_predicted_boundary": 0.5,
        "adaptive": adaptive_rows, "non_adaptive_control": control_rows,
        "elapsed_sec": round(time.time() - t0),
    }, indent=2))
    print(f"\nWrote {out}  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
