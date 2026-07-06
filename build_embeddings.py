"""
build_embeddings.py — embed a dataset into 768-dim vectors and save
to disk, ready for FAISS indexing.

Usage:
    python3 build_embeddings.py --dataset nq --batch-size 256 --device cpu
    python3 build_embeddings.py --dataset nq --batch-size 256 --device mps
    python3 build_embeddings.py --dataset demo --batch-size 32 --device cpu

Notes for Mac users:
    --device cuda   WILL NOT WORK on a Mac (no NVIDIA GPU). Use "mps"
                    (Apple Silicon GPU) or "cpu" instead.
    --device mps    Apple Silicon GPU acceleration. Faster than CPU,
                    but known to be less stable in some sentence-
                    transformers versions on long-running jobs — if
                    it crashes partway through, re-run with "cpu".
    --device cpu    Slowest but most stable. On an M1 Max, budget
                    roughly 10-14 hours for the full 2.6M-passage
                    Natural Questions corpus. Consider running
                    overnight, or in smaller chunks (see --limit).
"""

import argparse
import time
import sys
from pathlib import Path
from typing import Optional, List

import numpy as np


def get_args():
    p = argparse.ArgumentParser(description="Build sentence embeddings for RAG-Shield")
    p.add_argument("--dataset", type=str, default="demo",
                    choices=["demo", "nq"],
                    help="'demo' = your existing small KB. "
                         "'nq' = Natural Questions corpus (~2.6M passages)")
    p.add_argument("--batch-size", type=int, default=32,
                    help="How many documents to embed at once. "
                         "Larger = faster but more memory used.")
    p.add_argument("--device", type=str, default="cpu",
                    choices=["cpu", "mps", "cuda"],
                    help="cpu (safe, slow) / mps (Apple GPU) / "
                         "cuda (NVIDIA GPU only — will NOT work on Mac)")
    p.add_argument("--limit", type=int, default=None,
                    help="Optional: only embed the first N documents "
                         "(useful for testing before committing to "
                         "the full multi-hour run)")
    p.add_argument("--output", type=str, default="embeddings/nq_embeddings.npy",
                    help="Where to save the resulting embeddings")
    return p.parse_args()


def load_documents(dataset_name: str, limit: Optional[int]) -> List[str]:
    if dataset_name == "demo":
        # Reuses your existing small demo KB from retriever.py
        from ragshield_core.retriever import _DEMO_CLEAN
        docs = [d["text"] for d in _DEMO_CLEAN]
        print(f"Loaded {len(docs)} demo documents.")
        return docs

    elif dataset_name == "nq":
        try:
            from datasets import load_dataset
        except ImportError:
            print("ERROR: 'datasets' library not installed.")
            print("Run: pip install datasets")
            sys.exit(1)

        print("Downloading/loading Natural Questions corpus "
              "(this can take a while the first time)...")
        ds = load_dataset("natural_questions", split="train")

        docs = []
        for i, row in enumerate(ds):
            if limit is not None and i >= limit:
                break
            # Natural Questions has nested document structure —
            # extract plain text from the document_text field
            text = row.get("document", {}).get("html", "") or \
                   row.get("document", {}).get("text", "")
            if text:
                docs.append(text)

        print(f"Loaded {len(docs)} documents from Natural Questions "
              f"({'limited to ' + str(limit) if limit else 'full corpus'}).")
        return docs

    return []


def main():
    args = get_args()

    print(f"\n{'='*60}")
    print(f"  RAG-Shield Embedding Builder")
    print(f"{'='*60}")
    print(f"  Dataset:     {args.dataset}")
    print(f"  Batch size:  {args.batch_size}")
    print(f"  Device:      {args.device}")
    print(f"  Limit:       {args.limit or 'none (full dataset)'}")
    print(f"  Output:      {args.output}")
    print(f"{'='*60}\n")

    if args.device == "cuda":
        print("WARNING: --device cuda requires an NVIDIA GPU.")
        print("If you are on a Mac, this will fail. Use --device mps")
        print("(Apple Silicon GPU) or --device cpu instead.\n")

    from sentence_transformers import SentenceTransformer

    print("Loading all-mpnet-base-v2 model...")
    model = SentenceTransformer("all-mpnet-base-v2", device=args.device)

    docs = load_documents(args.dataset, args.limit)

    if len(docs) == 0:
        print("ERROR: no documents loaded. Check your dataset choice.")
        sys.exit(1)

    print(f"\nEmbedding {len(docs)} documents "
          f"(batch size {args.batch_size}, device {args.device})...")
    print("This is the slow part. Progress will print periodically.\n")

    start = time.time()

    embeddings = model.encode(
        docs,
        batch_size=args.batch_size,
        normalize_embeddings=True,   # unit-length vectors for cosine similarity
        show_progress_bar=True,
        convert_to_numpy=True,
    )

    elapsed = time.time() - start
    print(f"\nDone. Embedded {len(docs)} documents in "
          f"{elapsed/60:.1f} minutes ({elapsed/len(docs)*1000:.1f} ms/doc average).")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, embeddings)

    print(f"\nSaved embeddings to: {output_path}")
    print(f"Shape: {embeddings.shape}  "
          f"({embeddings.shape[0]} docs x {embeddings.shape[1]} dimensions)")
    print(f"\nNext step: build a FAISS index from these embeddings.")
    print(f"See docs/TECH_FAISS.md for the IndexIVFFlat setup at this scale.")


if __name__ == "__main__":
    main()
