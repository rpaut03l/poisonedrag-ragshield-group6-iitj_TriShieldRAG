<a id="top"></a>

# 🔍 RAGSHIELD_FAISS.md — FAISS & IndexFlatIP Explained
### How fast document search actually works — in RAG generally, and in RAG-Shield specifically

---

## 🔝 TOP NAVIGATION — Jump to any file

**Related:** [RAGSHIELD_THEORY.md](RAGSHIELD_THEORY.md#top) (the story) → [RAGSHIELD_NUMERICALS.md](RAGSHIELD_NUMERICALS.md#top) (the math) → [RAGSHIELD_PRACTICE.md](RAGSHIELD_PRACTICE.md#top) (running it) → **This file:** RAGSHIELD_FAISS.md (the search engine)

[🏠 Repo Home](../../README.md) &nbsp;·&nbsp; [📂 Docs Index](../README.md) &nbsp;·&nbsp; [📘 Theory](RAGSHIELD_THEORY.md#top) &nbsp;·&nbsp; [🧮 Numericals](RAGSHIELD_NUMERICALS.md#top) &nbsp;·&nbsp; [🛠️ Practice](RAGSHIELD_PRACTICE.md#top) &nbsp;·&nbsp; [🔍 FAISS (you are here)](#top)

---

## 📌 TABLE OF CONTENTS

```
┌─────────────────────────────────────────────────────────────┐
│  This file stands ALONGSIDE Theory/Numericals/Practice —    │
│  it zooms into ONE specific tool (FAISS) used inside the    │
│  RETRIEVAL step, before Ring 1/2/3 ever run.                │
└─────────────────────────────────────────────────────────────┘
```

- [A. The Simple Story — Why Do We Need FAISS At All?](#a-simple-story)
- [B. What "IndexFlatIP" Actually Means, Word by Word](#b-word-by-word)
- [C. Notation and Vocabulary](#c-notation)
- [D. The Math — Inner Product, Step by Step](#d-math)
- [E. Step-by-Step — Building and Searching an Index](#e-step-by-step)
- [F. How RAG (in General) Uses FAISS](#f-rag-general)
- [G. How RAG-Shield Specifically Uses FAISS](#g-ragshield-specific)
- [H. IndexFlatIP vs IndexIVFFlat — Side by Side](#h-flat-vs-ivf)
- [I. Full Code Walkthrough From Our Repo](#i-code-walkthrough)
- [J. Mnemonics](#j-mnemonics)
- [K. Cheatsheet](#k-cheatsheet)
- [L. Exam Hacks](#l-exam-hacks)

---

<a id="a-simple-story"></a>
## A. The Simple Story — Why Do We Need FAISS At All?

Imagine a **giant toy box** with a million toys inside. You're
holding a red rubber ball and want to find the 5 toys in the box
that are MOST SIMILAR to your ball.

```
   YOUR BALL              THE GIANT TOY BOX (1,000,000 toys)
   (red, round,           [toy1] [toy2] [toy3] ... [toy999999] [toy1000000]
    rubber)

   You want: the 5 MOST SIMILAR toys, out of a million, FAST.
```

If you checked every single toy one by one, comparing it to your
ball, that would take forever with a million toys. **FAISS is a
tool built by Meta (Facebook) that does this comparison job
extremely fast**, even with millions or billions of "toys" — in
our case, documents that have been turned into lists of numbers.

**FAISS = Facebook AI Similarity Search.** That's literally what
the name means — a search tool for finding similar things.

**Important: FAISS does NOT understand meaning.** It's not an AI
model. It's a super-fast calculator for comparing lists of numbers.
A separate tool (`all-mpnet-base-v2`, a sentence-embedding model)
does the job of turning text into meaningful numbers FIRST — FAISS
only compares those numbers afterward.

[⬆ Back to top](#top)

---

<a id="b-word-by-word"></a>
## B. What "IndexFlatIP" Actually Means, Word by Word

```
"Index"  = FAISS's organised storage container for all your
           vectors — think of it as a specially-designed filing
           cabinet built for fast similarity lookups

"Flat"   = NO shortcuts. Every single vector gets checked, one by
           one, every single search. Nothing is skipped, nothing
           is pre-sorted into groups.

"IP"     = Inner Product — the specific MATH RULE used to measure
           how similar two vectors are (explained fully in
           Section D below)
```

**Put together:** `IndexFlatIP` = "a storage container that checks
EVERY vector exhaustively, using the inner-product math rule to
measure similarity." It is the SIMPLEST, most STRAIGHTFORWARD, and
most EXACT search method FAISS offers — nothing clever, nothing
approximate, just a thorough, honest, one-by-one comparison.

[⬆ Back to top](#top)

---

<a id="c-notation"></a>
## C. Notation and Vocabulary

```
vector             = a list of numbers describing a "location"
                     in meaning-space (e.g. 768 numbers per
                     document — see RAGSHIELD_NUMERICALS.md)

dimension (d)      = how many numbers are in each vector
                     (d = 768 throughout this project)

index              = FAISS's internal, organised storage of
                     vectors, built so searching is fast

query vector        = the ONE vector you are searching FOR right
                     now (the user's question, turned into numbers)

top-K              = "give me the K closest/most-similar matches"
                     (K = 5 throughout this project)

inner product (IP) = the specific calculation: multiply matching
                     numbers together, then add up all the results
                     (full worked example in Section D)

similarity score    = the NUMBER that comes out of the inner-product
                     calculation — higher means more similar

exhaustive search    = checking EVERY single stored vector, with no
                     shortcuts — this is what "Flat" means

approximate search   = checking only a SUBSET of stored vectors,
                     using pre-sorted groups, to trade a little
                     accuracy for a lot of speed (this is what
                     IndexIVFFlat does instead — see Section H)
```

[⬆ Back to top](#top)

---

<a id="d-math"></a>
## D. The Math — Inner Product, Step by Step

### D.1 — What "Inner Product" Actually Computes

```
Given two vectors:
    query  = [q1, q2, q3, ..., q768]
    doc    = [d1, d2, d3, ..., d768]

Inner product formula:
    IP(query, doc) = (q1×d1) + (q2×d2) + (q3×d3) + ... + (q768×d768)

In plain words: multiply each MATCHING pair of numbers together,
then add up ALL of those products into one single final number.
```

### D.2 — A Tiny Worked Example (3 numbers instead of 768)

```
query = [1, 2, 3]
doc   = [4, 5, 6]

Step 1 — multiply matching positions:
    1×4 = 4
    2×5 = 10
    3×6 = 18

Step 2 — add them all up:
    4 + 10 + 18 = 32

IP(query, doc) = 32
```

### D.3 — Why a BIGGER Inner Product Means MORE Similar

```
If two vectors point in a SIMILAR direction (similar meaning),
their matching numbers tend to have the SAME SIGN (both positive
or both negative) and similar SIZE — so each multiplication
produces a bigger positive number, and the total sum is large.

If two vectors point in DIFFERENT directions (different meaning),
their matching numbers often have OPPOSITE signs or very different
sizes — multiplications partly cancel out, and the total sum is
smaller (or even negative).

RULE: Bigger inner product = more similar. Smaller (or negative)
      inner product = less similar.
```

### D.4 — The Crucial Detail: Normalisation

```
Inner product ALONE is influenced by both DIRECTION and LENGTH of
the vectors. A very long vector pointing in a so-so direction could
score higher than a short vector pointing in a PERFECT direction —
which would be misleading.

FIX: before comparing, shrink EVERY vector to length exactly 1
(this is called "normalising"). Once every vector has the SAME
length, the inner product ONLY reflects direction (meaning) — and
at that point, inner product of two length-1 vectors becomes
mathematically IDENTICAL to cosine similarity
(see RAGSHIELD_NUMERICALS.md, Section D.3, for the cosine
similarity explanation used inside Ring 1's OutlierDetector).

This is why our code always sets normalize_embeddings=True when
creating vectors — see Section I below.
```

[⬆ Back to top](#top)

---

<a id="e-step-by-step"></a>
## E. Step-by-Step — Building and Searching an Index

```
STEP 1 — Build time (happens ONCE, when the knowledge base is made)
    Every document is turned into a 768-number vector
    All these vectors get loaded into a FAISS index:
        index.add(all_document_vectors)

STEP 2 — Query time (happens EVERY time a user asks a question)
    The user's question ALSO gets turned into a 768-number vector,
    using the SAME embedding model (so they're comparable — like
    using the same ruler to measure two different things)

STEP 3 — FAISS searches
    scores, doc_ids = index.search(query_vector, k=5)
    "search" computes the inner product between the query and
    EVERY stored vector (for IndexFlatIP specifically — no
    shortcuts), then returns the 5 best matches

STEP 4 — Ranking
    FAISS returns doc_ids sorted from MOST similar to LEAST
    similar, along with their similarity scores

STEP 5 — Hand off to Ring 1
    RAG-Shield takes these 5 documents and passes them to
    Ring 1 (Ingest Guard) for screening — see
    RAGSHIELD_THEORY.md, Section D
```

[⬆ Back to top](#top)

---

<a id="f-rag-general"></a>
## F. How RAG (in General) Uses FAISS

This section explains the ROLE FAISS plays in ANY RAG system, not
just this project — so you understand the general pattern before
seeing our specific implementation.

```
                     GENERIC RAG PIPELINE
                     =====================

  Knowledge Base           User Question          Answer
  (millions of docs)            │                    ▲
       │                        │                    │
       ▼                        ▼                    │
  ┌───────────┐          ┌─────────────┐       ┌─────────────┐
  │  Embed    │          │   Embed     │       │     LLM     │
  │  ALL docs │          │  the query  │       │  generates  │
  │  (once)   │          │  (each time)│       │  the answer │
  └───────────┘          └─────────────┘       └─────────────┘
       │                        │                    ▲
       ▼                        ▼                    │
  ┌─────────────────────────────────────┐            │
  │            FAISS INDEX              │            │
  │  Stores all doc vectors, finds the  │────────────┘
  │  TOP-K most similar to the query    │
  └─────────────────────────────────────┘
```

**Why FAISS specifically, and not just a simple loop comparing
every document one by one in plain Python?**

```
A simple Python loop over 1 million documents, computing inner
product by hand for each one, would be SLOW — Python itself has
overhead for every single operation.

FAISS is written in C++ (a much faster, lower-level programming
language) and is specifically OPTIMISED for exactly this kind of
massive, repetitive numerical comparison. It can also use special
CPU/GPU instructions that do many calculations simultaneously
instead of one at a time.

Result: FAISS can search millions of vectors in milliseconds,
where a naive Python loop might take many seconds or even minutes
for the same task.
```

[⬆ Back to top](#top)

---

<a id="g-ragshield-specific"></a>
## G. How RAG-Shield Specifically Uses FAISS

```
┌────────────────────────────────────────────────────────────┐
│  WHERE FAISS SITS IN THE RAG-SHIELD PIPELINE               │
├────────────────────────────────────────────────────────────┤
│                                                            │
│   Documents added to KB                                    │
│         │                                                  │
│         ▼                                                  │
│   sentence-transformers embeds them (768-dim vectors)      │
│         │                                                  │
│         ▼                                                  │
│   ★ FAISS (IndexFlatIP) stores + indexes them ★            │
│         │                                                  │
│         ▼                                                  │
│   User asks a question                                     │
│         │                                                  │
│         ▼                                                  │
│   sentence-transformers embeds the QUESTION                │
│         │                                                  │
│         ▼                                                  │
│   ★ FAISS.search() finds top-5 most similar docs ★         │
│         │                                                  │
│         ▼                                                  │
│   RING 1 — Ingest Guard screens those 5 docs               │
│         │                                                  │
│         ▼                                                  │
│   RING 2 — Retrieval Scorer re-ranks by trust              │
│         │                                                  │
│         ▼                                                  │
│   RING 3 — Cross-LLM Consensus generates final answer      │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Critical fact tying this back to Numericals/Theory:** FAISS's
similarity score becomes `ret_score` inside Ring 2's trust formula
(see [RAGSHIELD_NUMERICALS.md, Section E.3](RAGSHIELD_NUMERICALS.md#e-ring2-math)):

```
trust = 0.45×prov + 0.35×cons + 0.20×ret_score
                                      ^^^^^^^^^
                                      this number
                                      comes directly
                                      from FAISS's
                                      inner-product
                                      search
```

**Why `ret_score` is weighted LOWEST (0.20) in that formula:**
because poison documents are SPECIFICALLY crafted to score high on
FAISS similarity (the "S" component of P=S+I — see
[RAGSHIELD_THEORY.md, Section B](RAGSHIELD_THEORY.md#b-attack)).
Trusting FAISS's number heavily would hand the attacker exactly
what they optimised for, so Ring 2 deliberately discounts it.

[⬆ Back to top](#top)

---

<a id="h-flat-vs-ivf"></a>
## H. IndexFlatIP vs IndexIVFFlat — Side by Side

```
┌───────────────────┬───────────────────────┬───────────────────────┐
│                   │ IndexFlatIP           │ IndexIVFFlat          │
│                   │ (current, small scale)│ (planned, 2M+ scale)  │
├───────────────────┼───────────────────────┼───────────────────────┤
│ Search style      │ Exact — checks EVERY  │ Approximate — checks  │
│                   │ vector, no shortcuts  │ only nearby "bins"    │
├───────────────────┼───────────────────────┼───────────────────────┤
│ Setup complexity  │ Trivial — just add()  │ Needs a "training"    │
│                   │ vectors and search    │ step first (see       │
│                   │                       │RAGSHIELD_NUMERICALS   │
│                   │                       │.md Section H)         │
├───────────────────┼───────────────────────┼───────────────────────┤
│ Search speed at   │ Instant               │ Instant               │
│ 5,000 docs        │                       │                       │
├───────────────────┼───────────────────────┼───────────────────────┤
│ Search speed at   │ Noticeably slower —   │ Still fast, if nlist/ │
│ 2.6 million docs  │ 2.6M comparisons per  │ nprobe are tuned wel  │
│                   │ query                 │                       │
├───────────────────┼───────────────────────┼───────────────────────┤
│ Memory at 2.6M    │ ~8GB just for vectors │ Similar memory, plus  │
│ docs              │                       │ small overhead for    │
│                   │                       │ bin structure         │
├───────────────────┼───────────────────────┼───────────────────────┤
│ Accuracy          │ 100% exact — always   │Slightly approximate—  │
│                   │ finds the TRUE top-K  │ tiny chance of missing│
│                   │                       │ a true top-K match    │
│                   │                       │ (tunable via nprobe)  │
└───────────────────┴───────────────────────┴───────────────────────┘
```

**The simplest possible summary:** IndexFlatIP is honest and exact
but doesn't scale forever. IndexIVFFlat sorts things into labelled
bins first so it only has to check a handful of bins instead of
every single vector — trading a tiny, controllable bit of accuracy
for a massive speed gain at large scale. Full detail on the
IndexIVFFlat side is in
[RAGSHIELD_NUMERICALS.md, Section H](RAGSHIELD_NUMERICALS.md#h-scaling-math)
and [RAGSHIELD_PRACTICE.md, Section E](RAGSHIELD_PRACTICE.md#e-scaling-steps).

[⬆ Back to top](#top)

---

<a id="i-code-walkthrough"></a>
## I. Full Code Walkthrough From Our Repo

**File:** `ragshield_core/retriever.py`

```python
# ── BUILDING the index (happens once, when the KB is created) ──

self._faiss = faiss.IndexFlatIP(emb.shape[1])
```
> Creates a new, empty IndexFlatIP. `emb.shape[1]` grabs the SECOND
> number from the embeddings' shape (recall `.shape` gives you
> `(number_of_docs, dimension)` — so `[1]` picks out just the
> dimension, which is 768). This tells FAISS "expect vectors with
> exactly 768 numbers each."

```python
self._faiss.add(emb.astype(np.float32))
```
> `emb.astype(np.float32)` converts all the numbers into a specific
> storage format (32-bit floating point) that FAISS is built to
> work with efficiently — similar to making sure everyone uses the
> same units (metres, not a mix of metres and feet) before
> comparing measurements. `.add(...)` then actually stores all
> these vectors inside the index.

```python
# ── SEARCHING the index (happens every time a query comes in) ──

scores, idx = self._faiss.search(qv, k)
```
> `qv` is the query vector (the user's question, already turned
> into 768 numbers by the same embedding model). `k` is how many
> results you want back (5, in our project). `.search(...)` runs
> the inner-product comparison against every stored vector (because
> this is IndexFlatIP — exhaustive, no shortcuts) and returns TWO
> things at once:
> - `scores` — the similarity numbers for the best matches
> - `idx` — WHICH documents those scores belong to (their index
>   positions, so you can look up the actual text)

**Where `normalize_embeddings=True` comes in (from
`ragshield_core/retriever.py`, using `sentence-transformers`):**

```python
doc_embeddings = model.encode(
    all_document_texts,
    normalize_embeddings=True,   # <- shrinks every vector to length 1
    batch_size=32,
)
```
> This is the step that makes IndexFlatIP's inner product
> mathematically EQUIVALENT to cosine similarity (see Section D.4
> above). Without this, longer documents might unfairly score
> higher purely because their vector happens to be longer, not
> because their MEANING is more similar.

[⬆ Back to top](#top)

---

<a id="j-mnemonics"></a>
## J. Mnemonics

```
FAISS = "Facebook AI Similarity Search" — fast calculator for
        comparing lists of numbers, NOT an AI model itself

FLAT  = "no shortcuts, check everything" (exact search)
IP    = "Inner Product" — multiply matching numbers, add them up

BIGGER IP = MORE SIMILAR (once vectors are normalised to length 1)

NORMALISE FIRST = "make every vector length 1 before comparing,
                   so only DIRECTION (meaning) matters, not length"

ret_score IS WEIGHTED LOWEST in Ring 2's trust formula because
poison is DESIGNED to maximise exactly this number
```

[⬆ Back to top](#top)

---

<a id="k-cheatsheet"></a>
## K. Cheatsheet

```
┌────────────────────────────────────────────────────────────────────┐
│ TERM                │ MEANING                                      │
├────────────────────────────────────────────────────────────────────┤
│ FAISS               │ Meta's fast vector-comparison library        │
│ Index               │ FAISS's organised storage of vector          │
│ IndexFlatIP         │ Exact search using inner product             │
│ Inner product (IP)  │ multiply matching numbers, then add them up  │
│ normalize_embeddings│ shrink vectors to length 1 before comparing  │
│ top-K               │ how many best matches to return (K=5 here)   │
│ ret_score           │ the similarity number FAISS returns, later   │
│                     │ used inside Ring 2's trust formula           │
│ IndexIVFFlat        │ approximate version, used for scaling to     │
│                     │ millions of documents (see Numericals/       │
│                     │ Practice for full detail)                    │
└────────────────────────────────────────────────────────────────────┘
```

[⬆ Back to top](#top)

---

<a id="l-exam-hacks"></a>
## L. Exam Hacks

```
TRAP: "Does FAISS understand what documents MEAN?"
SAFE: "No — FAISS only compares numbers. A separate model
       (sentence-transformers / all-mpnet-base-v2) turns text into
       meaningful numbers FIRST. FAISS's only job is fast, exact
       comparison of those numbers using inner product."

TRAP: "Why do we normalise embeddings before using FAISS?"
SAFE: "So that inner product only reflects DIRECTION (meaning)
       and not vector LENGTH. Once every vector has length 1,
       inner product becomes mathematically identical to cosine
       similarity."

TRAP: "Isn't a bigger inner product always better regardless of
       normalisation?"
SAFE: "Only if vectors are already normalised to the same length.
       Without normalisation, a longer vector could win purely by
       being longer, not by being more semantically similar —
       which is why normalize_embeddings=True matters."

TRAP: "Why does Ring 2 trust FAISS's score the LEAST of its three
       inputs?"
SAFE: "Because poison documents are specifically engineered to
       maximise FAISS similarity — that's the 'S' (search-trigger)
       component of P=S+I. Weighting it lowest (0.20) prevents the
       attacker's own optimisation target from being the strongest
       signal in our defense."
```

[⬆ Back to top](#top)

---

## 🔚 BOTTOM NAVIGATION — Jump to any file

**Related:** [RAGSHIELD_THEORY.md](RAGSHIELD_THEORY.md#top) (the story) → [RAGSHIELD_NUMERICALS.md](RAGSHIELD_NUMERICALS.md#top) (the math) → [RAGSHIELD_PRACTICE.md](RAGSHIELD_PRACTICE.md#top) (running it) → **This file:** RAGSHIELD_FAISS.md (the search engine)

[🏠 Repo Home](../../README.md) &nbsp;·&nbsp; [📂 Docs Index](../README.md) &nbsp;·&nbsp; [📘 Theory](RAGSHIELD_THEORY.md#top) &nbsp;·&nbsp; [🧮 Numericals](RAGSHIELD_NUMERICALS.md#top) &nbsp;·&nbsp; [🛠️ Practice](RAGSHIELD_PRACTICE.md#top) &nbsp;·&nbsp; [🔍 FAISS (you are here)](#top)

[⬆ Back to top](#top)
