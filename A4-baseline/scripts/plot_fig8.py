#!/usr/bin/env python3
"""Fig. 8 reproduction: merge the raw sweep results, compute confidence
intervals and plot the ns-3 curves against the digitised figure of the paper.

Usage:
    python plot_fig8.py [--results ../results/fig8] [--reference ../reference/mangold_fig8.csv]

Inputs
    <results>/raw/*.csv        one file per (load, run), written by edca-fig8 (run.sh fig8)
    <reference>                digitised Fig. 8 (digitise_fig8.py)
Outputs (in <results>)
    summary.csv                per (load, AC): mean, std, 95 % CI half width, n
    fig8.png                   same axes as the paper, ns-3 against the original
    comparison.md              ns-3 against the paper at the paper's load points
"""
import argparse
import csv
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


from a4lib import (ACS, COLOR, INK, MARKER, MUTED, group, interp, mean_ci, read_raw,
                   read_reference, style_axes)

LABEL = {"AC_VO": "AC_VO (voice)", "AC_VI": "AC_VI (video)",
         "AC_BE": "AC_BE (best effort)", "AC_BK": "AC_BK (background)"}
METRICS = ("offered_mbps", "throughput_mbps", "mean_delay_ms", "tx_pkts", "rx_pkts",
           "drop_queue", "drop_lifetime", "drop_retry")


def per_point(results):
    """{(load, ac): {metric: [value per run]}}"""
    data = {}
    for key, rows in group(read_raw(results), "load_mbps", "ac").items():
        data[key] = {m: [r[m] for r in rows] for m in METRICS}
    return data


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", default=os.path.join(here, "..", "results", "fig8"))
    ap.add_argument("--reference", default=os.path.join(here, "..", "reference", "mangold_fig8.csv"))
    args = ap.parse_args()

    data = per_point(args.results)
    ref = read_reference(args.reference)
    loads = sorted({k[0] for k in data})

    # ---------------------------------------------------------------- summary.csv
    summary = {}
    with open(os.path.join(args.results, "summary.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["load_mbps", "ac", "n_runs", "offered_mbps", "throughput_mbps", "std_mbps",
                    "ci95_mbps", "ci95_rel_pct", "mean_delay_ms", "loss_pct",
                    "drop_queue", "drop_lifetime", "drop_retry"])
        for load in loads:
            for ac in ACS:
                d = data[(load, ac)]
                mean, std, ci = mean_ci(d["throughput_mbps"])
                tx, rx = sum(d["tx_pkts"]), sum(d["rx_pkts"])
                n = len(d["throughput_mbps"])
                summary[(load, ac)] = (mean, ci, n)
                w.writerow([load, ac, n, f"{sum(d['offered_mbps']) / n:.4f}", f"{mean:.4f}",
                            f"{std:.4f}", f"{ci:.4f}",
                            f"{100 * ci / mean:.2f}" if mean > 0 else "",
                            f"{sum(d['mean_delay_ms']) / n:.3f}",
                            f"{100 * (tx - rx) / tx:.2f}" if tx else "",
                            f"{sum(d['drop_queue']) / n:.0f}", f"{sum(d['drop_lifetime']) / n:.0f}",
                            f"{sum(d['drop_retry']) / n:.0f}"])

    # ---------------------------------------------------------------- fig8.png
    fig, ax = plt.subplots(figsize=(8, 5.6), dpi=150)
    ax.plot([0, 14], [0, 14], color=MUTED, lw=1, ls=(0, (2, 2)), zorder=1)
    for ac in ACS:
        if ac in ref:
            ax.plot(*zip(*ref[ac]), color=COLOR[ac], lw=1.2, ls=(0, (4, 3)), alpha=0.75,
                    marker=MARKER[ac], ms=6, mfc="none", mew=1.2, zorder=2)
        x = [0.0] + loads
        y = [0.0] + [summary[(l, ac)][0] for l in loads]
        e = [0.0] + [0.0 if math.isnan(summary[(l, ac)][1]) else summary[(l, ac)][1] for l in loads]
        ax.errorbar(x, y, yerr=e, color=COLOR[ac], lw=2, marker=MARKER[ac], ms=7,
                    mfc="white", mew=1.6, capsize=3, elinewidth=1.2, zorder=3)

    # legend: colour and marker = AC, line style = source
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], color=COLOR[a], marker=MARKER[a], mfc="white", mew=1.6, lw=2,
                      label=LABEL[a]) for a in ACS]
    handles += [Line2D([], [], color=INK, lw=2, label="ns-3 (mean, 95 % CI)"),
                Line2D([], [], color=INK, lw=1.2, ls=(0, (4, 3)), alpha=0.75,
                       label="Mangold et al., Fig. 8 (digitised)"),
                Line2D([], [], color=MUTED, lw=1, ls=(0, (2, 2)), label="Total offer per AC")]
    ax.legend(handles=handles, loc="center right", frameon=False, fontsize=9, labelcolor=INK)

    n_runs = sorted({v[2] for v in summary.values()})
    ax.set_title("Throughput per AC with increasing offered traffic per AC\n"
                 f"ns-3 reproduction of Fig. 8, {'/'.join(map(str, n_runs))} runs per point",
                 loc="left", fontsize=11, color=INK)
    ax.set_xlabel("Offered traffic per AC (3 streams each) [Mb/s]", color=INK)
    ax.set_ylabel("Throughput per AC (3 streams each) [Mb/s]", color=INK)
    ax.set_xlim(-0.5, 31)
    ax.set_ylim(-0.3, 14)
    ax.set_xticks([0, 3, 6, 9, 12, 15, 18, 30])
    ax.set_yticks(range(0, 15, 2))
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(args.results, "fig8.png"))

    # ---------------------------------------------------------------- comparison.md
    with open(os.path.join(args.results, "comparison.md"), "w") as fh:
        fh.write("Throughput per AC [Mb/s]: ns-3 (mean ± 95 % CI half width) against the "
                 "digitised Fig. 8 (linearly interpolated at the simulated load).\n\n")
        fh.write("| Load | " + " | ".join(f"{a} ns-3 | {a} paper" for a in ACS)
                 + " | Total ns-3 | Total paper |\n")
        fh.write("| ---: |" + " ---: | ---: |" * (len(ACS) + 1) + "\n")
        for load in loads:
            cells, tot_s, tot_p = [], 0.0, 0.0
            for ac in ACS:
                mean, ci, _ = summary[(load, ac)]
                p = interp(ref.get(ac, []), load)
                tot_s += mean
                tot_p = tot_p + p if (p is not None and tot_p is not None) else None
                cells.append(f"{mean:.2f} ± {ci:.2f} | " + (f"{abs(p):.2f}" if p is not None else "n/a"))
            fh.write(f"| {load:g} | " + " | ".join(cells) + f" | {tot_s:.2f} | "
                     + (f"{tot_p:.2f}" if tot_p is not None else "n/a") + " |\n")

    print(f"{len(loads)} load points, runs per point: {n_runs}")
    print(f"written: summary.csv, fig8.png, comparison.md in {os.path.abspath(args.results)}")


if __name__ == "__main__":
    main()
