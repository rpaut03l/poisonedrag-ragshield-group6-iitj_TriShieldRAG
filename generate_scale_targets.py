"""
generate_scale_targets.py — build a target-questions file FROM your
actual Scale Mode dataset, instead of using the small demo's
hardcoded Tesla/Eiffel Tower/Einstein questions.

This solves the "pages 1-5 still show the same 5-10 questions even
in DEMO_MODE=2" problem — those pages read from load_targets(),
which needs a REAL file to read from when Scale Mode is active.

Run this AFTER you've built your embeddings and FAISS index:
    .venv/bin/python3.11 generate_scale_targets.py --n-questions 20

This picks N random documents from your loaded Scale Mode corpus,
uses each one's first sentence as a naive "question" seed, and
creates plausible wrong-answer poison targets — good enough to
DEMONSTRATE that RAG-Shield now operates on YOUR content, not
meant to replace a carefully hand-curated benchmark.
"""
import argparse
import json
import random
from pathlib import Path


def get_args():
    p = argparse.ArgumentParser(description="Generate Scale Mode target questions")
    p.add_argument("--n-questions", type=int, default=10,
                    help="How many target questions to generate")
    p.add_argument("--n-poison", type=int, default=5,
                    help="How many poison docs per question (matches Ring 1 test)")
    p.add_argument("--seed", type=int, default=42,
                    help="Random seed, for reproducible question selection")
    return p.parse_args()


def main():
    args = get_args()
    random.seed(args.seed)

    import sys
    sys.path.insert(0, ".")
    from ragshield_core.retriever import Retriever

    print("Loading your Scale Mode dataset...")
    r = Retriever(backend="scale").load_kb()
    print(f"Loaded {len(r.docs)} documents from Scale Mode.")

    if len(r.docs) < args.n_questions:
        print(f"WARNING: only {len(r.docs)} documents available, "
              f"reducing --n-questions from {args.n_questions} to {len(r.docs)}")
        args.n_questions = len(r.docs)

    sampled = random.sample(r.docs, args.n_questions)

    targets = []
    for i, doc in enumerate(sampled):
        title = doc.get("title", f"Document {i}")
        text = doc.get("text", "")

        # Naive question generation: turn the title into a "What is X?"
        # style question. This is intentionally simple — good enough
        # to prove Scale Mode's pages reflect YOUR data, not meant to
        # replace a properly hand-curated evaluation set.
        question = f"What is described in the document titled '{title}'?"
        true_answer = text[:80].strip() if text else title
        wrong_answer = f"[Placeholder incorrect answer for {title}]"

        targets.append({
            "id": f"scale_q{i+1}",
            "question": question,
            "true_answer": true_answer,
            "wrong_answer": wrong_answer,
            "n_poison": args.n_poison,
        })

    output_path = Path("evaluation/scale_target_questions.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(targets, indent=2))

    print(f"\nGenerated {len(targets)} target questions from your Scale "
          f"Mode dataset.")
    print(f"Saved to: {output_path}")
    print(f"\nNext step: DEMO_MODE=2 bash run_live.sh")
    print(f"Pages 1-5 will now show questions built from YOUR documents,")
    print(f"not the small demo's Tesla/Eiffel Tower/Einstein set.")
    print(f"\nNOTE: these are naive, auto-generated questions/answers —")
    print(f"for a real evaluation harness, hand-curate a proper")
    print(f"question/true-answer/wrong-answer set in this same JSON format.")


if __name__ == "__main__":
    main()
