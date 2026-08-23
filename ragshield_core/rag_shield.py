"""
ragshield_core.rag_shield
The orchestrator. Wires Retriever + Ring1 + Ring2 + Ring3 into one pipeline
and exposes a single `answer()` call plus a `trace()` call that returns every
ring's decision for the forensic UI.

Usage:
    shield = RAGShield().setup(poisoned=True)
    out = shield.answer("Who founded Tesla Motors?", defense=True,
                        candidates=["Martin Eberhard", "Nikola Jones"])
"""
from __future__ import annotations
from typing import Optional

from .retriever import Retriever, load_targets
from .ring1_ingest import IngestGuard
from .ring2_retrieval import RetrievalScorer
from .ring3_consensus import CrossLLMConsensus
from .llm_backends import make_consensus_panel
from .paper_baseline import PaperBaselineDefense
from . import config
from .raglog import log


class RAGShield:
    def __init__(self, top_k: int = None):
        self.top_k = top_k or config.TOP_K
        self.retriever = Retriever()
        self.ingest = IngestGuard()
        self.scorer = RetrievalScorer()
        self.panel = make_consensus_panel()
        self.consensus = CrossLLMConsensus(self.panel)
        # NEW: third evaluation arm -- reproduces PoisonedRAG's OWN
        # tested defenses (perplexity + duplicate-text filtering),
        # separate from RAG-Shield's own Ring 1/2/3. See
        # paper_baseline.py for why this is a faithful, not
        # artificially weak or strong, reproduction.
        self.paper_baseline = PaperBaselineDefense()
        self._questions = [t["question"] for t in load_targets()]

    # ---------- setup ----------
    def setup(self, poisoned: bool = True):
        """
        Load KB and (optionally) inject poison into the corpus.
        NOTE: Ring 1 is NOT applied here. It is applied per-query only when
        defense=True, so the no-defense baseline genuinely sees the poison
        (otherwise the attack could never 'succeed' and the demo would lie).
        """
        self.retriever.load_kb()
        self.poisoned = poisoned
        if poisoned:
            self.retriever.load_poison()
            self.retriever.inject_poison()   # builds index with poison included
        else:
            self.retriever.build()
        self._ring1_blocked = []
        return self

    # ---------- main entry ----------
    def answer(self, question: str, defense: bool = True,
               candidates: Optional[list[str]] = None) -> dict:
        trace = self.trace(question, defense=defense, candidates=candidates)
        return {"answer": trace["answer"], "defense": defense, "trace": trace}

    def trace(self, question: str, defense: bool = True,
              candidates: Optional[list[str]] = None) -> dict:
        log(f"QUERY: {question!r}  (defense={'ON' if defense else 'OFF'})")
        retrieved = self.retriever.retrieve(question, self.top_k)
        log(f"  retrieved {len(retrieved)} docs "
            f"({sum(1 for d in retrieved if d.get('source')=='POISONED')} poison)")
        t = {"question": question, "defense": defense, "retrieved": retrieved,
             "ring1_blocked": []}

        if not defense:
            log("  NO DEFENSE: feeding raw context straight to the LLM")
            llm = self.panel[0]
            t["answer"] = llm.answer_with_context(question, retrieved, candidates)
            log(f"  ANSWER (undefended) -> {t['answer'][:60]!r}")
            t["mode"] = "no-defense"
            return t

        # ----- NEW: PAPER'S DEFENSES BASELINE (third evaluation arm) -----
        # Faithful reproduction of PoisonedRAG's own tested defenses
        # (perplexity + duplicate-text filtering), NOT RAG-Shield's
        # Ring 1/2/3. See paper_baseline.py docstring for why this is
        # expected to perform close to no-defense, not somewhere
        # comfortably in the middle.
        if defense == "paper_baseline":
            log("  PAPER BASELINE (perplexity + duplicate-text filtering)...")
            kept_pb, blocked_pb = self.paper_baseline.filter_corpus(retrieved)
            log(f"  PAPER BASELINE -> blocked {len(blocked_pb)}, kept {len(kept_pb)}")
            t["paper_baseline_blocked"] = blocked_pb
            use_docs = kept_pb if kept_pb else retrieved  # fail-open, same policy as Ring 1
            llm = self.panel[0]
            t["answer"] = llm.answer_with_context(question, use_docs, candidates)
            log(f"  ANSWER (paper-baseline) -> {t['answer'][:60]!r}")
            t["mode"] = "paper-baseline"
            return t

        # ----- DEFENSE ON (full RAG-Shield: Ring 1 + Ring 2 + Ring 3) -----
        # Ring 1: screen the retrieved docs at query time (ingest-style checks)
        log("  RING 1 (Ingest Guard): screening retrieved docs...")
        # FIXED (target-question leak): previously passed self._questions,
        # the FULL list of questions the attacker chose to target. A real
        # defender does not have that list -- it only sees the query the
        # user just sent. Passing [question] restricts the verbatim-question
        # check to the incoming query alone, which is what Algorithm 1's
        # kbQ input can defensibly mean in deployment.
        kept1, blocked1 = self.ingest.filter_corpus(retrieved, [question])
        log(f"  RING 1 -> blocked {len(blocked1)} poison doc(s)")
        t["ring1_blocked"] = blocked1
        if kept1:
            retrieved = kept1
        else:
            # FIXED (oracle leak): the previous version filtered the wider
            # re-retrieval with `d.get("source") != "POISONED"`, i.e. it read
            # the attack's own ground-truth label to decide what to keep. No
            # deployable defense can do that -- knowing which documents are
            # poisoned IS the problem being solved. That filter fired on 6/10
            # questions in the 2.68M-scale run and was directly responsible
            # for the 0% ASR reported there.
            #
            # THE FIX: re-retrieve a wider pool, exclude only what Ring 1
            # already blocked on its own detector evidence, then run those
            # same detectors over the newly-surfaced candidates. If poison
            # survives, it survives -- Rings 2 and 3 still get their chance.
            blocked_ids = {b.get("id") for b in blocked1}
            wider = self.retriever.retrieve(question, self.top_k * 6)
            fresh = [d for d in wider if d.get("id") not in blocked_ids]
            rescreened_keep, rescreened_block = self.ingest.filter_corpus(
                fresh, [question])
            t["ring1_blocked"] = blocked1 + rescreened_block
            retrieved = rescreened_keep[: self.top_k]
            n_surv = sum(1 for d in retrieved if d.get("source") == "POISONED")
            log(f"  RING 1 -> all top-k blocked; re-retrieved {len(retrieved)} "
                f"doc(s) from wider pool after re-screening ({n_surv} still poison)")

        # Ring 2: rescore + drop low-trust
        log("  RING 2 (Retrieval Scorer): re-ranking by trust...")
        kept, dropped = self.scorer.filter(retrieved)
        log(f"  RING 2 -> kept {len(kept)}, dropped {len(dropped)} low-trust")
        t["ring2_kept"], t["ring2_dropped"] = kept, dropped

        # Ring 3: cross-LLM consensus with re-retrieval on disagreement
        def reretrieve(suspects):
            ids = {s.get("id") for s in suspects}
            return [d for d in kept if d.get("id") not in ids]

        log(f"  RING 3 (Cross-LLM Consensus): polling {len(self.panel)} models...")
        verdict = self.consensus.run(question, kept, candidates, reretrieve)
        log(f"  RING 3 -> agreement {int(verdict['agreement']*100)}%"
            + (" | DISAGREED, re-retrieved" if verdict.get("reretrieved") else " | agreed"))
        t["ring3"] = verdict
        t["answer"] = verdict["answer"]
        log(f"  FINAL ANSWER -> {t['answer'][:60]!r}")
        t["mode"] = "rag-shield"
        return t
