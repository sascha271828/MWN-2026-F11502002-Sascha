#!/usr/bin/env python3
"""Figures for the A4 slides, drawn from the same result files as the study
note (no new simulations).

  bk_zoom.png    AC_BK throughput 0 to 9 Mb/s: paper (digitised markers),
                 ns-3 standard and legacy countdown rule
  pilot_vi.png   CCDF of the AC_VI packet delay at 2.95 and 5.90 Mb/s per AC
                 for the three arrival processes of the pilot
  traffic_ccdf.png  gaps between packets of all Poisson streams (run.sh traffic),
                 divided by the model mean, against the exponential law e^-x.
                 Needs the arrival logs results/traffic/raw/*.arrivals.

Usage:
    python plot_slides.py [--out ../results/slides]
"""
import argparse
import os

import glob

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from a4lib import COLOR, INK, MARKER, MUTED, read_reference, style_axes
from analyse_pilot import MODEL_COLOR, MODEL_LABEL, MODEL_LS, MODELS, ccdf, read_delay
from compare_rules import read_summary
from verify_traffic import BURST_AC, read_arrivals, summary_row

STREAMS_PER_AC = 3

FONT = 13


def bk_zoom(here, out):
    std = read_summary(os.path.join(here, "..", "results", "fig8"))
    leg = read_summary(os.path.join(here, "..", "results-legacy", "fig8"))
    ref = read_reference(os.path.join(here, "..", "reference", "mangold_fig8.csv"))
    ac = "AC_BK"
    loads = [l for l in sorted({k[0] for k in std}) if l <= 9]

    fig, ax = plt.subplots(figsize=(6.4, 4.3), dpi=300)
    px, py = zip(*[(x, abs(y)) for x, y in ref[ac] if x <= 9.5])
    ax.plot(px, py, color=COLOR[ac], lw=1.4, ls=(0, (4, 3)), marker=MARKER[ac], ms=7, mfc="none",
            mew=1.4, label="Mangold et al., Fig. 8")
    for data, lw, alpha, label in ((std, 2.2, 1.0, "ns-3, standard rule"),
                                   (leg, 1.2, 0.6, "ns-3, legacy rule")):
        ax.errorbar([0.0] + loads, [0.0] + [data[(l, ac)][0] for l in loads],
                    yerr=[0.0] + [data[(l, ac)][1] for l in loads], color=COLOR[ac], lw=lw,
                    alpha=alpha, marker=MARKER[ac], ms=6, mfc=COLOR[ac], capsize=3, label=label)
    ax.annotate("0.30 at 6.1 Mb/s", xy=(6.06, 0.30), xytext=(6.7, 1.3), fontsize=FONT - 1,
                color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_xlabel("Offered traffic per AC [Mb/s]", fontsize=FONT, color=INK)
    ax.set_ylabel("AC_BK throughput [Mb/s]", fontsize=FONT, color=INK)
    ax.set_xlim(-0.2, 9.4)
    ax.set_ylim(-0.1, 3.4)
    ax.set_xticks([0, 1.5, 3, 3.6, 4.5, 6, 7.5, 9])
    ax.set_xticklabels(["0", "1.5", "3", "3.6", "4.5", "6", "7.5", "9"])
    ax.tick_params(labelsize=FONT - 2)
    style_axes(ax)
    ax.legend(frameon=False, fontsize=FONT - 1, labelcolor=INK, loc="upper right")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "bk_zoom.png"), transparent=True)


def pilot_vi(here, out):
    hist = read_delay(os.path.join(here, "..", "results", "pilot"))
    loads = sorted({k[0] for k in hist})[:2]  # 2.95 and 5.90 Mb/s per AC
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.9), dpi=300, sharey=True)
    for ax, load in zip(axes, loads):
        for model in MODELS:
            xs, ys = ccdf(hist[(load, model, "AC_VI", "packet")])
            ax.step(xs, ys, where="post", color=MODEL_COLOR[model], ls=MODEL_LS[model], lw=2.2)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(0.1, 100)
        ax.set_ylim(1e-3, 1.5)
        ax.set_title(f"{load:.2f} Mb/s per AC", fontsize=FONT, color=INK)
        ax.set_xlabel("AC_VI packet delay x [ms]", fontsize=FONT, color=INK)
        ax.tick_params(labelsize=FONT - 2)
        style_axes(ax)
    axes[0].set_ylabel("P(delay > x)", fontsize=FONT, color=INK)
    handles = [Line2D([], [], color=MODEL_COLOR[m], ls=MODEL_LS[m], lw=2.2, label=MODEL_LABEL[m])
               for m in MODELS]
    fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False, fontsize=FONT - 2,
               labelcolor=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(os.path.join(out, "pilot_vi.png"), transparent=True)


def traffic_ccdf(here, out):
    """Pooled CCDF of normalised inter-arrival times. For a Poisson source
    the gap divided by its mean is Exp(1): P(gap / mean > x) = e^-x, a
    straight line on a logarithmic y axis. The model mean (not the measured
    one) is used, so a wrong rate would shift the curve."""
    files = sorted(glob.glob(os.path.join(here, "..", "results", "traffic", "raw", "*.arrivals")))
    if not files:
        raise SystemExit("no arrival logs: run 'run.sh traffic' first")
    norm, n_streams, ratios = [], 0, []
    for path in files:
        load, vi_model = summary_row(path)
        stream_rate_bps = load * 1e6 / STREAMS_PER_AC
        for (ac, _), (t, _, size) in read_arrivals(path).items():
            if ac == BURST_AC and vi_model.startswith("burst"):
                continue
            mean_model_s = 8 * size[0] / stream_rate_bps
            gaps = np.diff(t)
            norm.append(gaps / mean_model_s)
            ratios.append(gaps.mean() / mean_model_s)
            n_streams += 1
    x = np.sort(np.concatenate(norm))
    ccdf = 1.0 - np.arange(1, len(x) + 1) / len(x)
    keep = ccdf > 0  # the last point has CCDF 0, not drawable on a log axis

    fig, ax = plt.subplots(figsize=(6.4, 4.3), dpi=300)
    grid = np.linspace(0, 10, 200)
    ax.plot(grid, np.exp(-grid), color=MUTED, lw=1.4, ls=(0, (4, 3)),
            label="Poisson model: $e^{-x}$")
    ax.plot(x[keep], ccdf[keep], color=COLOR["AC_VO"], lw=2.2,
            label=f"ns-3: {n_streams} streams, {len(x):,} gaps".replace(f"{len(x):,}",
                                                                     f"{len(x):,}".replace(",", "\u2009")))
    ax.set_yscale("log")
    ax.set_xlim(0, 10)
    ax.set_ylim(1e-5, 1.2)
    ax.set_xlabel("Gap between packets / expected mean gap", fontsize=FONT, color=INK)
    ax.set_ylabel("Share of gaps longer than x", fontsize=FONT, color=INK)
    ax.tick_params(labelsize=FONT - 2)
    style_axes(ax)
    ax.legend(frameon=False, fontsize=FONT - 1, labelcolor=INK, loc="upper right")
    ax.text(0.03, 0.04, f"Measured mean / expected mean = {np.mean(ratios):.4f}",
            transform=ax.transAxes, fontsize=FONT - 2, color=INK)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "traffic_ccdf.png"), transparent=True)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.path.join(here, "..", "results", "slides"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    bk_zoom(here, args.out)
    pilot_vi(here, args.out)
    traffic_ccdf(here, args.out)
    print(f"written: {args.out}/bk_zoom.png, pilot_vi.png, traffic_ccdf.png")


if __name__ == "__main__":
    main()