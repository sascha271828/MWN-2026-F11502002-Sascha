#!/usr/bin/env python3
"""Burstiness pilot: AC_VI as Poisson source against AC_VI as periodic bursts
(video frames) at the same mean load. All other ACs are Poisson in every case.

The question: which metric shows a difference between the arrival processes,
and at which load? Throughput is the control (expected: no difference).

Usage:
    python analyse_pilot.py [--results ../results/pilot]

Inputs
    <results>/raw/*.csv      per run summary, written by edca-fig8 (run.sh pilot)
    <results>/raw/*.delay    per run delay histograms (50 us bins)
Outputs (in <results>)
    pilot.csv                per (load, model, AC): throughput, loss, delay statistics
    pilot.md                 the same as tables for the study note
    pilot_ccdf.png           CCDF of the packet delay of AC_VO and AC_VI
"""
import argparse
import csv
import glob
import math
import os
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

from a4lib import ACS, INK, MUTED, group, mean_ci, read_raw, style_axes

MODELS = ["poisson", "burst-random", "burst-aligned"]
MODEL_LABEL = {"poisson": "Poisson", "burst-random": "Bursts, random phases",
               "burst-aligned": "Bursts, aligned phases"}
MODEL_COLOR = {"poisson": "#2a78d6", "burst-random": "#eb6834", "burst-aligned": "#1baf7a"}
MODEL_LS = {"poisson": "-", "burst-random": (0, (5, 2)), "burst-aligned": (0, (1, 1.5))}
OVERFLOW_US = 2_000_000  # edca-fig8 counts delays beyond 2 s in one last bin
QUANTILE = 0.99


def read_delay(results):
    """{(load, model, ac, kind): {run: {bin_upper_us: count}}}"""
    hist = defaultdict(lambda: defaultdict(dict))
    files = sorted(glob.glob(os.path.join(results, "raw", "*.delay")))
    if not files:
        raise SystemExit(f"no delay histograms in {results}/raw")
    for f in files:
        with open(f, newline="") as fh:
            for r in csv.DictReader(fh):
                edge = float(r["bin_upper_us"])
                assert edge <= OVERFLOW_US, f"{f}: delays beyond the histogram range"
                key = (float(r["load_mbps"]), r["vi_model"], r["ac"], r["kind"])
                hist[key][int(r["run"])][edge] = int(r["count"])
    return hist


def quantile_ms(bins, q):
    """Upper edge of the bin in which the q quantile lies [ms]."""
    total = sum(bins.values())
    acc = 0
    for edge in sorted(bins):
        acc += bins[edge]
        if acc >= q * total:
            return edge / 1e3
    raise AssertionError("empty histogram")


def ccdf(runs):
    """Pooled over the runs: (delay [ms], P(D > delay))"""
    pooled = defaultdict(int)
    for bins in runs.values():
        for edge, c in bins.items():
            pooled[edge] += c
    total = sum(pooled.values())
    xs, ys, acc = [], [], 0
    for edge in sorted(pooled):
        acc += pooled[edge]
        xs.append(edge / 1e3)
        ys.append(1 - acc / total)
    return xs, ys


def welch_diff(a, b, conf=0.95):
    """mean(a) - mean(b) and the half width of its Welch confidence interval"""
    ma, sa, _ = mean_ci(a)
    mb, sb, _ = mean_ci(b)
    va, vb = sa ** 2 / len(a), sb ** 2 / len(b)
    if va + vb == 0:
        return ma - mb, 0.0
    dof = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    return ma - mb, stats.t.ppf(0.5 + conf / 2, dof) * math.sqrt(va + vb)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", default=os.path.join(here, "..", "results", "pilot"))
    args = ap.parse_args()

    points = group(read_raw(args.results), "load_mbps", "vi_model", "ac")
    hist = read_delay(args.results)
    loads = sorted({k[0] for k in points})

    # ---------------------------------------------------------------- statistics
    res = {}
    for (load, model, ac), rows in points.items():
        rows = sorted(rows, key=lambda r: r["run"])
        thr = [r["throughput_mbps"] for r in rows]
        loss = [100 * (1 - r["rx_pkts"] / r["tx_pkts"]) for r in rows]
        d = dict(n=len(rows), thr=thr, loss=loss,
                 offered=sum(r["offered_mbps"] for r in rows) / len(rows),
                 mean_delay=[r["mean_delay_ms"] for r in rows],
                 frame_delay=[r["mean_frame_delay_ms"] for r in rows],
                 frame_loss=[100 * (1 - r["rx_frames"] / r["tx_frames"]) for r in rows],
                 drops={k: sum(r[k] for r in rows) / len(rows)
                        for k in ("drop_queue", "drop_lifetime", "drop_retry")})
        for kind in ("packet", "frame"):
            runs = hist[(load, model, ac, kind)]
            assert sorted(runs) == [r["run"] for r in rows], "delay files and runs differ"
            d[f"p99_{kind}"] = [quantile_ms(runs[run], QUANTILE) for run in sorted(runs)]
        res[(load, model, ac)] = d

    # ---------------------------------------------------------------- pilot.csv
    with open(os.path.join(args.results, "pilot.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["load_mbps", "vi_model", "ac", "n_runs", "offered_mbps", "throughput_mbps",
                    "throughput_ci95", "loss_pct", "loss_ci95", "mean_delay_ms", "mean_delay_ci95",
                    "p99_delay_ms", "p99_delay_ci95", "mean_frame_delay_ms", "p99_frame_delay_ms",
                    "frame_loss_pct", "drop_queue", "drop_lifetime", "drop_retry"])
        for load in loads:
            for model in MODELS:
                for ac in ACS:
                    d = res[(load, model, ac)]
                    cells = [load, model, ac, d["n"], f"{d['offered']:.4f}"]
                    for k in ("thr", "loss", "mean_delay", "p99_packet"):
                        m, _, ci = mean_ci(d[k])
                        cells += [f"{m:.4f}", f"{ci:.4f}"]
                    cells += [f"{mean_ci(d['frame_delay'])[0]:.4f}",
                              f"{mean_ci(d['p99_frame'])[0]:.4f}",
                              f"{mean_ci(d['frame_loss'])[0]:.4f}"]
                    cells += [f"{d['drops'][k]:.0f}"
                              for k in ("drop_queue", "drop_lifetime", "drop_retry")]
                    w.writerow(cells)

    # ---------------------------------------------------------------- pilot.md
    def cell(values, digits):
        m, _, ci = mean_ci(values)
        return f"{m:.{digits}f} ± {ci:.{digits}f}"

    n_runs = sorted({d["n"] for d in res.values()})
    with open(os.path.join(args.results, "pilot.md"), "w") as fh:
        fh.write(f"Mean ± 95 % CI half width over {'/'.join(map(str, n_runs))} runs. "
                 "Load = offered traffic per AC. Only AC_VI changes its arrival process.\n\n")

        fh.write("Control: throughput per AC [Mb/s]\n\n")
        fh.write("| Load | AC | Poisson | Bursts, random | Bursts, aligned | "
                 "Random minus Poisson | Aligned minus Poisson |\n"
                 "| ---: | :--- | ---: | ---: | ---: | ---: | ---: |\n")
        for load in loads:
            for ac in ACS:
                base = res[(load, "poisson", ac)]["thr"]
                diffs = []
                for model in MODELS[1:]:
                    dm, dci = welch_diff(res[(load, model, ac)]["thr"], base)
                    diffs.append(f"{dm:+.3f} ± {dci:.3f}")
                fh.write(f"| {load:.2f} | {ac} | "
                         + " | ".join(cell(res[(load, m, ac)]["thr"], 3) for m in MODELS)
                         + " | " + " | ".join(diffs) + " |\n")

        for title, key, digits in (("Mean packet delay [ms]", "mean_delay", 2),
                                   (f"{QUANTILE:.0%} quantile of the packet delay [ms] "
                                    "(50 µs bins)", "p99_packet", 2),
                                   ("Packet loss [%]", "loss", 2)):
            fh.write(f"\n{title}\n\n| Load | AC | Poisson | Bursts, random | Bursts, aligned |\n"
                     "| ---: | :--- | ---: | ---: | ---: |\n")
            for load in loads:
                for ac in ACS:
                    fh.write(f"| {load:.2f} | {ac} | "
                             + " | ".join(cell(res[(load, m, ac)][key], digits) for m in MODELS)
                             + " |\n")

        fh.write("\nAC_VI video frames (burst models; a Poisson \"frame\" is one MSDU)\n\n"
                 "| Load | Model | Mean frame delay [ms] | 99 % frame delay [ms] | "
                 "Incomplete frames [%] |\n| ---: | :--- | ---: | ---: | ---: |\n")
        for load in loads:
            for model in MODELS:
                d = res[(load, model, "AC_VI")]
                fh.write(f"| {load:.2f} | {MODEL_LABEL[model]} | {cell(d['frame_delay'], 2)} | "
                         f"{cell(d['p99_frame'], 2)} | {cell(d['frame_loss'], 2)} |\n")

    # ---------------------------------------------------------------- pilot_ccdf.png
    shown = ["AC_VO", "AC_VI"]
    fig, axes = plt.subplots(len(shown), len(loads), figsize=(3.6 * len(loads), 6.4), dpi=150,
                             sharex=True, sharey=True, squeeze=False)
    for i, ac in enumerate(shown):
        for j, load in enumerate(loads):
            ax = axes[i][j]
            for model in MODELS:
                xs, ys = ccdf(hist[(load, model, ac, "packet")])
                ax.step(xs, ys, where="post", color=MODEL_COLOR[model], ls=MODEL_LS[model], lw=2,
                        label=MODEL_LABEL[model])
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_ylim(1e-4, 1.5)
            ax.set_xlim(0.1, 1000)
            style_axes(ax)
            if i == 0:
                ax.set_title(f"{load:.2f} Mb/s per AC", fontsize=10, color=INK)
            if j == 0:
                ax.set_ylabel(f"{ac}\nP(delay > x)", color=INK)
            if i == len(shown) - 1:
                ax.set_xlabel("Packet delay x [ms]", color=INK)
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False, fontsize=9,
               labelcolor=INK, bbox_to_anchor=(0.5, 0.955), title="Arrival process of AC_VI",
               title_fontsize=9)
    fig.suptitle("Packet delay CCDF: AC_VI as Poisson source and as periodic bursts, same mean load",
                 x=0.01, ha="left", fontsize=11, color=INK)
    fig.text(0.01, 0.005, f"ns-3, pooled over {'/'.join(map(str, n_runs))} runs per curve, "
             "source to sink delay, 50 µs bins", fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 0.9))
    fig.savefig(os.path.join(args.results, "pilot_ccdf.png"))

    print(open(os.path.join(args.results, "pilot.md")).read())


if __name__ == "__main__":
    main()
