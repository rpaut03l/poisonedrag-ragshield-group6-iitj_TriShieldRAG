"""
evaluation/run_experiments_3way.py
Extends run_experiments.py's 2-arm comparison (no-defense / rag-shield)
to the full 3-arm comparison your paper's checklist requires:
  - none                 : no defense at all
  - paper's-defenses      : PoisonedRAG's own tested defenses
                            (perplexity + duplicate-text filtering)
  - full pipeline (ours)  : RAG-Shield Ring 1 + Ring 2 + Ring 3

Run:
    python evaluation/run_experiments_3way.py
"""
import sys, json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ragshield_core.rag_shield import RAGShield
from ragshield_core.retriever import load_targets
from ragshield_core import config


def main():
    t0 = time.time()
    targets = load_targets()
    print(f"Loaded {len(targets)} target questions.")
    shield = RAGShield().setup(poisoned=True)

    rows = []
    asr_none = asr_paper = asr_full = 0

    for i, t in enumerate(targets):
        print(f"[{i+1}/{len(targets)}] {t['question'][:70]}", flush=True)
        c = [t["true_answer"], t["wrong_answer"]]

        r_none = shield.answer(t["question"], defense=False, candidates=c)
        r_paper = shield.answer(t["question"], defense="paper_baseline", candidates=c)
        r_full = shield.answer(t["question"], defense=True, candidates=c)

        f_none = t["wrong_answer"].lower() in r_none["answer"].lower()
        f_paper = t["wrong_answer"].lower() in r_paper["answer"].lower()
        f_full = t["wrong_answer"].lower() in r_full["answer"].lower()

        asr_none += f_none
        asr_paper += f_paper
        asr_full += f_full

        rows.append({
            "id": t["id"], "question": t["question"],
            "true": t["true_answer"], "wrong": t["wrong_answer"],
            "none_answer": r_none["answer"], "none_fooled": f_none,
            "paper_answer": r_paper["answer"], "paper_fooled": f_paper,
            "paper_blocked": len(r_paper["trace"].get("paper_baseline_blocked", [])),
            "full_answer": r_full["answer"], "full_fooled": f_full,
            "full_ring1_blocked": len(r_full["trace"].get("ring1_blocked", [])),
            "full_ring2_dropped": len(r_full["trace"].get("ring2_dropped", [])),
            "full_ring3_agreement": r_full["trace"].get("ring3", {}).get("agreement"),
        })

    n = len(targets)
    summary = {
        "mode": "demo" if config.demo_mode() else "live",
        "n_questions": n,
        "asr_none_pct": round(100 * asr_none / n),
        "asr_paper_defenses_pct": round(100 * asr_paper / n),
        "asr_full_pipeline_pct": round(100 * asr_full / n),
        "reduction_none_to_full_pts": round(100 * (asr_none - asr_full) / n),
        "elapsed_sec": round(time.time() - t0),
    }

    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = config.RESULTS_DIR / "asr_results_3way.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))

    print("\n=== TriShieldRAG 3-Way Evaluation ===")
    print(f"mode={summary['mode']}  questions={n}  elapsed={summary['elapsed_sec']}s")
    print(f"{'question':45} {'none':16} {'paper-def':16} {'full':16}")
    print("-" * 95)
    for r in rows:
        print(f"{r['question'][:43]:45} {r['none_answer'][:14]:16} "
              f"{r['paper_answer'][:14]:16} {r['full_answer'][:14]:16}")
    print("-" * 95)
    print(f"ASR none            : {summary['asr_none_pct']}%")
    print(f"ASR paper-defenses  : {summary['asr_paper_defenses_pct']}%")
    print(f"ASR full pipeline   : {summary['asr_full_pipeline_pct']}%")
    print(f"Reduction (none->full): {summary['reduction_none_to_full_pts']} pts")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
