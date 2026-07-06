<a id="top"></a>

# 🛠️ RAGSHIELD_PRACTICE.md — Run It, Break It, Fix It
### Commands, troubleshooting, and viva-style practice questions

---

## 🔝 TOP NAVIGATION — Jump to any file

**Previous:** [RAGSHIELD_THEORY.md](RAGSHIELD_THEORY.md#top) (the story) → [RAGSHIELD_NUMERICALS.md](RAGSHIELD_NUMERICALS.md#top) (the math) → **This file:** RAGSHIELD_PRACTICE.md (running it)

[🏠 Repo Home](../../README.md) &nbsp;·&nbsp; [📂 Docs Index](../README.md) &nbsp;·&nbsp; [📘 Theory](RAGSHIELD_THEORY.md#top) &nbsp;·&nbsp; [🧮 Numericals](RAGSHIELD_NUMERICALS.md#top) &nbsp;·&nbsp; [🛠️ Practice (you are here)](#top) &nbsp;·&nbsp; [🔍 FAISS Deep-Dive](RAGSHIELD_FAISS.md#top)

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
- [E.1 Real Terminal Run — What You'll Actually See](#e1-terminal-walkthrough)
- [E.2 Line-by-Line — The Safe Index-Building Script](#e2-line-by-line)
- [E.3 What Comes After Step 4 — Finishing the 2M-Doc Scale-Up](#e3-post-step4)
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

<a id="e1-terminal-walkthrough"></a>
### E.1 — Real Terminal Run — What You'll Actually See

This is a REAL run, copied from an actual terminal session of my MBP Machine, showing
the exact crash-then-fix journey — so you know it's normal to hit
this once, and exactly how to read the messages.

```
ATTEMPT 1 — hardcoded nlist=4096, only 500 vectors on disk
──────────────────────────────────────────────────────────

.venv/bin/python3.11 -c "
import faiss, numpy as np
d = 768
vectors = np.load('embeddings/nq_embeddings.npy')
quantizer = faiss.IndexFlatIP(d)
nlist = 4096
index = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
index.train(vectors[:200000])
index.add(vectors)
index.nprobe = 32
faiss.write_index(index, 'ragshield_2m.index')
print('Index built:', index.ntotal, 'vectors')
"

RuntimeError: ... 'nx >= static_cast<idx_t>(k)' failed:
Number of training points (500) should be at least as
large as number of clusters (4096)

WHAT THIS MEANS IN PLAIN WORDS:
  You told FAISS "sort my books into 4096 labeled bins."
  You only HAVE 500 books. You can't fill 4096 bins with 500 books
  — most bins would be completely empty, which breaks the maths
  FAISS uses to build those bins in the first place.
```

```
ATTEMPT 2 — manually lowered nlist to 89, still shows a WARNING
────────────────────────────────────────────────────────────────

nlist = 89   (a guess — closer, but still not quite right)

WARNING clustering 500 points to 89 centroids: please provide
at least 3471 training points
Index built: 500 vectors

WHAT THIS MEANS:
  It didn't crash this time — 89 is small enough to actually work.
  But FAISS is still politely warning you: "this works, but 89
  bins is more than ideal for only 500 books — quality of the
  bins won't be great." It's a WARNING, not an ERROR, so the
  script finishes and the index gets saved — just not perfectly
  tuned. This is fine for a quick test, not fine for production.
```

```
ATTEMPT 3 — the RIGHT way: run the full pipeline script instead
──────────────────────────────────────────────────────────────────

.venv/bin/python3.11 build_embeddings.py \
    --dataset nq --batch-size 256 --device mps --limit 5000

============================================================
  RAG-Shield Embedding Builder
============================================================
  Dataset:     nq
  Batch size:  256
  Device:      mps
  Limit:       5000
  Output:      embeddings/nq_embeddings.npy
============================================================

Loading all-mpnet-base-v2 model...
Warning: You are sending unauthenticated requests to the HF Hub.
Please set a HF_TOKEN to enable higher rate limits and faster
downloads.
Loading weights: 100%|████████████| 199/199 [00:00<00:00, 6421.40it/s]

Downloading/loading Natural Questions corpus...
Using the latest cached version of the dataset since
natural_questions couldn't be found on the Hugging Face Hub
Found the latest cached dataset configuration 'default'...
Loading dataset shards: 100%|████████| 235/235 [00:23<00:00]
Loaded 5000 documents from Natural Questions (limited to 5000).

Embedding 5000 documents (batch size 256, device mps)...
This is the slow part. Progress will print periodically.

Batches: 75%|███████████████        | 15/20 [02:42<00:36, ...]
```

**How to read each of these lines, one at a time:**

```
"Warning: You are sending unauthenticated requests to the HF Hub"
  → HF = Hugging Face, the site that hosts the AI model and dataset
    files. This just means you haven't logged in with a free
    account token. Totally safe to ignore for small/test runs —
    only matters if you're downloading huge amounts repeatedly and
    want faster/more reliable downloads. Not an error.

"Loading weights: 100%|████| 199/199 [00:00<00:00, 6421.40it/s]"
  → This is the all-mpnet-base-v2 model's internal numbers being
    loaded into memory. 199/199 means all 199 pieces loaded.
    6421 "it/s" = how fast each piece loaded. This finished
    basically instantly here.

"Using the latest cached version of the dataset since
 natural_questions couldn't be found on the Hugging Face Hub"
  → Translation: "I tried to check online for the newest version
    of this dataset, couldn't reach it (or it's not published
    there under that exact name anymore), so I'm using the copy
    you already downloaded before, sitting in your local cache
    folder." This is FINE — you already have the data, no need
    to worry.

"Found the latest cached dataset configuration 'default' at
 /Users/rohitpatel/.cache/huggingface/datasets/..."
  → This is just telling you WHERE on your hard drive it found
    the cached copy. You'll rarely need this path yourself.

"Loading dataset shards: 100%|████| 235/235 [00:23<00:00]"
  → The Natural Questions dataset is split into 235 "shard" files
    (like 235 separate boxes instead of one giant box, for easier
    handling). All 235 loaded in 23 seconds.

"Loaded 5000 documents from Natural Questions (limited to 5000)."
  → Confirms your --limit 5000 flag worked — it only pulled the
    first 5000 documents, not the entire 2.6-million-document
    corpus. Good for testing.

"Embedding 5000 documents (batch size 256, device mps)..."
  → NOW the actual slow part begins: turning each of those 5000
    text documents into a 768-number vector, using your Mac's
    Apple GPU (mps), in batches of 256 documents at a time.

"Batches: 75%|███████| 15/20 [02:42<00:36, ...]"
  → Progress bar. 5000 documents ÷ 256 per batch ≈ 20 batches
    total. 15 out of 20 done = 75%. "02:42<00:36" means
    2 minutes 42 seconds have passed, roughly 36 seconds left.
```

[⬆ Back to top](#top)

---

<a id="e2-line-by-line"></a>
### E.2 — Line-by-Line — The Safe Index-Building Script

Here is the EXACT fixed script from earlier, explained one line
at a time, assuming zero prior knowledge of any single word in it.

```python
.venv/bin/python3.11 -c "
import faiss, numpy as np, math
```
> **Line 1 (the shell command wrapper):** `.venv/bin/python3.11 -c "..."`
> means "run Python from inside my project's own private toolbox
> (`.venv`), and the code to run is everything inside these quote
> marks." Using `-c` lets you run a short script directly from the
> terminal without saving it to a `.py` file first.
>
> **Line 2:** `import faiss, numpy as np, math` loads three toolkits:
> - `faiss` — the fast vector-search library (see the dedicated
>   [RAGSHIELD_FAISS.md](RAGSHIELD_FAISS.md#top) guide)
> - `numpy as np` — a library for working with big lists/grids of
>   numbers efficiently; `as np` just means "call it np for short"
> - `math` — Python's built-in toolkit for things like square roots

```python
d = 768
```
> **Line 3:** creates a variable named `d` (short for "dimension")
> and sets it to 768 — the number of numbers in each vector, because
> that's what `all-mpnet-base-v2` outputs (see
> [RAGSHIELD_NUMERICALS.md](RAGSHIELD_NUMERICALS.md#notation) for
> what a "dimension" means).

```python
vectors = np.load('embeddings/nq_embeddings.npy')
```
> **Line 4:** opens the file `embeddings/nq_embeddings.npy` (the
> `.npy` file you created earlier with `build_embeddings.py`) and
> loads all the saved vectors into a variable called `vectors`.
> Think of this as "open the box of pre-measured ingredients you
> prepared earlier."

```python
n = vectors.shape[0]
```
> **Line 5:** `vectors.shape` tells you the SIZE of the vectors grid
> — it returns something like `(5000, 768)`, meaning 5000 rows
> (documents) by 768 columns (numbers per document). `.shape[0]`
> grabs just the FIRST number in that pair — how many documents
> (rows) you actually have. This is stored in `n`.

```python
# safe formula: ~4*sqrt(n), capped so it never exceeds what you have
nlist = max(1, min(int(4 * math.sqrt(n)), n // 4, n))
```
> **Line 6 (comment):** starts with `#`, which means "this line is
> a note for humans, Python ignores it completely."
>
> **Line 7 — the actual safe formula, broken into pieces:**
> - `math.sqrt(n)` — the square root of n (e.g. if n=5000,
>   `sqrt(5000) ≈ 70.7`)
> - `4 * math.sqrt(n)` — multiply that by 4 (a commonly-used rule
>   of thumb in FAISS's own documentation for choosing a reasonable
>   number of clusters)
> - `int(...)` — round it down to a whole number (you can't have
>   70.7 clusters, only whole clusters)
> - `n // 4` — n divided by 4, rounded down (the `//` symbol means
>   "divide and throw away any leftover remainder")
> - `min(int(4*sqrt(n)), n // 4, n)` — take the SMALLEST of these
>   three numbers, as a safety net, so nlist is never accidentally
>   bigger than what your data can actually support
> - `max(1, ...)` — on the OUTSIDE, make sure the final answer is
>   never less than 1 (you always need at least 1 cluster)
>
> **In plain words:** "figure out a sensible number of storage bins
> for however many documents I actually have — never more bins
> than documents allow."

```python
print(f'n={n} vectors -> nlist={nlist}')
```
> **Line 8:** prints a message to the screen showing exactly what
> values were calculated, so you can SEE the numbers before
> anything else happens. The `f'...'` is called an "f-string" — it
> lets you drop variable values directly inside a text message
> using curly braces `{}`.

```python
quantizer = faiss.IndexFlatIP(d)
```
> **Line 9:** creates a small HELPER index using exact search
> (`IndexFlatIP` — see the dedicated
> [RAGSHIELD_FAISS.md](RAGSHIELD_FAISS.md#top) guide for full
> detail). This helper is used ONLY internally, to help sort
> vectors into their bins — it is not your final search index.

```python
index = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
```
> **Line 10:** creates your REAL index — the approximate,
> bin-sorting kind (`IndexIVFFlat`). It needs 4 pieces of
> information: the helper quantizer from Line 9, the dimension
> `d`, how many bins `nlist`, and which MATH RULE to use for
> comparing vectors (`METRIC_INNER_PRODUCT` — the same "multiply
> then add" idea from
> [RAGSHIELD_NUMERICALS.md's cosine similarity explanation](RAGSHIELD_NUMERICALS.md#d-ring1-math)).

```python
index.train(vectors[:n])
```
> **Line 11:** this is the "sort the books into bins" step. FAISS
> looks at your vectors and figures out where to draw the boundary
> lines between bins so similar vectors end up together.
> `vectors[:n]` means "use all n vectors you have" (slicing from
> the start up to n — since n already equals the full count, this
> uses everything).

```python
index.add(vectors)
```
> **Line 12:** now that the bins exist (from Line 11), actually
> PLACE every vector into its correct bin. Training decides WHERE
> the bins are; adding puts your actual data into them.

```python
index.nprobe = max(1, nlist // 16)
```
> **Line 13:** sets how many bins get CHECKED during each search —
> not all of them (that would defeat the purpose of having bins),
> just a fraction. `nlist // 16` means "roughly 1/16th, about 6%,
> of the total bins." `max(1, ...)` again ensures you check AT
> LEAST 1 bin even if nlist is tiny.

```python
faiss.write_index(index, 'ragshield_2m.index')
```
> **Line 14:** saves your finished, trained, populated index to a
> file on disk named `ragshield_2m.index`, so you don't have to
> rebuild it from scratch every time you restart your program.

```python
print('Index built:', index.ntotal, 'vectors')
"
```
> **Line 15:** prints a final confirmation message. `index.ntotal`
> is a built-in FAISS property that tells you exactly how many
> vectors ended up stored inside the index — a good sanity check
> that nothing went missing.

[⬆ Back to top](#top)

---

<a id="e3-post-step4"></a>
### E.3 — What Comes After Step 4 — Finishing the 2M-Doc Scale-Up

Once your evaluation harness runs successfully on the full-scale
index (the end of Step 4 in Section E above), here are the
remaining steps to fully complete the production-scale migration:

```bash
# Step 5 — Verify search QUALITY didn't degrade too much
# (approximate search trades a little accuracy for a lot of speed
#  — this step checks you haven't traded away TOO much accuracy)

.venv/bin/python3.11 -c "
import faiss, numpy as np

# load both the OLD exact index and the NEW approximate index
exact = faiss.read_index('ragshield_exact_baseline.index')
approx = faiss.read_index('ragshield_2m.index')

# run the same 20 test queries against both
test_queries = np.load('embeddings/test_queries.npy')

exact_scores, exact_ids = exact.search(test_queries, 5)
approx_scores, approx_ids = approx.search(test_queries, 5)

# count how many top-5 results MATCH between exact and approximate
matches = 0
total = 0
for e_row, a_row in zip(exact_ids, approx_ids):
    matches += len(set(e_row) & set(a_row))
    total += 5

recall = matches / total
print(f'Recall vs exact search: {recall:.1%}')
print('Target: 90%+ recall is considered production-safe')
"

# Step 6 — If recall is too low (below ~90%), increase nprobe
# and re-test — this is the main knob to trade speed for accuracy
#   index.nprobe = 64   # try doubling it, re-run Step 5

# Step 7 — Re-run the FULL RAG-Shield evaluation harness at scale
# to confirm Ring 1/2/3 still produce the expected ASR numbers
# with the new index in place
DEMO_MODE=0 .venv/bin/python3.11 -m frontend.pages.5_Results_Dashboard

# Step 8 — Update your .env / config to point at the new index
# instead of the small demo one, so the live Streamlit app uses
# the 2M-scale index going forward
#   FAISS_INDEX_PATH=ragshield_2m.index

# Step 9 — Document the final numbers in your paper/README:
#   - final vector count (should read ~2,600,000)
#   - nlist and nprobe values actually used
#   - measured recall vs exact search
#   - measured query latency at this scale
#   - confirm Ring 1/2/3 ASR results are consistent with the
#     smaller-scale numbers already reported
```

**Checklist — you're fully done scaling when:**

```
☐ Full 2.6M-document corpus embedded (not just a --limit slice)
☐ IndexIVFFlat built and trained on the FULL vector set (or a
  large representative sample, 100K+ vectors)
☐ Recall vs exact search measured and above ~90%
☐ Query latency confirmed under ~100ms per search
☐ Full RAG-Shield evaluation harness re-run successfully
☐ ASR numbers at scale documented and compared to small-scale
  numbers (they should be similar — Ring 1/2/3 math is unchanged,
  see Numericals Section H)
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

[🏠 Repo Home](../../README.md) &nbsp;·&nbsp; [📂 Docs Index](../README.md) &nbsp;·&nbsp; [📘 Theory](RAGSHIELD_THEORY.md#top) &nbsp;·&nbsp; [🧮 Numericals](RAGSHIELD_NUMERICALS.md#top) &nbsp;·&nbsp; [🛠️ Practice (you are here)](#top) &nbsp;·&nbsp; [🔍 FAISS Deep-Dive](RAGSHIELD_FAISS.md#top)

[⬆ Back to top](#top)
