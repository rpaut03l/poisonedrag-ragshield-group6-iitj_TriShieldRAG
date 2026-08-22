"""
diagnose_alignment.py -- fast, cheap test of several text-construction
hypotheses against a few known indices, before re-running the full
(slow) build_scale_metadata.py again. Only downloads 2 shards, not
all 27, and doesn't touch the corpus download (already HF-cached).
"""
import numpy as np
import torch
from datasets import load_dataset
from huggingface_hub import hf_hub_download
from sentence_transformers import SentenceTransformer

REPO = 'rpaut03l/trishieldrag-nq-mpnet-embeddings'
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

CHECK = [0, 1_500_000, 2_681_467]

print("loading BeIR/nq corpus (should hit local cache)...", flush=True)
ds = load_dataset("BeIR/nq", "corpus", split="corpus")

model = SentenceTransformer('all-mpnet-base-v2', device=DEVICE)

VARIANTS = {
    "text_only": lambda title, text: text,
    "title_space_text": lambda title, text: f"{title} {text}".strip(),
    "title_period_text": lambda title, text: f"{title}. {text}".strip(),
    "title_newline_text": lambda title, text: f"{title}\n{text}".strip(),
    "text_title_appended": lambda title, text: f"{text} {title}".strip(),
}

for idx in CHECK:
    shard_offset = (idx // 100_000) * 100_000
    within_shard = idx - shard_offset
    fname = 'emb_%09d.npy' % shard_offset
    p = hf_hub_download(REPO, fname, repo_type='dataset')
    shard = np.load(p, mmap_mode='r')
    saved_vec = np.array(shard[within_shard])
    del shard

    row = ds[idx]
    title, text = row.get("title", ""), row.get("text", "")
    print(f"\n=== idx={idx}  title={title!r}  text_len={len(text)} ===", flush=True)

    for name, fn in VARIANTS.items():
        candidate = fn(title, text)
        emb = model.encode([candidate], normalize_embeddings=True)[0]
        cosine = float(np.dot(saved_vec, emb))
        marker = "  <-- MATCH" if cosine > 0.999 else ""
        print(f"  {name:<22} cosine={cosine:.4f}{marker}", flush=True)
