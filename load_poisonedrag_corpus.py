"""
load_poisonedrag_corpus.py -- import the ORIGINAL PoisonedRAG artifact
(results/adv_targeted_results/nq.json) into TriShieldRAG's evaluation
format, with validation.

Why this instead of generating our own poison:

  * It is the exact artifact behind PoisonedRAG's published USENIX
    Security 2025 numbers, so a reviewer cannot argue we weakened or
    strawmanned the attack we claim to defend against.
  * Their target questions are hand-curated close-ended questions with
    real factual answers, replacing our auto-generated "What is 'X'?"
    set whose true_answers were often weak (e.g. "Recent human history
    of the Rocky Mountains is one of more rapid change.").
  * Their incorrect answers are subtle and same-type ("23" -> "24"),
    not absurd category errors, which is the threat model the paper
    actually describes.
  * Same corpus (BeIR NQ, 2,681,468 passages), same questions, same
    n_p=5, same k=5 as their Table 1 -> our ASR becomes DIRECTLY
    comparable to their reported 97% for the first time.

Source schema (per entry):
    {id, question, "correct answer", "incorrect answer", adv_texts[5]}

Note on poison length: their adv_texts run ~100 words (gen_adv.py
ADV_PROMPT[0]), versus the ~40-word boilerplate template previously
used here. Ring 1's perplexity detector p(d) was implicitly tuned
against the shorter template, so scores may differ substantially.
That is a real finding either way and should be reported, not tuned
around.

Usage:
    python3 load_poisonedrag_corpus.py \
        --src ~/PoisonedRAG/results/adv_targeted_results/nq.json \
        --n-questions 10 --seed 42
"""
import argparse, json, random, sys
from pathlib import Path

# Refusal-looking text must never end up as an attacker target answer.
_REFUSAL_SIGNS = (
    "i can't", "i cannot", "i'm not able", "i am not able", "i appreciate",
    "as an ai", "i won't", "i will not", "sorry", "unable to help",
)


def looks_like_refusal(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(s in t for s in _REFUSAL_SIGNS) or len(t.split()) > 15


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True,
                    help="PoisonedRAG results/adv_targeted_results/nq.json")
    ap.add_argument("--targets-out", default="evaluation/scale_target_questions.json")
    ap.add_argument("--poison-out", default="baseline/poison_corpus.jsonl")
    ap.add_argument("--n-questions", type=int, default=10)
    ap.add_argument("--n-poison", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    src = json.loads(Path(args.src).expanduser().read_text())
    print(f"Loaded {len(src)} PoisonedRAG NQ entries from {args.src}")

    entries = [src[k] for k in sorted(src.keys())]

    # ---- validate before selecting -------------------------------------
    usable, rejected = [], []
    for e in entries:
        q = e.get("question", "").strip()
        ca = e.get("correct answer", "").strip()
        ia = e.get("incorrect answer", "").strip()
        adv = [a.strip() for a in e.get("adv_texts", []) if a and a.strip()]
        why = None
        if not (q and ca and ia):
            why = "missing question/answer field"
        elif len(adv) < args.n_poison:
            why = f"only {len(adv)} adv_texts (need {args.n_poison})"
        elif len(set(adv[:args.n_poison])) < args.n_poison:
            why = "adv_texts contain duplicates"
        elif looks_like_refusal(ia):
            why = "incorrect answer looks like a refusal / is too long"
        elif ca.lower() == ia.lower():
            why = "incorrect answer equals correct answer"
        (rejected if why else usable).append((e, why))

    print(f"  usable: {len(usable)}   rejected: {len(rejected)}")
    for e, why in rejected[:5]:
        print(f"    - {e.get('id')}: {why}")
    if len(usable) < args.n_questions:
        sys.exit(f"ERROR: only {len(usable)} usable entries, need {args.n_questions}")

    random.seed(args.seed)
    chosen = random.sample([e for e, _ in usable], args.n_questions)

    targets, poison = [], []
    for e in chosen:
        q = e["question"].strip()
        ca, ia = e["correct answer"].strip(), e["incorrect answer"].strip()
        targets.append({
            "id": e["id"], "question": q,
            "true_answer": ca, "wrong_answer": ia,
            "n_poison": args.n_poison,
            "source_artifact": "PoisonedRAG results/adv_targeted_results/nq.json",
        })
        for i, adv in enumerate(e["adv_texts"][:args.n_poison]):
            poison.append({
                "id": f"poison_{e['id']}_{i}",
                "title": q[:60],
                # PoisonedRAG black-box: P = S (+) I with S = target question
                "text": f"{q} {adv.strip()}",
                "source": "POISONED",
                "target_q": q, "wrong_answer": ia, "true_answer": ca,
            })

    # ---- post-write sanity ---------------------------------------------
    n_distinct = len({p["text"] for p in poison})
    if n_distinct != len(poison):
        print(f"WARNING: {len(poison) - n_distinct} duplicate poison texts")
    bad = [t["id"] for t in targets if looks_like_refusal(t["wrong_answer"])]
    if bad:
        sys.exit(f"ERROR: refusal-like wrong_answer survived for {bad}")

    tp = Path(args.targets_out); tp.parent.mkdir(parents=True, exist_ok=True)
    tp.write_text(json.dumps(targets, indent=2))
    pp = Path(args.poison_out); pp.parent.mkdir(parents=True, exist_ok=True)
    pp.write_text("\n".join(json.dumps(p) for p in poison) + "\n")

    print(f"\nWrote {len(targets)} targets -> {tp}")
    print(f"Wrote {len(poison)} poison docs ({n_distinct} distinct) -> {pp}")
    avg = sum(len(p["text"].split()) for p in poison) / len(poison)
    print(f"Mean poison length: {avg:.0f} words")
    print("\nSelected questions:")
    for t in targets:
        print(f"  {t['id']}: {t['question'][:58]}")
        print(f"      true={t['true_answer']!r}  wrong={t['wrong_answer']!r}")


if __name__ == "__main__":
    main()
