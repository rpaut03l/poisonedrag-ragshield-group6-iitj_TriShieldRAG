"""
make_asr_figure.py -- Figure 2: end-to-end ASR as a function of the
poison fraction rho, for the adaptive and non-adaptive attackers, with
the Phase-1 consistency-inversion boundary rho* overlaid.

The point of the figure is that the MECHANISM measured in Figure 1
(Ring 2's consistency signal inverting at rho* ~= 0.27) PREDICTS the
OUTCOME: ASR is zero below rho* and rises monotonically above it.

Second panel plots Ring 3's mean weighted agreement against rho.
Agreement falls as poison accumulates and then returns to ~1.0 at
rho=1.0, where ASR is also 100% -- i.e. the panel is most confident
exactly when the context is uniformly poisoned. Agreement measures
uniformity of context, not correctness, which is the premise the
theta_3 = 0.66 acceptance threshold relies on.

Reads evaluation/results/rho_sweep_llm.json.
"""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RHO_STAR = 0.27          # measured in Phase 1 (k=5: 0.299, k=10: 0.241)
THETA_3 = 0.66           # Ring 3 acceptance threshold from the paper


def xy(rows, key):
    return ([r["rho"] for r in rows if r.get(key) is not None],
            [r[key] for r in rows if r.get(key) is not None])


def main():
    data = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("figures/asr_vs_rho")
    out.parent.mkdir(parents=True, exist_ok=True)

    ad = data.get("adaptive", [])
    na = data.get("non_adaptive_control", [])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4))

    # ---- panel A: ASR -------------------------------------------------
    x, y = xy(ad, "asr_pct")
    ax1.plot(x, y, "o-", color="#c0392b", lw=2.2, ms=7,
             label="adaptive (Ring 1 evaded)")
    if na:
        x2, y2 = xy(na, "asr_pct")
        ax1.plot(x2, y2, "s--", color="#e67e22", lw=1.8, ms=6, alpha=0.85,
                 label="non-adaptive")

    ax1.axvspan(-0.03, RHO_STAR, color="#27ae60", alpha=0.10)
    ax1.axvline(RHO_STAR, color="#27ae60", lw=1.6)
    ax1.annotate(f"$\\rho^*={RHO_STAR}$\n(Fig. 1)", xy=(RHO_STAR, 88),
                 xytext=(RHO_STAR + 0.05, 84), fontsize=9, color="#1e8449",
                 arrowprops=dict(arrowstyle="->", color="#27ae60", lw=1))
    ax1.axvline(0.5, color="#2c3e50", ls="--", lw=1.3, alpha=0.7)
    ax1.annotate("Prop. 1\npredicts 0.5", xy=(0.5, 12), xytext=(0.52, 8),
                 fontsize=9, color="#2c3e50")

    ax1.set_xlabel(r"poison fraction $\rho$ of retrieved top-$k$")
    ax1.set_ylabel("attack success rate (%)")
    ax1.set_title("A. ASR tracks the measured inversion boundary", fontsize=11)
    ax1.set_ylim(-4, 104); ax1.set_xlim(-0.03, 1.03)
    ax1.grid(alpha=0.25, ls=":")
    ax1.legend(loc="upper left", frameon=False, fontsize=9)

    # ---- panel B: agreement vs correctness ----------------------------
    xa, ya = xy(ad, "mean_agreement")
    ax2.plot(xa, ya, "o-", color="#8e44ad", lw=2.2, ms=7,
             label="Ring 3 mean agreement")
    xs, ys = xy(ad, "asr_pct")
    ax2.plot(xs, [v / 100 for v in ys], "^:", color="#c0392b", lw=1.6, ms=6,
             alpha=0.75, label="ASR (scaled to 0-1)")
    ax2.axhline(THETA_3, color="#2c3e50", ls="--", lw=1.3, alpha=0.8)
    ax2.annotate(r"$\vartheta_3=0.66$ accept", xy=(0.02, THETA_3 + 0.02),
                 fontsize=9, color="#2c3e50")
    if xa:
        ax2.annotate("unanimous\nand wrong", xy=(1.0, 1.0), xytext=(0.62, 0.90),
                     fontsize=9, color="#8e44ad",
                     arrowprops=dict(arrowstyle="->", color="#8e44ad", lw=1))

    ax2.set_xlabel(r"poison fraction $\rho$ of retrieved top-$k$")
    ax2.set_ylabel("agreement / scaled ASR")
    ax2.set_title("B. Agreement is not evidence of correctness", fontsize=11)
    ax2.set_ylim(-0.04, 1.10); ax2.set_xlim(-0.03, 1.03)
    ax2.grid(alpha=0.25, ls=":")
    ax2.legend(loc="lower left", frameon=False, fontsize=9)

    fig.tight_layout()
    for ext in ("pdf", "png"):
        p = out.with_suffix("." + ext)
        fig.savefig(p, dpi=200, bbox_inches="tight")
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
