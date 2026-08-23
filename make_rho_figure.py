"""
make_rho_figure.py -- Figure: Ring 2 consistency inversion vs poison
fraction rho, with the measured boundary against Proposition 1's
analytically predicted rho = 0.5.

Reads the JSON written by rho_sweep.py (k=5 and k=10) and emits a
publication-quality PDF + PNG.
"""
import json, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def interp_cross(rows):
    pts = [(r["rho"], r["consistency_poison"], r["consistency_clean"])
           for r in rows
           if r["consistency_poison"] is not None
           and r["consistency_clean"] is not None]
    for (r1, p1, c1), (r2, p2, c2) in zip(pts, pts[1:]):
        g1, g2 = c1 - p1, c2 - p2
        if g1 > 0 >= g2:
            return r1 + (r2 - r1) * g1 / (g1 - g2)
    return None


def series(rows, key):
    return ([r["rho"] for r in rows if r[key] is not None],
            [r[key] for r in rows if r[key] is not None])


def main():
    k5 = json.loads(Path(sys.argv[1]).read_text())
    k10 = json.loads(Path(sys.argv[2]).read_text())
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("figures/rho_inversion")
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)

    for ax, data, label in ((axes[0], k5, "k = 5"), (axes[1], k10, "k = 10")):
        rows = data["rows"]
        xp, yp = series(rows, "consistency_poison")
        xc, yc = series(rows, "consistency_clean")
        ax.plot(xp, yp, "o-", color="#c0392b", lw=2, ms=6, label="poison")
        ax.plot(xc, yc, "s-", color="#27ae60", lw=2, ms=6, label="clean")

        rstar = interp_cross(rows)
        if rstar is not None:
            ax.axvline(rstar, color="#c0392b", ls="-", lw=1.4, alpha=0.8)
            ax.annotate(f"measured\n$\\rho^*={rstar:.2f}$",
                        xy=(rstar, 0.40), xytext=(rstar + 0.06, 0.36),
                        fontsize=9, color="#c0392b",
                        arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1))
        ax.axvline(0.5, color="#2c3e50", ls="--", lw=1.4, alpha=0.8)
        ax.annotate("Prop. 1\npredicts 0.5", xy=(0.5, 0.68), xytext=(0.52, 0.70),
                    fontsize=9, color="#2c3e50")

        ax.set_xlabel(r"poison fraction $\rho$ of retrieved top-$k$")
        ax.set_title(label, fontsize=11)
        ax.grid(alpha=0.25, ls=":")
        ax.set_xlim(-0.03, 1.03)

    axes[0].set_ylabel("Ring 2 consistency score  $c(d)$")
    axes[0].legend(loc="lower left", frameon=False, fontsize=9)
    fig.suptitle("Ring 2's consistency signal inverts at $\\rho\\approx0.27$, "
                 "not the predicted $0.5$", fontsize=12, y=1.00)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        p = out.with_suffix("." + ext)
        fig.savefig(p, dpi=200, bbox_inches="tight")
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
