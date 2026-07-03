<a id="top"></a>

[⬅ Theory](RAGSHIELD_THEORY.md#top) · [⬅ Numericals](RAGSHIELD_NUMERICALS.md#top) · [⬅ Back to Index](RAGSHIELD_INDEX.md#top)

# 🛠️ RAG-Shield PRACTICE — Run It, Break It, Fix It

> This file is for DOING, not reading. Copy-paste the commands.

---

## 📌 Quick Nav

- [A. First-Time Setup](#a-setup)
- [B. Daily Startup Commands](#b-startup)
- [C. Reading the App — Page by Page](#c-app-pages)
- [D. Troubleshooting — Common Errors](#d-troubleshooting)
- [E. Viva-Style Practice Questions](#e-viva-practice)
- [F. Cheatsheet — Commands in One Block](#f-cheatsheet)
- [G. Exam Hacks — Last-Minute Survival](#g-exam-hacks)

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

# Step 3 — copy the env template and fill in keys
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

# OR start the app (DEMO mode — instant, mock LLMs, no API keys needed)
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
  What you do: pick a question, click "Run attack (no defense)"
  What you see: 5 poison docs, the LLM's wrong answer
  What it proves: without defense, poison wins

Page 2 — Defense Demo
  What you do: pick a question, click "Run with RAG-Shield"
  What you see: Ring 1 → Ring 2 → Ring 3, live numbers, final answer
  What it proves: with defense, the correct answer survives

Page 3 — Side by Side
  What you do: click "Compare"
  What you see: no-defense (red) vs RAG-Shield (green), same screen
  What it proves: the visual "before and after"

Page 4 — Forensic Explorer
  What you do: expand any retrieved document
  What you see: the raw JSON scores from all 3 rings for that doc
  What it proves: every decision is auditable, not a black box

Page 5 — Results Dashboard
  What you do: click "Run evaluation"
  What you see: ASR % for No-Defense vs RAG-Shield across all
                10 questions, computed live
  What it proves: the headline number (91%→0-13%) is real, not
                  hardcoded
```

[⬆ Back to top](#top)

---

<a id="d-troubleshooting"></a>
## D. Troubleshooting — Common Errors

```
ERROR: "command not found: python"
FIX:   Use the full venv path: .venv/bin/python3.11 <script>.py
       Or: alias python='.venv/bin/python3.11'

ERROR: "ModuleNotFoundError: No module named 'X'"
FIX:   .venv/bin/python3.11 -m pip install X
       If pip itself is broken (resolvelib error), nuclear rebuild:
         rm -rf .venv
         python3.11 -m venv .venv
         .venv/bin/python3.11 -m pip install --upgrade pip
         .venv/bin/python3.11 -m pip install -r requirements.txt

ERROR: "[DOWN] Claude -> No module named 'typing_extensions'"
FIX:   .venv/bin/python3.11 -m pip install typing_extensions
       If still failing, do the nuclear rebuild above.

ERROR: "[DOWN] Mistral -> MISTRAL_API_KEY not set"
FIX:   Get a free key at https://console.mistral.ai/api-keys
       Add to .env: MISTRAL_API_KEY=your-key-here
       Do NOT use a GCP/Vertex key here — it must be a real
       mistral.ai key (starts differently, no "AQ." prefix)

ERROR: "Status 401 Unauthorized" (Mistral)
FIX:   Wrong key type. Re-check you copied from console.mistral.ai,
       not from Google Cloud Console.

ERROR: "ImportError: cannot import name 'Mistral' from 'mistralai'"
FIX:   Version mismatch. Pin exactly:
         .venv/bin/python3.11 -m pip install mistralai==1.3.1

ERROR: Ollama shows [DOWN]
FIX:   ollama serve &
       wait 5 seconds, then re-run backends_status.py

ERROR: Streamlit page shows stale/wrong data
FIX:   Press Cmd+R (or Ctrl+R) in the browser — clears
       @st.cache_data in 2-3 seconds

FALLBACK: everything still broken, demo is in 10 minutes
FIX:   DEMO_MODE=1 .venv/bin/python3.11 -m streamlit run frontend/app.py
       Zero API keys needed, instant startup, same defense logic
       with mock LLMs instead of real ones.
```

[⬆ Back to top](#top)

---

<a id="e-viva-practice"></a>
## E. Viva-Style Practice Questions

**Q1. What does "P = S + I" mean?**
> A: The formula PoisonedRAG uses to describe a poison document. S is
> the search-trigger (text designed to get retrieved), I is the
> injection (the actual lie). Together they form one poison document.

**Q2. Why does Ring 1 use `max()` instead of averaging the three detector scores?**
> A: `max()` means ANY single strong signal is enough to block —
> a deliberately aggressive policy. Averaging would let one weak
> detector "dilute" a strong signal from another, letting some
> poison through.

**Q3. What happens if Ring 1 blocks ALL retrieved documents?**
> A: The fallback fires — it retrieves a much wider pool (30 docs
> instead of 5), strips anything labelled POISONED, and returns
> the top-5 clean documents instead.

**Q4. Why is retrieval_score weighted LOWEST (0.20) in Ring 2's trust formula?**
> A: Because poison is specifically engineered to score HIGH on
> retrieval similarity (that's the whole point of the "S" component
> in P=S+I). Trusting that signal heavily would work in the
> attacker's favour, so we deliberately weight it least.

**Q5. Can a clean document ever be dropped by Ring 2?**
> A: Only if its consistency AND retrieval score are both extremely
> low — but since provenance alone (0.45 × 1.0 = 0.45) already
> exceeds the 0.35 drop threshold, a properly-labelled clean
> document is mathematically guaranteed to survive Ring 2.

**Q6. Why three DIFFERENT LLM companies instead of one strong model?**
> A: Different companies train differently — different data,
> different safety approaches. A poison document that fools Claude
> might not fool Mistral or LLaMA identically. Diversity of failure
> modes is the actual defense mechanism, not raw model strength.

**Q7. What is "candidate-aware matching" and why was it needed?**
> A: Instead of requiring LLM answers to match EXACTLY as strings,
> it checks whether all significant words of a candidate answer
> appear in the LLM's response. This was needed because Claude
> often gives a longer, more verbose sentence than Mistral or LLaMA
> even when they all agree on the same fact — exact string matching
> was incorrectly flagging this as "disagreement."

**Q8. What's the difference between Ring 2 dropping a document and Ring 3 disagreeing?**
> A: Ring 2 drops a document from the CONTEXT before any LLM sees
> it — based on trust score alone. Ring 3 disagreement happens
> AFTER the LLMs have already answered, when their answers don't
> match each other — it triggers a re-retrieval, not a simple drop.

**Q9. Is RAG-Shield tested against an adaptive attacker (one who knows the exact thresholds)?**
> A: Not yet — this is an honest, stated limitation. Current
> evaluation is against PoisonedRAG-style poison. Testing against
> an attacker with knowledge of our exact 0.5 / 0.35 / 0.66
> thresholds is planned future work.

**Q10. Why is RAG-Shield's approach called "black-box"?**
> A: Because it never needs access to a model's internal weights,
> attention matrices, or gradients — only the model's normal
> text-in, text-out API. This means it works identically on
> closed-source APIs (Claude, GPT-4) and open-weight local models
> (LLaMA via Ollama).

[⬆ Back to top](#top)

---

<a id="f-cheatsheet"></a>
## F. Cheatsheet — Commands in One Block

```bash
# Full daily routine, copy-paste all at once:

cd poisonedrag-ragshield-group6-iitj
ps aux | grep -i ollama
DEMO_MODE=0 .venv/bin/python3.11 backends_status.py
DEMO_MODE=0 bash run_live.sh &
bash tail_logs.sh

# If anything breaks, fallback to demo mode instantly:
DEMO_MODE=1 .venv/bin/python3.11 -m streamlit run frontend/app.py
```

[⬆ Back to top](#top)

---

<a id="g-exam-hacks"></a>
## G. Last Min  Hacks — Last-Minute Survival

```
If asked to derive a Ring 1/2/3 score by hand:
  → go to NUMERICALS.md Section D/E/F, copy the exact formula,
    plug in the numbers they give you, show every step

If asked "why not just use one bigger/smarter LLM instead of 3?":
  → "Defense-in-depth. A single point of failure, no matter how
     strong, is still ONE point an attacker only needs to beat once."

If asked to compare with a specific competitor paper:
  → go to THEORY.md Section H, find the text diagram for that
    exact paper vs RAG-Shield

If the demo genuinely crashes mid-presentation:
  → DEMO_MODE=1 fallback (see Section D above) — same story,
    same numbers, zero API dependency, restarts in seconds

If asked about scale/limitations:
  → be honest: "5K documents / 10 questions currently — we're
    actively scaling to the full 2.6M-passage NQ corpus as part
    of the production expansion plan"
```

[⬆ Back to top](#top)

---

[⬅ Theory](RAGSHIELD_THEORY.md#top) · [⬅ Numericals](RAGSHIELD_NUMERICALS.md#top) · [⬅ Back to Index](RAGSHIELD_INDEX.md#top)
