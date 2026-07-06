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
- [B. The Three DEMO_MODE Flags — Complete Command Reference](#b-three-modes)
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

<a id="b-three-modes"></a>
## B. The Three DEMO_MODE Flags — Complete Command Reference

RAG-Shield has THREE modes, all controlled by one environment
variable. Full conceptual explanation in
[RAGSHIELD_THEORY.md, Section I](RAGSHIELD_THEORY.md#i-three-modes);
the exact code logic in
[RAGSHIELD_NUMERICALS.md, Section I](RAGSHIELD_NUMERICALS.md#i-demo-mode-logic).
This section is the practical, copy-paste command reference for
all three.

### B.1 — DEMO_MODE=1 (Default) — Small KB, Fake LLMs

```bash
# Optional pre-flight — even in mock mode, this confirms your real
# LLM keys ALSO work, in case you want to switch modes later:
DEMO_MODE=1 .venv/bin/python3.11 backends_status.py

# No need to even set the flag — this is the default if unset
.venv/bin/python3.11 -m streamlit run frontend/app.py

# Or explicitly:
DEMO_MODE=1 .venv/bin/python3.11 -m streamlit run frontend/app.py
```

**What you get:** the small 12-document built-in KB, mock/fake LLM
answers (no API calls, no cost, no internet needed). Use this for
instant local testing of the RING LOGIC itself, without touching
any real AI models.

### B.2 — DEMO_MODE=0 — Small KB, REAL LLMs (Your Live Demo)

```bash
# Pre-flight — confirm all 3 LLMs are reachable
DEMO_MODE=0 .venv/bin/python3.11 backends_status.py

# Start the app
DEMO_MODE=0 bash run_live.sh

# Watch the live decision log (separate terminal)
bash tail_logs.sh
```

**What you get:** the SAME small 12-document built-in KB as
DEMO_MODE=1, but now REAL calls to Claude, Mistral, and LLaMA. This
is what you run for your actual viva/demo — same questions, real AI
brains.

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

### B.3 — DEMO_MODE=2 (NEW) — YOUR Large Dataset, REAL LLMs

```bash
# Step 1 — build embeddings for your dataset (start SMALL, always)
.venv/bin/python3.11 build_embeddings.py \
    --dataset nq --batch-size 256 --device mps --limit 5000

# Step 2 — build the FAISS index from those embeddings
.venv/bin/python3.11 -c "
import faiss, numpy as np, math
d = 768
vectors = np.load('embeddings/nq_embeddings.npy')
n = vectors.shape[0]
nlist = max(1, min(int(4 * math.sqrt(n)), n // 4, n))
print(f'n={n} vectors -> nlist={nlist}')
quantizer = faiss.IndexFlatIP(d)
index = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
index.train(vectors[:n])
index.add(vectors)
index.nprobe = max(1, nlist // 16)
faiss.write_index(index, 'ragshield_2m.index')
print('Index built:', index.ntotal, 'vectors')
"

# Step 3 — confirm Scale Mode is actually loading YOUR data
DEMO_MODE=2 .venv/bin/python3.11 -c "
from ragshield_core.retriever import Retriever
r = Retriever().load_kb()
print(f'Backend: {r.backend}')
print(f'Documents loaded: {len(r.docs)}')
"
# Expected output:
#   [Scale Mode] Loaded 5000 documents, FAISS index with 5000
#   vectors from ragshield_2m.index
#   Backend: scale
#   Documents loaded: 5000

# Step 3.5 — pre-flight check ALL 3 LLM backends before running
DEMO_MODE=2 .venv/bin/python3.11 backends_status.py
# Expected output:
#   DEMO_MODE=2  ->  SCALE mode: Ring 3 uses LIVE backends against
#   YOUR large dataset
#   [LIVE] Claude (Anthropic)          -> 'OK'
#   [LIVE] Mistral-Small (MistralAI)   -> 'OK'
#   [LIVE] Ollama (local Meta)         -> 'OK'
#   Ring 3 vendor diversity: (shown, same as live mode)
#   ✅  Ready for scale testing. Run: DEMO_MODE=2 bash run_live.sh

# Step 4 — run the full app against your large dataset
DEMO_MODE=2 bash run_live.sh

# Or run just the evaluation dashboard directly:
DEMO_MODE=2 .venv/bin/python3.11 -m frontend.pages.5_Results_Dashboard
```

**What you get:** REAL LLM calls (same as DEMO_MODE=0), but
retrieving from YOUR large dataset instead of the small built-in
KB. Use this to prove RAG-Shield's defense holds up at genuine
scale, not just on 5 toy questions.

### B.4 — Side-by-Side Comparison Table

```
┌───────────────┬──────────────────────┬─────────────────┬──────────────────────┐
│ Flag          │ Documents            │ LLMs            │ Command to run       │
├───────────────┼──────────────────────┼─────────────────┼──────────────────────┤
│ DEMO_MODE=1   │ 12 built-in docs     │ Mock/fake       │ streamlit run        │
│ (default)     │                      │                 │ frontend/app.py      │
├───────────────┼──────────────────────┼─────────────────┼──────────────────────┤
│ DEMO_MODE=0   │ 12 built-in docs     │ Real (Claude,   │ DEMO_MODE=0 bash     │
│               │ (5000 docs)          │ Mistral,        │ run_live.sh          │
│               │                      │ LLaMA)          │                      │
├───────────────┼──────────────────────┼─────────────────┼──────────────────────┤
│ DEMO_MODE=2   │ YOUR large dataset   │ Real (same as   │ DEMO_MODE=2 bash     │
│ (NEW)         │ (5K–2.6M docs)       │ mode 0, CMO)    │ run_live.sh          │
└───────────────┴──────────────────────┴─────────────────┴──────────────────────┘
```

**Why DEMO_MODE=2 is completely safe to add:** it's checked FIRST
in the code, before the demo/live split, and returns a totally
separate code path (`_load_scale_kb()`) that never touches the
small built-in KB logic at all. DEMO_MODE=0 and DEMO_MODE=1 run
through EXACTLY the same code they always have — see
[RAGSHIELD_NUMERICALS.md, Section I.4](RAGSHIELD_NUMERICALS.md#i-demo-mode-logic)
for the full proof.

[⬆ Back to top](#top)

---

<a id="b5-env-setup"></a>
### B.5 — Setting Up SCALE_* Variables in Your `.env` File (IMPORTANT)

**The mistake to avoid:** typing `SCALE_EMBEDDINGS_PATH=...` directly
into your terminal (as a bare command, without `export`, or even
with `export`) only sets it for the CURRENT terminal session. The
moment you close that tab or open a new one, it's gone — Scale Mode
falls back to defaults, or you get confusing "file not found" errors
even though you built the files correctly.

```
┌─────────────────────────────────────────────────────────────────┐
│  WRONG — vanishes when the terminal closes:                     │
│    SCALE_EMBEDDINGS_PATH=embeddings/nq_embeddings.npy           │
│    SCALE_FAISS_INDEX_PATH=ragshield_2m.index                    │
│                                                                 │
│  RIGHT — saved permanently, loaded automatically every run:     │
│    (add these two lines INTO your .env file itself)             │
└─────────────────────────────────────────────────────────────────┘
```

**The fix — add these lines to your actual `.env` file:**

```bash
vim .env
# (or use any text editor — nano, VS Code, whatever you prefer)

# Add these lines anywhere in the file:
SCALE_EMBEDDINGS_PATH=embeddings/nq_embeddings.npy
SCALE_FAISS_INDEX_PATH=ragshield_2m.index
```

**Real terminal walkthrough — exactly what this looks like in practice:**

```bash
➜  Major-Project-PoisonedRAG git:(feat/build_embeddings) ✗ vim .env
# (opens your .env file — add the two SCALE_* lines, save, quit)

➜  Major-Project-PoisonedRAG git:(feat/build_embeddings) ✗ .venv/bin/python3.11 build_embeddings.py \
    --dataset nq --batch-size 256 --device mps --limit 100000

============================================================
  RAG-Shield Embedding Builder
============================================================
  Dataset:     nq
  Batch size:  256
  Device:      mps
  Limit:       100000
  Output:      embeddings/nq_embeddings.npy
============================================================
Loading all-mpnet-base-v2 model...
Warning: You are sending unauthenticated requests to the HF Hub.
Please set a HF_TOKEN to enable higher rate limits and faster
downloads.
Loading weights: 100%|████████████| 199/199 [00:00<00:00, 5699.87it/s]
Downloading/loading Natural Questions corpus...
Using the latest cached version of the dataset since
natural_questions couldn't be found on the Hugging Face Hub
Found the latest cached dataset configuration 'default'...
Loading dataset shards: 100%|████████| 235/235 [00:22<00:00, 10.50it/s]
```

**Reading this output, line by line (same pattern as the smaller
5,000-doc run explained in
[Section E](#e-scaling-steps)):**

```
"Limit: 100000" instead of 5000
  → you're stepping UP in scale, exactly as recommended:
    5,000 → 50,000/100,000 → full corpus. Good discipline.

Everything else in this output means the SAME as your earlier
5,000-doc run — same model loading, same cached dataset lookup,
same shard loading. The ONLY difference is the bigger --limit
number, so it will take proportionally longer to finish embedding
(roughly 20x longer than the 5,000-doc run, since 100,000 is 20x
more documents).
```

#### Why This Is Completely Safe With Git — Nothing Gets Overwritten

**Your exact worry — "make sure whenever git pull or push happens
it doesn't change anything" — has a clean answer: `.env` is already
protected by `.gitignore`.**

```
┌─────────────────────────────────────────────────────────────────┐
│  .gitignore already contains:                                   │
│      .env                                                       │
│      .env.*                                                     │
│                                                                 │
│  This means:                                                    │
│    - Your REAL .env file (with real API keys, real paths)       │
│      NEVER gets committed, pushed, or pulled — git pretends     │
│      it doesn't exist                                           │
│    - Only .env.example (a TEMPLATE with fake placeholder        │
│      values, no real secrets) is tracked in git                 │
│    - When a teammate pulls your latest code, they get the       │
│      UPDATED .env.example (showing them which new variables     │
│      exist), but their OWN .env file — with their own keys      │
│      and paths — is completely untouched                        │
└─────────────────────────────────────────────────────────────────┘
```

**Quick verification — confirm your `.env` is protected right now:**

```bash
git check-ignore -v .env
# Expected output: .gitignore:9:.env    .env
# If you see this, your .env is safely ignored by git.
# If you see NOTHING printed, your .env is NOT ignored —
# stop and fix your .gitignore before continuing, to avoid
# accidentally committing your real API keys.
```

**What DOES get committed (the safe, shared template):**

```bash
# .env.example — this file has NO real secrets, just placeholder
# text showing WHICH variables exist and what format they expect.
# This is the file that goes into git and gets shared with
# teammates / graders / anyone who clones the repo.

OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
MISTRAL_API_KEY=your-mistral-key-here
MISTRAL_MODEL=mistral-small-latest
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_PANEL=llama3.2:3b,phi4-mini:latest

VLLM_BASE_URL=
VLLM_API_KEY=vllm
VLLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct

# ---- Scale Mode (DEMO_MODE=2) ----
SCALE_EMBEDDINGS_PATH=embeddings/nq_embeddings.npy
SCALE_FAISS_INDEX_PATH=ragshield_2m.index
SCALE_META_PATH=embeddings/nq_embeddings.meta.json
```

**One-sentence summary:** editing your real `.env` file to add
`SCALE_*` variables is completely private and permanent — it never
touches git at all, so future `git pull`/`git push` commands will
never overwrite, remove, or even see your local `.env` changes.

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
       (or however many questions your active mode's dataset has)
  Proves: the headline number is real, computed live — works
          identically whether you're in DEMO_MODE=0 or DEMO_MODE=2
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

ERROR: DEMO_MODE=0 gives backend "demo" instead of "faiss"
       (you expected real FAISS search but got the small demo KB)
FIX:   This was a real bug — retriever_backend()'s fallback line
       used to default RETRIEVER to "tfidf" (treated as demo-style)
       instead of "faiss" (real search) when RETRIEVER wasn't set.

       THE FIX (already applied in config.py):
         # before:
         return os.getenv("RETRIEVER", "tfidf")
         # after:
         return os.getenv("RETRIEVER", "faiss")

       Verify the fix is active:
         DEMO_MODE=0 .venv/bin/python3.11 -c "
         from ragshield_core.retriever import Retriever
         print(Retriever().load_kb().backend)"
         # should print: faiss

       Full explanation of every line of this fix:
       see RAGSHIELD_NUMERICALS.md, Section I.4.

       CONFIRMED WORKING — actual verified output, all 3 modes:
         DEMO_MODE=0 .venv/bin/python3.11 -c "from ragshield_core.retriever import Retriever; print(Retriever().load_kb().backend)"
         -> faiss

         DEMO_MODE=1 .venv/bin/python3.11 -c "from ragshield_core.retriever import Retriever; print(Retriever().load_kb().backend)"
         -> demo

         DEMO_MODE=2 .venv/bin/python3.11 -c "from ragshield_core.retriever import Retriever; print(Retriever().load_kb().backend)"
         -> [Scale Mode] Loaded 5000 documents, FAISS index with 5000 vectors from ragshield_2m.index
         -> scale

ERROR: backends_status.py always prints "DEMO mode: 3 MOCK LLMs"
       even under DEMO_MODE=2, even though it's actually pinging
       REAL Claude/Mistral/Ollama and getting [LIVE] for all three
FIX:   This was a SECOND, SEPARATE bug from the retriever one above.
       backends_status.py had its OWN hardcoded copy of the mode
       check, written BEFORE DEMO_MODE=2 existed:

         # OLD, buggy line (only knew about 2 modes):
         demo = os.getenv("DEMO_MODE", "1") not in ("0", "false", "False")
         # DEMO_MODE=2 falls into the "not in" list -> demo=True
         # -> wrongly prints "DEMO mode: 3 MOCK LLMs"
         # even though it just successfully pinged 3 REAL backends

       THE FIX: import the SAME functions the rest of the app
       already uses, instead of recalculating locally:
         from ragshield_core import config
         is_demo  = config.demo_mode()
         is_scale = config.scale_mode()
         is_live  = (not is_demo) and (not is_scale)

       This guarantees backends_status.py can NEVER drift out of
       sync with config.py again — there is only ONE place that
       decides what each DEMO_MODE value means.

       CONFIRMED WORKING — actual verified output, all 3 modes:

         DEMO_MODE=1 .venv/bin/python3.11 backends_status.py
         -> DEMO_MODE=1  ->  DEMO mode: Ring 3 uses 3 MOCK LLMs (no network)
         -> [LIVE] Claude / Mistral / Ollama all OK
         -> Live backends : ['Claude', 'Mistral', 'LLaMA']
         -> Ring 3 panel  : 3 vendor(s) active

         DEMO_MODE=0 .venv/bin/python3.11 backends_status.py
         -> DEMO_MODE=0  ->  LIVE mode: Ring 3 uses the live backends below
         -> [LIVE] Claude / Mistral / Ollama all OK
         -> Ring 3 vendor diversity: Claude->Anthropic, Mistral->Mistral AI,
            LLaMA->Meta
         -> ✅ Ready for demo. Run: DEMO_MODE=0 bash run_live.sh

         DEMO_MODE=2 .venv/bin/python3.11 backends_status.py — FULL
         REAL OUTPUT (exactly as it appears on your terminal):

           DEMO_MODE=2  ->  SCALE mode: Ring 3 uses LIVE backends against YOUR large dataset
           Pinging backends:
             [LIVE] Claude (Anthropic)     -> 'OK'  (1120 ms)
             [LIVE] Mistral-Small (MistralAI) -> 'OK'  (588 ms)
             [LIVE] Ollama (local Meta)    -> 'ok'  (540 ms)
           Live backends : ['Claude', 'Mistral', 'LLaMA']
           Ring 3 panel  : 3 vendor(s) active
           Ring 3 vendor diversity:
             Claude   -> Anthropic  (US, Constitutional AI)
             Mistral  -> Mistral AI (France, EU-trained)
             LLaMA    -> Meta       (US, open-weight, local)
           ✅  Ready for scale testing. Run: DEMO_MODE=2 bash run_live.sh

         Banner correctly says "SCALE mode" now (was wrongly "DEMO
         mode" before the fix) — this is the confirmed, working,
         fixed behaviour running on a real machine, real API keys,
         real Ollama.

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
FIX:   This is just a WARNING, not an error — safe to ignore.

ERROR: DEMO_MODE=2 raises "FileNotFoundError: DEMO_MODE=2 (Scale
        Mode) requires two files that don't exist yet"
FIX:   You haven't built the embeddings/index files yet. Follow
       Section B.3 above, Steps 1-2, before trying Step 3 or 4.

ERROR: process gets "killed" partway through embedding a huge
       dataset (e.g. running WITHOUT --limit on the full 2.6M docs)
FIX:   Your machine likely ran out of memory holding that many
       documents at once. ALWAYS test with --limit first:
         --limit 5000    (few minutes)
         --limit 50000   (tens of minutes)
         --limit 500000  (a few hours)
         (no --limit)    (full 2.6M — only after the above all
                          worked, budget most of a day, or run
                          overnight)

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
— only the infrastructure around retrieval does.**

```bash
# Step 1 — get the Natural Questions corpus
pip install datasets

# Step 2 — embed documents, ALWAYS starting small
.venv/bin/python3.11 build_embeddings.py \
    --dataset nq --batch-size 256 --device mps --limit 5000

# if that works cleanly, scale up gradually:
.venv/bin/python3.11 build_embeddings.py \
    --dataset nq --batch-size 256 --device mps --limit 100000

# only once THAT works, run the full corpus (budget several hours):
.venv/bin/python3.11 build_embeddings.py \
    --dataset nq --batch-size 256 --device mps

# Step 3 — build an approximate index instead of exact search
.venv/bin/python3.11 -c "
import faiss, numpy as np, math
d = 768
vectors = np.load('embeddings/nq_embeddings.npy')
n = vectors.shape[0]
nlist = max(1, min(int(4 * math.sqrt(n)), n // 4, n))
print(f'n={n} vectors -> nlist={nlist}')
quantizer = faiss.IndexFlatIP(d)
index = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
index.train(vectors[:n])
index.add(vectors)
index.nprobe = max(1, nlist // 16)
faiss.write_index(index, 'ragshield_2m.index')
print('Index built:', index.ntotal, 'vectors')
"

# Step 4 — re-run the SAME evaluation harness using DEMO_MODE=2
DEMO_MODE=2 .venv/bin/python3.11 -m frontend.pages.5_Results_Dashboard
```

**What comes after Step 4 — finishing the full scale-up:**

```bash
# Step 5 — verify search QUALITY didn't degrade too much
.venv/bin/python3.11 -c "
import faiss, numpy as np
exact = faiss.read_index('ragshield_exact_baseline.index')
approx = faiss.read_index('ragshield_2m.index')
test_queries = np.load('embeddings/test_queries.npy')
exact_scores, exact_ids = exact.search(test_queries, 5)
approx_scores, approx_ids = approx.search(test_queries, 5)
matches, total = 0, 0
for e_row, a_row in zip(exact_ids, approx_ids):
    matches += len(set(e_row) & set(a_row))
    total += 5
recall = matches / total
print(f'Recall vs exact search: {recall:.1%}')
print('Target: 90%+ recall is considered production-safe')
"

# Step 6 — if recall is too low, increase nprobe and re-test
#   index.nprobe = 64   # try doubling it, re-run Step 5

# Step 7 — confirm Ring 1/2/3 still produce expected ASR at scale
DEMO_MODE=2 .venv/bin/python3.11 -m frontend.pages.5_Results_Dashboard

# Step 8 — point the live app permanently at your new index by
#          adding these lines to your ACTUAL .env file (not just
#          setting them as one-off shell exports, which vanish when
#          you close the terminal). Open .env and add:
#
#   SCALE_EMBEDDINGS_PATH=embeddings/nq_embeddings.npy
#   SCALE_FAISS_INDEX_PATH=ragshield_2m.index
#
# See Section B.5 below for the full explanation of why this matters
# and a copy-paste-ready block for your .env file.

# Step 9 — document final numbers: vector count, nlist/nprobe used,
#          measured recall, measured latency, ASR consistency
```

**Checklist — you're fully done scaling when:**

```
☐ Full 2.6M-document corpus embedded (not just a --limit slice)
☐ IndexIVFFlat built and trained on the FULL vector set (or a
  large representative sample, 100K+ vectors)
☐ Recall vs exact search measured and above ~90%
☐ Query latency confirmed under ~100ms per search
☐ Full RAG-Shield evaluation harness re-run successfully under
  DEMO_MODE=2
☐ ASR numbers at scale documented and compared to small-scale
  numbers (they should be similar — Ring 1/2/3 math is unchanged)
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

**Q11. Why add DEMO_MODE=2 instead of just modifying DEMO_MODE=0
to load the big dataset?**
> Safety and reversibility. DEMO_MODE=0 and DEMO_MODE=1 are your
> proven, working demo/live paths — they must never break,
> especially right before a viva or presentation. Adding a third
> VALUE to the same variable is purely additive: every existing
> command you already use keeps working byte-for-byte identically.
> If Scale Mode ever has a bug, it only affects DEMO_MODE=2 — your
> demo (1) and live (0) paths are completely unaffected because
> the code checks scale_mode() first and returns early, never
> touching the original demo/live logic underneath.

**Q12. What was the actual bug found in retriever_backend(), and
how do you know the fix didn't break anything?**
> The function's final fallback line defaulted RETRIEVER to
> "tfidf" when unset, but the Retriever class treats "tfidf" as
> demo-style backend rather than real FAISS search. So DEMO_MODE=0
> alone silently gave you the small demo KB, not real live search.
> The fix changes only the DEFAULT VALUE of that one os.getenv()
> call, from "tfidf" to "faiss". Verified safe by testing 4
> scenarios directly: DEMO_MODE=1 unaffected, DEMO_MODE=0 with
> RETRIEVER unset now correctly gives "faiss", DEMO_MODE=0 with
> RETRIEVER=tfidf explicitly set still respects that override, and
> DEMO_MODE=2 unaffected.

**Q13. There were TWO separate bugs related to DEMO_MODE=2 — what
was the second one, and why is importing config.py directly a
better fix than writing a new local calculation?**
> The second bug was in backends_status.py — a standalone script
> with its OWN hardcoded copy of the mode-detection logic, written
> before DEMO_MODE=2 existed. It only checked for 2 modes, so
> DEMO_MODE=2 fell into its "not demo" exclusion list incorrectly,
> causing it to print "DEMO mode: 3 MOCK LLMs" even while
> successfully pinging 3 REAL backends. The fix imports demo_mode()
> and scale_mode() directly from config.py instead of recalculating
> them locally — this means there is now only ONE authoritative
> place in the entire codebase that decides what each DEMO_MODE
> value means, so this exact class of bug (two files disagreeing
> about mode logic) cannot happen again.

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

0-1-2 = GEARS   → the three DEMO_MODE values, easiest way to remember:
                  1 = small KB + fake LLMs   (first gear)
                  0 = small KB + real LLMs   (second gear)
                  2 = BIG KB + real LLMs     (third gear, NEW)
                 "0 and 1 stay small. 2 goes big."

"faiss not      → the exact one-word fix for the retriever_backend()
 tfidf"           bug: change the DEFAULT string from "tfidf" to
                  "faiss" so DEMO_MODE=0 means real search by default

"ONE SOURCE OF  → the fix for the backends_status.py bug: it now
 TRUTH"           IMPORTS demo_mode()/scale_mode() from config.py
                  instead of recalculating its own copy — one file
                  decides mode logic, everyone else just asks it
```

[⬆ Back to top](#top)

---

<a id="h-cheatsheet"></a>
## H. Cheatsheet — Commands in One Block

```bash
# ── DEMO_MODE=1 — instant, no keys needed ──
DEMO_MODE=1 .venv/bin/python3.11 backends_status.py   # optional pre-flight
.venv/bin/python3.11 -m streamlit run frontend/app.py

# ── DEMO_MODE=0 — your live demo, real LLMs, small KB ──
cd poisonedrag-ragshield-group6-iitj
ps aux | grep -i ollama
DEMO_MODE=0 .venv/bin/python3.11 backends_status.py
DEMO_MODE=0 bash run_live.sh &
bash tail_logs.sh

# ── DEMO_MODE=2 — YOUR large dataset, real LLMs ──
.venv/bin/python3.11 build_embeddings.py --dataset nq --device mps --limit 5000
# (build the FAISS index — see Section E, Step 3)
DEMO_MODE=2 .venv/bin/python3.11 backends_status.py
DEMO_MODE=2 bash run_live.sh
# quick check Scale Mode is really loading your data:
DEMO_MODE=2 .venv/bin/python3.11 -c "from ragshield_core.retriever import Retriever; r=Retriever().load_kb(); print(r.backend, len(r.docs))"

# ── Verify all 3 backend/mode combinations in one go (copy-paste all) ──
for mode in 1 0 2; do
  echo "=== DEMO_MODE=$mode ==="
  DEMO_MODE=$mode .venv/bin/python3.11 -c "from ragshield_core.retriever import Retriever; print(Retriever().load_kb().backend)"
done

# ── Instant fallback if anything breaks ──
DEMO_MODE=1 .venv/bin/python3.11 -m streamlit run frontend/app.py
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

If asked "how many modes does your system have, and why?":
  → "Three — DEMO_MODE 0, 1, and 2. Mode 1 is instant testing with
     fake LLMs. Mode 0 is the real demo with real LLMs on a small
     KB. Mode 2 is the same real LLMs but tested against a large,
     real-world-scale dataset — added as a pure extension, never
     touching the existing 0/1 code paths."

If the demo crashes mid-presentation:
  → DEMO_MODE=1 fallback (Section D above) — same story, same
    numbers, zero API dependency, restarts in seconds

If asked about current limitations:
  → be honest: "5K documents / 10 questions currently — actively
    scaling to the full 2.6M-passage NQ corpus as part of the
    production expansion plan, using DEMO_MODE=2"
```

[⬆ Back to top](#top)

---

## 🔚 BOTTOM NAVIGATION — Jump to any file

**Previous:** [RAGSHIELD_THEORY.md](RAGSHIELD_THEORY.md#top) (the story) → [RAGSHIELD_NUMERICALS.md](RAGSHIELD_NUMERICALS.md#top) (the math) → **This file:** RAGSHIELD_PRACTICE.md (running it)

[🏠 Repo Home](../../README.md) &nbsp;·&nbsp; [📂 Docs Index](../README.md) &nbsp;·&nbsp; [📘 Theory](RAGSHIELD_THEORY.md#top) &nbsp;·&nbsp; [🧮 Numericals](RAGSHIELD_NUMERICALS.md#top) &nbsp;·&nbsp; [🛠️ Practice (you are here)](#top)

[⬆ Back to top](#top)
