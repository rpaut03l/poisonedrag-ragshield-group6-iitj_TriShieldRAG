<a id="top"></a>

# 🛠️ RAGSHIELD_PRACTICE.md — Run It, Break It, Fix It
### Commands, troubleshooting, and viva-style practice questions

---

## 🔝 TOP NAVIGATION — Jump to any file

**Previous:** [RAGSHIELD_THEORY.md](RAGSHIELD_THEORY.md#top) (the story) → [RAGSHIELD_NUMERICALS.md](RAGSHIELD_NUMERICALS.md#top) (the math) → **This file:** RAGSHIELD_PRACTICE.md (running it)

[🏠 Repo Home](../../README.md) &nbsp;·&nbsp; [📂 Docs Index](../README.md) &nbsp;·&nbsp; [📘 Theory](RAGSHIELD_THEORY.md#top) &nbsp;·&nbsp; [🧮 Numericals](RAGSHIELD_NUMERICALS.md#top) &nbsp;·&nbsp; [🛠️ Practice (you are here)](#top)

---

## 📌 TABLE OF CONTENTS

```
┌─────────────────────────────────────────────────────────┐
│  THEORY.md  →  NUMERICALS.md  →  PRACTICE.md (you are   │
│  (the story)   (the math)        here — the doing)      │
└─────────────────────────────────────────────────────────┘
```

- [A. First-Time Setup](#a-setup)
- [B. Daily Startup Commands](#b-startup)
- [C. Reading the App — Page by Page](#c-app-pages)
- [D. Troubleshooting — Common Errors](#d-troubleshooting)
- [E. Scaling to 2 Million Docs — Practical Steps](#e-scaling-steps)
- [F. Viva-Style Practice Questions](#f-viva-practice)
- [G. Mnemonics](#g-mnemonics)
- [H. Cheatsheet — Commands in One Block](#h-cheatsheet)
- [I. Exam Hacks — Last-Minute Survival](#i-exam-hacks)

---

<a id="a-setup"></a>
## A. First-Time Setup

```bash
# Step 1 — clone the repo
git clone https://github.com/rpaut03l/poisonedrag-ragshield-group6-iitj.git
cd poisonedrag-ragshield-group6-iitj

# Step 2 — create a virtual environment
python3.11 -m venv .venv
.venv/bin/python3.11 -m pip install --upgrade pip
.venv/bin/python3.11 -m pip install -r requirements.txt

# Step 3 — copy env template and fill in keys
cp .env.example .env
# Open .env and fill:
#   ANTHROPIC_API_KEY=...
#   MISTRAL_API_KEY=...
#   OLLAMA_BASE_URL=http://localhost:11434/v1

# Step 4 — (live mode only) install and start Ollama
# Download from https://ollama.com
ollama pull llama3.2:3b
ollama serve &
```

**Which `python3` are you actually using? Check this if anything
behaves strangely:**

```bash
which python3
python3 --version
```

If you have MULTIPLE Pythons installed (very common on Mac — one
from Apple's Command Line Tools, maybe another from Homebrew, maybe
another from python.org), always prefer running scripts through
your **virtual environment's** Python directly, to avoid confusing
version mismatches:

```bash
.venv/bin/python3.11 build_embeddings.py --dataset nq --device cpu --limit 5000
# instead of just "python3 build_embeddings.py ..."
```

[⬆ Back to top](#top)

---

<a id="b-startup"></a>
## B. Daily Startup Commands

```bash
cd poisonedrag-ragshield-group6-iitj

# Check Ollama is running
ps aux | grep -i ollama

# Pre-flight — confirm all 3 LLMs are reachable
DEMO_MODE=0 .venv/bin/python3.11 backends_status.py

# Start the app (LIVE mode — real LLMs)
DEMO_MODE=0 bash run_live.sh

# OR start the app (DEMO mode — instant, mock LLMs, no API keys)
DEMO_MODE=1 bash run_demo.sh

# Watch the live decision log (separate terminal)
bash tail_logs.sh
```

**What "good" pre-flight output looks like:**

```
DEMO_MODE=0  ->  LIVE mode: Ring 3 uses the live backends below

Pinging backends:
  [LIVE] Claude (Anthropic)          -> 'OK'
  [LIVE] Mistral-Small (MistralAI)   -> 'OK'
  [LIVE] Ollama (local Meta)         -> 'OK'

Live backends : ['Claude', 'Mistral', 'LLaMA']
Ring 3 panel  : 3 vendor(s) active

✅  Ready for demo.
```

[⬆ Back to top](#top)

---

<a id="c-app-pages"></a>
## C. Reading the App — Page by Page

```
Page 1 — Attack Demo
  Do: pick a question, click "Run attack (no defense)"
  See: 5 poison docs, the LLM's wrong answer
  Proves: without defense, poison wins

Page 2 — Defense Demo
  Do: pick a question, click "Run with RAG-Shield"
  See: Ring 1 → Ring 2 → Ring 3, live numbers, final answer
  Proves: with defense, correct answer survives

Page 3 — Side by Side
  Do: click "Compare"
  See: no-defense (red) vs RAG-Shield (green), same screen
  Proves: the visual "before and after"

Page 4 — Forensic Explorer
  Do: expand any retrieved document
  See: the raw JSON scores from all 3 rings for that doc
  Proves: every decision is auditable, not a black box

Page 5 — Results Dashboard
  Do: click "Run evaluation"
  See: ASR % for No-Defense vs RAG-Shield, all 10 questions
  Proves: the headline number (91%→0-13%) is real, computed live
```

[⬆ Back to top](#top)

---

<a id="d-troubleshooting"></a>
## D. Troubleshooting — Common Errors

```
ERROR: "command not found: python"
FIX:   Use full venv path: .venv/bin/python3.11 <script>.py

ERROR: "ModuleNotFoundError: No module named 'X'"
FIX:   .venv/bin/python3.11 -m pip install X
       If pip is broken (resolvelib error), nuclear rebuild:
         rm -rf .venv
         python3.11 -m venv .venv
         .venv/bin/python3.11 -m pip install --upgrade pip
         .venv/bin/python3.11 -m pip install -r requirements.txt

ERROR: "TypeError: unsupported operand type(s) for |: 'type' and
        'NoneType'"
FIX:   This means your script has "new-style" type hints like
       `int | None`, which only work on Python 3.10+. Your system's
       python3 is older (common with Apple's built-in or Homebrew
       Python 3.9). Fix the script to use:
         from typing import Optional
         def my_func(x: Optional[int]):
       instead of:
         def my_func(x: int | None):
       This works on EVERY Python version, old or new.

ERROR: "RuntimeError: ... 'nx >= static_cast<idx_t>(k)' failed:
        Number of training points (500) should be at least as
        large as number of clusters (4096)"
FIX:   This means nlist (number of clusters) is LARGER than how
       many vectors you actually have. FAISS needs at least
       nlist vectors to train that many clusters — you can't sort
       500 books into 4096 labeled bins, there aren't enough books.

       Rule of thumb: nlist ≈ 4 × sqrt(number_of_vectors),
       capped at vectors/4 so you never exceed what you have.

       Fixed code:
         import math
         n = vectors.shape[0]
         nlist = max(1, min(int(4 * math.sqrt(n)), n // 4, n))
         index = faiss.IndexIVFFlat(quantizer, d, nlist,
                                     faiss.METRIC_INNER_PRODUCT)
         index.train(vectors[:n])

       This scales automatically: n=500 → nlist=89 (safe),
       n=2.6M → nlist≈6449 (well-tuned for that size). Never
       hardcode nlist=4096 when testing on small --limit slices.

ERROR: "[DOWN] Claude -> No module named 'typing_extensions'"
FIX:   .venv/bin/python3.11 -m pip install typing_extensions
       If still failing, nuclear rebuild above.

ERROR: "[DOWN] Mistral -> MISTRAL_API_KEY not set"
FIX:   Get free key: https://console.mistral.ai/api-keys
       Add to .env: MISTRAL_API_KEY=your-key-here
       Must be a real mistral.ai key, not a GCP/Vertex key

ERROR: "Status 401 Unauthorized" (Mistral)
FIX:   Wrong key type — re-check it's from console.mistral.ai

ERROR: "ImportError: cannot import name 'Mistral' from 'mistralai'"
FIX:   Pin exact version:
         .venv/bin/python3.11 -m pip install mistralai==1.3.1

ERROR: Ollama shows [DOWN]
FIX:   ollama serve &  → wait 5s → re-run backends_status.py

ERROR: Streamlit shows stale data
FIX:   Cmd+R (or Ctrl+R) in browser — clears cache in 2-3 seconds

ERROR: "NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+"
FIX:   This is just a WARNING, not an error — safe to ignore. It
       means your Python's built-in SSL library is older than what
       urllib3 v2 prefers. The script will still run correctly.
       If you want to silence it permanently:
         .venv/bin/python3.11 -m pip install 'urllib3<2'

ERROR: script seems "stuck" after printing setup info, no crash,
       just no more output for a while (e.g. a lock/mutex message)
FIX:   This is often just the embedding model loading or a native
       library (PyTorch/tokenizers) doing internal setup — NOT
       necessarily broken. Wait 1-2 minutes. If truly stuck longer
       than 5 minutes with zero CPU/GPU activity (check Activity
       Monitor), Ctrl+C and retry with a smaller --limit or with
       --device cpu instead of --device mps.

FALLBACK: everything broken, demo in 10 minutes
FIX:   DEMO_MODE=1 .venv/bin/python3.11 -m streamlit run frontend/app.py
       Zero API keys, instant startup, same logic, mock LLMs
```

[⬆ Back to top](#top)

---

<a id="e-scaling-steps"></a>
## E. Scaling to 2 Million Docs — Practical Steps

**The math doesn't change (see [Numericals Section H](RAGSHIELD_NUMERICALS.md#h-scaling-math))
— only the infrastructure around retrieval does. Here's the
practical checklist:**

```bash
# Step 1 — get the Natural Questions corpus
pip install datasets

# Step 2 — embed documents. Use build_embeddings.py in the repo root.
# IMPORTANT for Mac users:
#   --device cuda is for NVIDIA GPUs ONLY — it will not work on a Mac.
#   Use --device mps (Apple Silicon GPU) or --device cpu instead.
#
# ALWAYS test with a small --limit first before committing to the
# full multi-hour run:
.venv/bin/python3.11 build_embeddings.py \
    --dataset nq --batch-size 256 --device mps --limit 5000

# if that works cleanly, scale up gradually:
.venv/bin/python3.11 build_embeddings.py \
    --dataset nq --batch-size 256 --device mps --limit 100000

# only once THAT works, run the full corpus (budget several hours):
.venv/bin/python3.11 build_embeddings.py \
    --dataset nq --batch-size 256 --device mps

# Step 3 — build an approximate index instead of exact search
# IMPORTANT: nlist must scale with your vector count. FAISS needs
# at least nlist vectors to train that many clusters — hardcoding
# nlist=4096 will CRASH on small test runs (e.g. --limit 500).
.venv/bin/python3.11 -c "
import faiss, numpy as np, math
d = 768
vectors = np.load('embeddings/nq_embeddings.npy')
n = vectors.shape[0]

# safe formula: ~4*sqrt(n), capped so it never exceeds what you have
nlist = max(1, min(int(4 * math.sqrt(n)), n // 4, n))
print(f'n={n} vectors -> nlist={nlist}')

quantizer = faiss.IndexFlatIP(d)
index = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
index.train(vectors[:n])        # train on what you actually have
index.add(vectors)
index.nprobe = max(1, nlist // 16)   # search ~6% of clusters
faiss.write_index(index, 'ragshield_2m.index')
print('Index built:', index.ntotal, 'vectors')
"

# Step 4 — re-run the SAME evaluation harness (no code changes needed
#          in ring1_ingest.py, ring2_retrieval.py, or ring3_consensus.py)
DEMO_MODE=0 .venv/bin/python3.11 -m frontend.pages.5_Results_Dashboard
```

**What to watch for after scaling:**

```
☐ Recall check: does IndexIVFFlat still find the SAME top-5 docs
  as IndexFlatIP would, for a sample of test queries? (small
  recall loss is expected and fine — big loss means nprobe is too low)
☐ Memory usage during index.add() — monitor with Activity Monitor,
  should stabilize around 8-10GB for 2.6M × 768-dim vectors
☐ Query latency — should stay under ~100ms even at 2.6M scale with
  a well-tuned nprobe
```

[⬆ Back to top](#top)

---

<a id="f-viva-practice"></a>
## F. Viva-Style Practice Questions

**Q1. What does "P = S + I" mean?**
> The formula for a poison document. S = search-trigger (gets it
> retrieved), I = injection (the actual lie). Together = one
> poison document.

**Q2. Why does Ring 1 use max() instead of averaging the three scores?**
> max() means ANY single strong signal blocks the doc — deliberately
> aggressive. Averaging would let a weak detector dilute a strong
> signal from another, letting poison through.

**Q3. What happens if Ring 1 blocks ALL retrieved documents?**
> The fallback fires — retrieves a wider pool (30 docs instead of
> 5), strips anything labelled POISONED, returns the top-5 clean.

**Q4. Why is retrieval_score weighted LOWEST (0.20) in Ring 2?**
> Poison is specifically engineered to score HIGH on retrieval
> similarity (that's the "S" in P=S+I). Trusting it heavily would
> favour the attacker, so we weight it least.

**Q5. Can a clean document ever be dropped by Ring 2?**
> Only if consistency AND retrieval score are both extremely low —
> but provenance alone (0.45×1.0=0.45) already exceeds the 0.35
> drop threshold, so a properly-labelled clean doc always survives.

**Q6. Why three DIFFERENT LLM companies instead of one strong model?**
> Different training data and safety approaches mean a poison doc
> that fools Claude might not fool Mistral or LLaMA the same way.
> Diversity of failure IS the defense mechanism.

**Q7. What is "candidate-aware matching" and why was it needed?**
> Checks whether all significant words of a candidate answer appear
> in the LLM's response, instead of requiring an exact string match.
> Needed because Claude often phrases answers more verbosely than
> Mistral or LLaMA even when all three agree on the same fact.

**Q8. Does scaling to 2 million documents change any ring's formula?**
> No. Ring 1 operates on one document at a time, Ring 2 on the
> retrieved top-K set only, Ring 3 on LLM text answers — none
> reference total KB size. Only the FAISS index type changes,
> from exact (IndexFlatIP) to approximate (IndexIVFFlat).

**Q9. Is RAG-Shield tested against an adaptive attacker?**
> Not yet — an honest, stated limitation. Current evaluation is
> against PoisonedRAG-style poison. Testing against an attacker
> aware of our exact thresholds is planned future work.

**Q10. Why is RAG-Shield's approach called "black-box"?**
> It never needs access to a model's internal weights or attention
> matrices — only normal text-in, text-out API calls. Works
> identically on closed APIs (Claude, GPT-4) and open local models.

[⬆ Back to top](#top)

---

<a id="g-mnemonics"></a>
## G. Mnemonics

```
I-R-C           → Ingest, Retrieval, Consensus (the 3 rings)
                  "I-R-C, easy as ABC"

BAPS            → Black-box, All-3-stages, Pipeline, Scalable
                  (our 4 advantages over every competitor)

"same math,     → the scaling answer in 4 words:
 bigger index"     formulas unchanged, only FAISS index type changes

"venv python    → always run scripts through .venv/bin/python3.11,
 not system      never bare "python3" — avoids version-mismatch
 python"          errors like int|None syntax failures
```

[⬆ Back to top](#top)

---

<a id="h-cheatsheet"></a>
## H. Cheatsheet — Commands in One Block

```bash
# Full daily routine:
cd poisonedrag-ragshield-group6-iitj
ps aux | grep -i ollama
DEMO_MODE=0 .venv/bin/python3.11 backends_status.py
DEMO_MODE=0 bash run_live.sh &
bash tail_logs.sh

# Instant fallback if anything breaks:
DEMO_MODE=1 .venv/bin/python3.11 -m streamlit run frontend/app.py

# Scaling test run (always start small):
.venv/bin/python3.11 build_embeddings.py --dataset nq --device cpu --limit 5000
```

[⬆ Back to top](#top)

---

<a id="i-exam-hacks"></a>
## I. Exam Hacks — Last-Minute Survival

```
If asked to derive a Ring score by hand:
  → go to NUMERICALS.md Section D/E/F, copy the exact formula,
    plug in given numbers, show every step

If asked "why not one bigger LLM instead of 3?":
  → "Defense-in-depth. A single point of failure, however strong,
     is still ONE point an attacker only needs to beat once."

If asked "does this scale to millions of documents?":
  → "Yes — Ring 1/2/3 formulas are scale-invariant. Only the FAISS
     index type changes from exact (IndexFlatIP) to approximate
     (IndexIVFFlat). See Numericals Section H for the full proof."

If the demo crashes mid-presentation:
  → DEMO_MODE=1 fallback (Section D above) — same story, same
    numbers, zero API dependency, restarts in seconds

If asked about current limitations:
  → be honest: "5K documents / 10 questions currently — actively
    scaling to the full 2.6M-passage NQ corpus as part of the
    production expansion plan"
```

[⬆ Back to top](#top)

---

## 🔚 BOTTOM NAVIGATION — Jump to any file

**Previous:** [RAGSHIELD_THEORY.md](RAGSHIELD_THEORY.md#top) (the story) → [RAGSHIELD_NUMERICALS.md](RAGSHIELD_NUMERICALS.md#top) (the math) → **This file:** RAGSHIELD_PRACTICE.md (running it)

[🏠 Repo Home](../../README.md) &nbsp;·&nbsp; [📂 Docs Index](../README.md) &nbsp;·&nbsp; [📘 Theory](RAGSHIELD_THEORY.md#top) &nbsp;·&nbsp; [🧮 Numericals](RAGSHIELD_NUMERICALS.md#top) &nbsp;·&nbsp; [🛠️ Practice (you are here)](#top)

[⬆ Back to top](#top)
