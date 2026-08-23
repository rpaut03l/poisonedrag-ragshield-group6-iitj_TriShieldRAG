r"""
make_appendices.py -- generate the arXiv appendices from committed result
artifacts. Nothing here is written by hand; every row is read from the JSON
files under evaluation/results/, so the appendix cannot drift from the
measurements it documents.

Usage (from the repo root):
    python3 make_appendices.py > appendices.tex

Then in the paper, after \appendix:
    \input{appendices}
"""
import json, glob, statistics as st
from pathlib import Path

def esc(t):
    """LaTeX-escape a string from the corpus."""
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"),
                 ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\^{}")]:
        t = t.replace(a, b)
    return t

def load(p):
    q = Path(p)
    return json.loads(q.read_text()) if q.exists() else None

OUT = []
def w(s=""): OUT.append(s)

# ------------------------------------------------------------------
# Appendix A / B: full target-question sets with per-configuration outcome
# ------------------------------------------------------------------
def question_appendix(letter, corpus, targets_path, nonad_glob, ad_glob):
    tg = load(targets_path)
    if not tg: return
    def outcomes(pat):
        d = {}
        for f in sorted(glob.glob(pat)):
            for r in json.load(open(f))["rows"]:
                d.setdefault(r["id"], []).append(
                    (r["none_fooled"], r["paper_fooled"], r["full_fooled"]))
        return d
    na, ad = outcomes(nonad_glob), outcomes(ad_glob)
    if not na and not ad: return

    # longtable cannot break pages in twocolumn mode, and these tables are
    # wide, so they get a full single-column page.
    w(r"\onecolumn")
    w(r"\section{Target questions and per-question outcomes: %s}" % corpus)
    w(r"\label{sec:app%s}" % letter)
    w(r"""
All %d target questions, taken unmodified from the artifact released with
\cite{zou2024poisonedrag}. $t_q$ is the ground-truth answer supplied with the
artifact and $w_q$ the attacker's chosen answer.

Each outcome cell holds a triple $n/p/T$: the number of trials in which the
undefended baseline ($n$), the prior-work reproduction ($p$) and the full
three-ring pipeline ($T$) returned the attacker's answer, out of the number of
trials shown in parentheses. \textbf{NA} is the non-adaptive attacker,
\textbf{A} the adaptive one. A dash means the configuration was not run for
that corpus. Rows where $T$ exceeds $n$ under \textbf{A} are the questions on
which the defense actively harmed the answer.
""" % len(tg))
    w(r"\begin{longtable}{@{}p{6.6cm}p{2.9cm}p{2.9cm}cc@{}}")
    w(r"\toprule")
    w(r"\rowcolor{shieldblueLight}")
    w(r"\textbf{Target question} & \textbf{$t_q$} & \textbf{$w_q$} & "
      r"\textbf{NA} & \textbf{A} \\")
    w(r"\rowcolor{shieldblueLight}")
    w(r" & & & {\footnotesize $n/p/T$} & {\footnotesize $n/p/T$} \\")
    w(r"\midrule\endhead")
    for i, t in enumerate(tg):
        def triple(d):
            v = d.get(t["id"])
            if not v: return "---"
            return "/".join(str(sum(x[k] for x in v)) for k in range(3)) \
                   + r"\,\footnotesize(%d)" % len(v)
        row = [esc(t["question"])[:78], esc(t["true_answer"])[:26],
               esc(t["wrong_answer"])[:26], triple(na), triple(ad)]
        if i % 2: w(r"\rowcolor{neutralgray}")
        w(" & ".join(row) + r" \\")
    w(r"\bottomrule")
    w(r"\caption{%s target questions and per-question outcomes.}" % corpus)
    w(r"\label{tab:app%s}" % letter)
    w(r"\end{longtable}")
    w(r"\twocolumn")
    w()

question_appendix("A", "Natural Questions",
                  "evaluation/scale_target_questions_n100.json",
                  "evaluation/results/asr_3way_nonadaptive_t*.json",
                  "evaluation/results/asr_3way_adaptive_t*.json")
question_appendix("B", "HotpotQA",
                  "evaluation/hotpotqa_targets.json",
                  "evaluation/results/asr_3way_hp_nonadaptive_t*.json",
                  "evaluation/results/asr_3way_hp_adaptive_t*.json")

# ------------------------------------------------------------------
# Appendix C: complete rho sweeps, all corpora, every row
# ------------------------------------------------------------------
w(r"\FloatBarrier")
w(r"\section{Complete $\rho$-sweep tables}")
w(r"\label{sec:appC}")
w(r"""
Every row produced by \texttt{rho\_sweep.py} for each corpus, at $k=5$ and
$N=100$. $c_p$ and $c_c$ are the mean consistency scores of malicious and clean
documents; $t_p$ and $t_c$ the corresponding trust scores; \emph{inv} the
fraction of questions on which the highest-trust document in the retrieved set
is a malicious one. These are the tables from which every $\rho^{*}$ in
Table~\ref{tab:rhostar} is interpolated.
""")
for label, path in [("Natural Questions", "evaluation/results/rho_sweep_n100.json"),
                    ("HotpotQA", "evaluation/results/rho_sweep_hotpotqa.json"),
                    ("MS-MARCO", "evaluation/results/rho_sweep_msmarco.json")]:
    d = load(path)
    if not d: continue
    w(r"\begin{table}[t]")
    w(r"\caption{$\rho$ sweep, %s.}" % label)
    w(r"\centering\small\setlength{\tabcolsep}{5pt}")
    w(r"\begin{tabular}{@{}rrrrrrr@{}}")
    w(r"\toprule\rowcolor{shieldblueLight}")
    w(r"$\rho$ & $n_p$ & $c_p$ & $c_c$ & $t_p$ & $t_c$ & \emph{inv} \\")
    w(r"\midrule")
    for i, r in enumerate(d["rows"]):
        f = lambda v: "---" if v is None else f"{v:.3f}"
        if i % 2: w(r"\rowcolor{neutralgray}")
        w(f"{r['rho']:.2f} & {r['n_poison']} & {f(r['consistency_poison'])} & "
          f"{f(r['consistency_clean'])} & {f(r['trust_poison'])} & "
          f"{f(r['trust_clean'])} & {f(r.get('inversion_rate'))} \\\\")
    w(r"\bottomrule\end{tabular}\end{table}")
    w()

# ------------------------------------------------------------------
# Appendix D: per-trial results, not just aggregates
# ------------------------------------------------------------------
w(r"\FloatBarrier")
w(r"\section{Per-trial results}")
w(r"\label{sec:appD}")
w(r"""
Each end-to-end configuration was repeated. Table~\ref{tab:e2e} reports the mean
and standard deviation; this appendix gives the individual trials, so that the
spread can be inspected directly rather than taken on trust.
""")
w(r"\begin{table*}[t]\centering\small\setlength{\tabcolsep}{7pt}")
w(r"\begin{tabular}{@{}lrrrr@{}}")
w(r"\toprule\rowcolor{shieldblueLight}")
w(r"\textbf{Corpus / attacker} & \textbf{Trial} & \textbf{none} & "
  r"\textbf{prior} & \textbf{TriShield} \\")
w(r"\midrule")
GROUPS = [("NQ, non-adaptive", "evaluation/results/asr_3way_nonadaptive_t*.json"),
          ("NQ, adaptive", "evaluation/results/asr_3way_adaptive_t*.json"),
          ("HotpotQA, non-adaptive", "evaluation/results/asr_3way_hp_nonadaptive_t*.json"),
          ("HotpotQA, adaptive", "evaluation/results/asr_3way_hp_adaptive_t*.json")]
for gi, (label, pat) in enumerate(GROUPS):
    files = sorted(glob.glob(pat))
    if not files: continue
    vals = []
    for f in files:
        s_ = json.load(open(f))["summary"]
        vals.append((s_["asr_none_pct"], s_["asr_paper_defenses_pct"],
                     s_["asr_full_pipeline_pct"]))
    # multirow label spans the trial rows; no partial row shading, so no
    # coloured empty cells.
    for i, v in enumerate(vals, 1):
        lab = r"\multirow{%d}{*}{%s}" % (len(vals), label) if i == 1 else ""
        w(f"{lab} & {i} & {v[0]} & {v[1]} & {v[2]} \\\\")
    if len(vals) > 1:
        c = list(zip(*vals))
        m = [f"$\\mathbf{{{st.mean(x):.1f}\\pm{st.stdev(x):.1f}}}$" for x in c]
        w(r"\cmidrule(l){2-5}")
        w(f" & \\emph{{mean}} & {m[0]} & {m[1]} & {m[2]} \\\\")
    if gi < len(GROUPS) - 1: w(r"\midrule")
w(r"\bottomrule\end{tabular}")
w(r"\caption{Individual trial results behind Table~\ref{tab:e2e}.}")
w(r"\label{tab:apptrials}\end{table*}")
w()

# ------------------------------------------------------------------
# Appendix E: reproduction guide
# ------------------------------------------------------------------
w(r"\FloatBarrier")
w(r"""\section{Reproduction}
\label{sec:appE}

Every number in this paper is produced by one of the following commands, run
from the repository root against the environment recorded in
Table~\ref{tab:impl}. Corpus and index construction are deterministic given the
seed; the end-to-end measurements are not, since they sample a live model panel,
which is why each is repeated.

\paragraph{Corpus and index.} \texttt{build\_embeddings.py} embeds a BeIR corpus
into sharded \texttt{.npy} files and merges them; \texttt{build\_scale\_metadata.py}
writes the aligned metadata. \texttt{measure\_recall.py} computes exhaustive
ground truth on the GPU and reports recall at each $\mathrm{nprobe}$, producing
Table~\ref{tab:recall}.

\paragraph{Poison.} \texttt{load\_poisonedrag\_corpus.py} imports the artifact of
\cite{zou2024poisonedrag} and validates it, rejecting entries with missing
fields, duplicate adversarial texts, or degenerate target answers. The adaptive
variant is derived from the same file by removing the prepended question and
substituting an ordinary title.

\paragraph{Evasion certification.} \texttt{verify\_adaptive\_poison.py} scores
every candidate malicious text with Ring 1's production scorer and exits
non-zero unless all fall below $\vartheta_1$. No adaptive-attacker figure in
this paper was produced without this gate passing first.

\paragraph{Measurement.} \texttt{evaluation/run\_experiments\_3way.py} produces
Table~\ref{tab:e2e}; \texttt{rho\_sweep.py} produces Appendix~\ref{sec:appC} and
Fig.~\ref{fig:rho-inversion}; \texttt{rho\_sweep\_llm.py} produces
Table~\ref{tab:rho-asr} and Fig.~\ref{fig:asr-rho}. Figures are regenerated from
the result JSON by \texttt{make\_figures.py}, and this appendix by
\texttt{make\_appendices.py}.

\paragraph{Cost.} The deterministic sweeps require no model access and complete
in under a minute per corpus. The end-to-end measurements require API access to
the panel; the full set reported here consumed on the order of $2\times10^4$
model calls.
""")

print("\n".join(OUT))
