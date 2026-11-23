#!/usr/bin/env python3
"""Fig. 8: how much of the difference between ns-3 and the paper is explained
by the backoff countdown rule.

  paper     Mangold et al., Fig. 8 (digitised)
  standard  stock ns-3.48 (IEEE 802.11-2020 EDCA countdown), the A4 baseline
  legacy    ns-3.48 with patches/legacy-countdown.patch (DCF like countdown)

The shaded band between the two ns-3 curves is the part of the difference
that the countdown rule explains. The gap between the legacy curve and the
paper is the part that stays unexplained.

Explained share per point = (standard - legacy) / (standard - paper), only
reported where |standard - paper| is clearly larger than the digitisation
accuracy (0.3 Mb/s), otherwise the ratio is meaningless.

Usage:
    python plot_explained.py [--standard ../results/fig8] [--legacy ../results-legacy/fig8]
                             [--reference ../reference/mangold_fig8.csv]

Inputs: summary.csv of both sweeps (plot_fig8.py).
Outputs (in <legacy>): fig8_explained.png, explained.md
"""
import argparse
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from a4lib import ACS, COLOR, INK, MARKER, MUTED, interp, read_reference, style_axes
from compare_rules import read_summary

LABEL = {"AC_VO": "AC_VO (voice)", "AC_VI": "AC_VI (video)",
         "AC_BE": "AC_BE (best effort)", "AC_BK": "AC_BK (background)"}
MIN_GAP_MBPS = 0.3  # smaller differences are inside the digitisation accuracy


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--standard", default=os.path.join(here, "..", "results", "fig8"))
    ap.add_argument("--legacy", default=os.path.join(here, "..", "results-legacy", "fig8"))
    ap.add_argument("--reference", default=os.path.join(here, "..", "reference", "mangold_fig8.csv"))
    args = ap.parse_args()

    std, leg = read_summary(args.standard), read_summary(args.legacy)
    ref = read_reference(args.reference)
    loads = sorted({k[0] for k in std})
    assert loads == sorted({k[0] for k in leg}), "both sweeps need the same load points"
    s30, l30 = std[(30.0, "AC_VO")], leg[(30.0, "AC_VO")]
    assert abs(s30[0] - l30[0]) > 5 * (s30[1] + l30[1]), (
        "standard and legacy sweep are identical: was the patch active during the legacy sweep?")

    # ---------------------------------------------------------------- figure
    fig, ax = plt.subplots(figsize=(8, 5.6), dpi=900)
    for ac in ACS:
        x = [0.0] + loads
        ys = [0.0] + [std[(l, ac)][0] for l in loads]
        yl = [0.0] + [leg[(l, ac)][0] for l in loads]
        el = [0.0] + [leg[(l, ac)][1] for l in loads]
        ax.fill_between(x, ys, yl, color=COLOR[ac], alpha=0.22, lw=0, zorder=1)
        ax.plot(*zip(*ref[ac]), color=COLOR[ac], lw=1.2, ls=(0, (4, 3)), alpha=0.75,
                marker=MARKER[ac], ms=6, mfc="none", mew=1.2, zorder=2)
        ax.plot(x, ys, color=COLOR[ac], lw=1.0, alpha=0.6, zorder=2)
        ax.errorbar(x, yl, yerr=el, color=COLOR[ac], lw=2, marker=MARKER[ac], ms=7,
                    mfc="white", mew=1.6, capsize=3, elinewidth=1.2, zorder=3)

    n_std = "/".join(map(str, sorted({v[2] for v in std.values()})))
    n_leg = "/".join(map(str, sorted({v[2] for v in leg.values()})))
    handles = [Line2D([], [], color=COLOR[a], marker=MARKER[a], mfc="white", mew=1.6, lw=2,
                      label=LABEL[a]) for a in ACS]
    handles += [Line2D([], [], color=INK, lw=2, label="ns-3, legacy countdown (mean, 95 % CI)"),
                Line2D([], [], color=INK, lw=1.0, alpha=0.6, label="ns-3, standard countdown"),
                Patch(color=MUTED, alpha=0.35, lw=0, label="Explained by the countdown rule"),
                Line2D([], [], color=INK, lw=1.2, ls=(0, (4, 3)), alpha=0.75,
                       label="Mangold et al., Fig. 8 (digitised)")]
    ax.legend(handles=handles, loc="center right", frameon=False, fontsize=11, labelcolor=INK)

    ax.set_title("How much of the difference does the countdown rule explain?\n"
                 f"ns-3 standard and legacy countdown against Fig. 8",
                 loc="center", fontsize=15, color=INK, weight="bold")
    ax.set_xlabel("Offered traffic per AC (3 streams each) [Mb/s]", color=INK, fontsize=13)
    ax.set_ylabel("Throughput per AC (3 streams each) [Mb/s]", color=INK, fontsize=13)
    ax.set_xlim(-0.5, 31)
    ax.set_ylim(-0.3, 14)
    ax.set_xticks([0, 3, 6, 9, 12, 15, 18, 30])
    ax.set_yticks(range(0, 15, 2))
    ax.tick_params(axis="both", which="major", labelsize=11)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(args.legacy, "fig8_explained.png"))

    # ---------------------------------------------------------------- table
    lines = [f"Throughput per AC [Mb/s]. Standard rule: {n_std} runs, legacy rule: {n_leg} runs, "
             "mean ± 95 % CI half width. Paper: digitised Fig. 8, interpolated. Explained share = "
             "(standard - legacy) / (standard - paper), only where |standard - paper| > "
             f"{MIN_GAP_MBPS} Mb/s.", "",
             "| Load | AC | Paper | Standard | Legacy | Standard minus paper | "
             "Legacy minus paper | Explained share |",
             "| ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for load in loads:
        for ac in ACS:
            p = abs(interp(ref[ac], load))
            s, l = std[(load, ac)], leg[(load, ac)]
            gap = s[0] - p
            share = f"{100 * (s[0] - l[0]) / gap:.0f} %" if abs(gap) > MIN_GAP_MBPS else ""
            lines.append(f"| {load:g} | {ac} | {p:.2f} | {s[0]:.2f} ± {s[1]:.2f} | "
                         f"{l[0]:.2f} ± {l[1]:.2f} | {gap:+.2f} | {l[0] - p:+.2f} | {share} |")
    text = "\n".join(lines) + "\n"
    with open(os.path.join(args.legacy, "explained.md"), "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
