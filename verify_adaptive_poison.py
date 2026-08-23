"""
verify_adaptive_poison.py -- prove poison is ACTUALLY adaptive before
any ASR number is computed from it.

An "adaptive attacker" claim is only meaningful if the poison
demonstrably evades the defense's detectors. This script scores every
candidate poison document with Ring 1's EXACT production scorer
(ragshield_core.ring1_ingest.IngestGuard) and reports, per document:

    p(d)   perplexity / repetition proxy      Eq. (2)
    pa(d)  pattern: short-q, verbatim-q, boilerplate   Eq. (3)
    o(d)   embedding outlier vs KB centroid   Eq. (4)
    score  max(p, pa, 0.7o + 0.3 max(p,pa))   Eq. (5)
    block  score >= theta_1 = 0.5             Eq. (6)

Exit codes:
    0  every document evades Ring 1 (score < theta_1)  -> genuinely adaptive
    1  one or more documents would be blocked          -> NOT adaptive

Use --require-all-evade (default) to enforce the gate. Use
--report-only to inspect scores without failing, e.g. while iterating
on candidate poison.

The point of the gate is honesty: if the adaptive poison does not
actually evade Ring 1, then running the pipeline and reporting the
resulting ASR as an "adaptive attacker" result would be false. Better
to fail loudly here.

Usage:
    python3 verify_adaptive_poison.py --poison baseline/poison_adaptive.jsonl
    python3 verify_adaptive_poison.py --poison baseline/poison_corpus.jsonl --report-only
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ragshield_core.ring1_ingest import IngestGuard   # noqa: E402


def load_poison(path: Path) -> list[dict]:
    txt = path.read_text().strip()
    if not txt:
        sys.exit(f"ERROR: {path} is empty")
    if txt.lstrip().startswith("["):
        return json.loads(txt)
    return [json.loads(l) for l in txt.splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poison", required=True)
    ap.add_argument("--threshold", type=float, default=0.5,
                    help="Ring 1 block threshold theta_1 (paper: 0.5)")
    ap.add_argument("--report-only", action="store_true",
                    help="print scores but always exit 0")
    ap.add_argument("--verbose", action="store_true",
                    help="show a text excerpt for each document")
    args = ap.parse_args()

    docs = load_poison(Path(args.poison))
    guard = IngestGuard(threshold=args.threshold)

    print(f"Scoring {len(docs)} poison document(s) from {args.poison}")
    print(f"Ring 1 threshold theta_1 = {args.threshold}\n")
    print(f"{'doc id':<28} {'p':>6} {'pa':>6} {'o':>6} {'score':>7}  verdict")
    print("-" * 74)

    blocked, evaded, by_q = [], [], {}
    for d in docs:
        # Ring 1 in deployment sees only the incoming query, so the
        # verbatim-question check is evaluated against this document's
        # own target question -- the most FAVOURABLE case for the
        # detector. If poison evades even here, it evades in the
        # pipeline too.
        q = d.get("target_q") or d.get("question") or ""
        v = guard.inspect(d, [q] if q else None)
        row = (d.get("id", "?"), v["perplexity"], v["pattern"],
               v["outlier"], v["score"], v["blocked"])
        (blocked if v["blocked"] else evaded).append(row)
        by_q.setdefault(q, []).append(v["blocked"])
        flag = "BLOCKED" if v["blocked"] else "evades"
        print(f"{row[0]:<28} {row[1]:>6.3f} {row[2]:>6.3f} {row[3]:>6.3f} "
              f"{row[4]:>7.3f}  {flag}")
        if args.verbose:
            print(f"{'':<28} {d.get('text','')[:100]!r}")

    n = len(docs)
    print("-" * 74)
    print(f"evaded Ring 1 : {len(evaded)}/{n} ({100*len(evaded)/n:.0f}%)")
    print(f"blocked       : {len(blocked)}/{n} ({100*len(blocked)/n:.0f}%)")

    # Per-question view: a question is only genuinely under adaptive
    # attack if ALL of its poison documents survive Ring 1.
    fully = [q for q, bs in by_q.items() if not any(bs)]
    partial = [q for q, bs in by_q.items() if any(bs) and not all(bs)]
    print(f"\nquestions with ALL poison evading : {len(fully)}/{len(by_q)}")
    print(f"questions with SOME poison blocked: {len(partial)}/{len(by_q)}")

    if blocked:
        print("\nDominant blocking signal among blocked docs:")
        for name, idx in (("perplexity p", 1), ("pattern pa", 2), ("outlier o", 3)):
            hits = sum(1 for r in blocked if r[idx] >= args.threshold)
            print(f"  {name:<14} >= {args.threshold}: {hits}/{len(blocked)}")

    if args.report_only:
        print("\n[report-only] exiting 0 regardless of verdict.")
        return

    if blocked:
        print(f"\nRESULT: NOT ADAPTIVE -- {len(blocked)} document(s) would be "
              f"blocked by Ring 1.\nDo NOT report ASR from this corpus as an "
              f"adaptive-attacker result.")
        sys.exit(1)

    print(f"\nRESULT: ADAPTIVE CONFIRMED -- all {n} documents evade Ring 1 "
          f"(score < {args.threshold}).\nASR measured against this corpus is a "
          f"valid adaptive-attacker result.")


if __name__ == "__main__":
    main()
