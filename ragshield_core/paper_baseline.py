"""
ragshield_core.paper_baseline
Reproduces PoisonedRAG's own tested defenses (perplexity detection +
duplicate-text filtering) as a faithful "prior work" baseline for the
3-way evaluation (none / paper's-defenses / full RAG-Shield).

Per the corrected literature review (verified against PoisonedRAG's
actual Section 7):
  - Perplexity detection: AUC 0.25 (NQ), 0.12 (MS-MARCO) -- WORSE than
    random guessing (Fig 6).
  - Duplicate-text filtering: UNCHANGED across all values (Table 13)
    -- because each poison doc is independently LLM-generated, so no
    two are literal duplicates.

This module intentionally reproduces those SAME two mechanisms
faithfully, so the evaluation shows the SAME near-total failure the
original paper reports, rather than an artificially stronger
strawman baseline. Paraphrasing-based defense and knowledge expansion
(the other two PoisonedRAG defenses) are NOT implemented here --
scoped out given the submission timeline; noted as a limitation.
"""
from __future__ import annotations
import numpy as np

from .ring1_ingest import PerplexityDetector


class PaperBaselineDefense:
    def __init__(self, perplexity_threshold: float = 0.5,
                 dup_cosine_threshold: float = 0.98, embedder=None):
        self.perp = PerplexityDetector()
        self.perplexity_threshold = perplexity_threshold
        self.dup_cosine_threshold = dup_cosine_threshold
        self._embedder = embedder  # allow injection to avoid loading a 2nd model copy

    def _get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            from . import config
            self._embedder = SentenceTransformer(config.EMBED_MODEL, device="cpu")
        return self._embedder

    def filter_corpus(self, docs: list[dict]) -> tuple[list[dict], list[dict]]:
        """Return (kept, blocked). Mirrors IngestGuard.filter_corpus's
        signature so it drops into the same call site in rag_shield.py.
        """
        # Step 1: perplexity-ONLY filtering -- this is PoisonedRAG's own
        # tested defense, NOT RAG-Shield's combined Ring 1 score (which
        # also folds in pattern-matching and embedding-outlier signals
        # the original paper never tested).
        kept_p, blocked_p = [], []
        for d in docs:
            text = f"{d.get('title', '')} {d.get('text', '')}"
            score = self.perp.score(text)
            verdict = {"perplexity": round(score, 3),
                       "blocked": score >= self.perplexity_threshold}
            (blocked_p if verdict["blocked"] else kept_p).append(
                {**d, "_paper_baseline": verdict})

        if len(kept_p) <= 1:
            return kept_p, blocked_p

        # Step 2: duplicate-text filtering on whatever survived step 1.
        # Expectation (per Table 13): near-zero effect, since PoisonedRAG
        # poison docs are independently LLM-generated and rarely
        # literal near-duplicates of each other.
        model = self._get_embedder()
        texts = [f"{d.get('title', '')} {d.get('text', '')}" for d in kept_p]
        vecs = model.encode(texts, normalize_embeddings=True)
        keep_mask = [True] * len(kept_p)
        dup_blocked = []
        for i in range(len(kept_p)):
            if not keep_mask[i]:
                continue
            for j in range(i + 1, len(kept_p)):
                if not keep_mask[j]:
                    continue
                cos = float(np.dot(vecs[i], vecs[j]))
                if cos >= self.dup_cosine_threshold:
                    keep_mask[j] = False
                    dup_blocked.append({
                        **kept_p[j],
                        "_paper_baseline": {"duplicate_of_index": i,
                                             "cosine": round(cos, 4)},
                    })

        kept = [d for d, keep in zip(kept_p, keep_mask) if keep]
        blocked = blocked_p + dup_blocked
        return kept, blocked
