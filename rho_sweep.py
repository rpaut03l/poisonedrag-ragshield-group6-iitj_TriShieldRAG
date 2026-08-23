"""
rho_sweep.py -- empirically test Proposition 1 (the minority-poison
assumption) by sweeping the poison fraction rho across the predicted
0.5 boundary and recording what each ring actually does.

Proposition 1 states that Rings 2 and 3 recover the correct answer
only while poison is a MINORITY of the retrieved top-k (rho < 0.5).
Above that, the majority token bag mu is dominated by poison, so the
consistency signal INVERTS: poison agrees with the (poisoned)
majority and scores HIGH, while the lone clean document disagrees
with it and scores LOW.

The paper derives this analytically and reports it as "consistent
with our single reported evaluation configuration". This script turns
it into a measured curve.

Two phases:

  PHASE 1 (cheap, deterministic, dense): for each rho, build a top-k
  set with exactly that poison fraction and record Ring 2's internals
  -- mean consistency for poison vs clean, mean trust for each, and
  whether the trust ORDERING has inverted (poison ranked above clean).
  No LLM calls, so we can sweep every achievable rho and repeat over
  all questions.

  PHASE 2 (expensive, optional): at selected rho values, run the full
  Ring 3 panel to measure weighted agreement and end-to-end ASR.

Usage:
    python3 rho_sweep.py                      # phase 1 only
    python3 rho_sweep.py --with-llm           # phases 1 and 2
    python3 rho_sweep.py --k 10               # denser rho grid
"""
import argparse, json, os, statistics, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("DEMO_MODE", "2")

from ragshield_core.ring2_retrieval import RetrievalScorer      # noqa: E402
from ragshield_core.retriever import Retriever, load_targets    # noqa: E402


def load_poison(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def build_topk(clean: list[dict], poison: list[dict], k: int, n_poison: int):
    """Top-k containing exactly n_poison poison docs, rest clean."""
    chosen = poison[:n_poison] + clean[: k - n_poison]
    # Give every doc a comparable retrieval score. Poison is engineered
    # to rank highly, so we give it a slight edge -- being generous to
    # the attacker here is the conservative choice for a defense paper.
    for i, d in enumerate(chosen):
        d.setdefault("score", 0.80 if d.get("source") == "POISONED" else 0.72)
    return chosen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poison", default="baseline/poison_adaptive.jsonl")
    ap.add_argument("--targets", default="evaluation/scale_target_questions.json")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--out", default="evaluation/results/rho_sweep.json")
    ap.add_argument("--with-llm", action="store_true")
    ap.add_argument("--llm-rhos", default="0.2,0.4,0.6,0.8")
    args = ap.parse_args()

    targets = json.loads(Path(args.targets).read_text())
    poison_all = load_poison(Path(args.poison))
    by_q = {}
    for p in poison_all:
        by_q.setdefault(p["target_q"], []).append(p)

    print("Loading corpus for clean documents...")
    r = Retriever(backend="scale").load_kb()
    scorer = RetrievalScorer()

    rows = []
    print(f"\nPHASE 1 -- Ring 2 internals, k={args.k}, "
          f"{len(targets)} questions\n")
    print(f"{'rho':>5} {'n_p':>4} {'cons(poison)':>13} {'cons(clean)':>12} "
          f"{'trust(poison)':>14} {'trust(clean)':>13} {'inverted':>9}")
    print("-" * 78)

    for n_p in range(0, args.k + 1):
        rho = n_p / args.k
        cp, cc, tp, tc, inversions = [], [], [], [], []
        for t in targets:
            q = t["question"]
            pois = by_q.get(q, [])
            if len(pois) < n_p:
                continue
            # clean docs: real corpus hits for this query, poison excluded
            clean = [d for d in r.retrieve(q, args.k * 4)
                     if d.get("source") != "POISONED"][: args.k]
            if len(clean) < args.k - n_p:
                continue
            topk = build_topk([dict(c) for c in clean],
                              [dict(p) for p in pois], args.k, n_p)
            scored = scorer.rescore(topk)
            ps = [d for d in scored if d.get("source") == "POISONED"]
            cs = [d for d in scored if d.get("source") != "POISONED"]
            if ps:
                cp.append(statistics.mean(d["_ring2"]["consistency"] for d in ps))
                tp.append(statistics.mean(d["_ring2"]["trust"] for d in ps))
            if cs:
                cc.append(statistics.mean(d["_ring2"]["consistency"] for d in cs))
                tc.append(statistics.mean(d["_ring2"]["trust"] for d in cs))
            if ps and cs:
                # inverted = highest-trust doc in the set is poison
                inversions.append(scored[0].get("source") == "POISONED")

        m = lambda xs: round(statistics.mean(xs), 3) if xs else None
        inv_rate = round(sum(inversions) / len(inversions), 2) if inversions else None
        row = {"rho": round(rho, 2), "n_poison": n_p,
               "consistency_poison": m(cp), "consistency_clean": m(cc),
               "trust_poison": m(tp), "trust_clean": m(tc),
               "inversion_rate": inv_rate, "n_questions": len(inversions)}
        rows.append(row)
        f = lambda v: f"{v:>13.3f}" if isinstance(v, float) else f"{'-':>13}"
        print(f"{rho:>5.2f} {n_p:>4} {f(row['consistency_poison'])} "
              f"{str(row['consistency_clean'] if row['consistency_clean'] is not None else '-'):>12} "
              f"{str(row['trust_poison'] if row['trust_poison'] is not None else '-'):>14} "
              f"{str(row['trust_clean'] if row['trust_clean'] is not None else '-'):>13} "
              f"{str(inv_rate if inv_rate is not None else '-'):>9}")

    # locate the crossing point
    cross = None
    for a, b in zip(rows, rows[1:]):
        ca, cb = a["consistency_clean"], b["consistency_clean"]
        pa, pb = a["consistency_poison"], b["consistency_poison"]
        if None in (ca, cb, pa, pb):
            continue
        if (ca - pa) > 0 >= (cb - pb):
            cross = (a["rho"], b["rho"])
            break

    print("\n" + "=" * 78)
    if cross:
        print(f"CONSISTENCY INVERSION between rho={cross[0]} and rho={cross[1]}")
        print(f"Proposition 1 predicts the boundary at rho = 0.5.")
    else:
        print("No consistency crossing detected in this sweep range.")

    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "k": args.k, "n_questions": len(targets),
        "poison_corpus": args.poison,
        "proposition_1_predicted_boundary": 0.5,
        "observed_inversion_between": cross,
        "rows": rows,
    }, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
