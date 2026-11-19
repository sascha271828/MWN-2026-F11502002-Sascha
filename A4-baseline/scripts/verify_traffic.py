#!/usr/bin/env python3
"""Traffic model verification of the sources used in A4.

Checks the MSDU generation times logged by edca-fig8 (--arrivalFile, written
by "run.sh traffic") against the model the source is supposed to follow:

  Poisson streams  inter-arrival times ~ Exp(mean = 8 * MSDU / stream rate).
                   Per stream a Kolmogorov-Smirnov test with the nominal mean
                   (not fitted). With many streams the p-values themselves
                   must be uniformly distributed, so the summary reports the
                   share of p < 0.05 (expected 5 %) instead of single values.
  burst streams    one frame every 1/fps, a fixed number of MSDUs per frame,
                   all MSDUs of a frame generated at the same instant.

Usage:
    python verify_traffic.py [--results ../results/traffic] --streams 3 --fps 60
"""
import argparse
import csv
import glob
import os
from collections import defaultdict

import numpy as np
from scipy import stats

BURST_AC = "AC_VI"  # the only AC that uses the burst model


def read_arrivals(path):
    """{(ac, stream): (times [s], frame ids, MSDU bytes)} as arrays"""
    cols = defaultdict(lambda: ([], [], []))
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            t, f, b = cols[(r["ac"], int(r["stream"]))]
            t.append(int(r["time_ns"]) * 1e-9)
            f.append(int(r["frame_id"]))
            b.append(int(r["msdu_bytes"]))
    return {k: tuple(np.asarray(c) for c in v) for k, v in cols.items()}


def summary_row(path):
    """load, model of AC_VI and measurement time of the run that wrote the log"""
    with open(path[: -len(".arrivals")] + ".csv", newline="") as fh:
        r = next(csv.DictReader(fh))
    return float(r["load_mbps"]), r["vi_model"]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", default=os.path.join(here, "..", "results", "traffic"))
    ap.add_argument("--streams", type=int, required=True, help="streams per AC")
    ap.add_argument("--fps", type=float, required=True, help="frame rate of the burst model [1/s]")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.results, "raw", "*.arrivals")))
    if not files:
        raise SystemExit(f"no arrival logs in {args.results}/raw, run 'run.sh traffic' first")

    poisson = defaultdict(list)  # ac -> (p value, mean ratio, CV) per stream
    burst_lines = []
    for path in files:
        load, vi_model = summary_row(path)
        stream_rate_bps = load * 1e6 / args.streams
        for (ac, stream), (t, ids, size) in sorted(read_arrivals(path).items()):
            if ac == BURST_AC and vi_model.startswith("burst"):
                first = np.r_[True, ids[1:] != ids[:-1]]  # first MSDU of every frame
                starts = np.flatnonzero(first)
                counts = np.diff(np.r_[starts, len(ids)])[1:-1]  # whole frames only
                frame_time = t[starts][np.cumsum(first) - 1]
                assert np.all(t == frame_time), "MSDUs of a frame not generated together"
                periods = np.diff(t[starts])
                rate = 8 * size.sum() / (t[-1] - t[0] + 1 / args.fps) / 1e6
                burst_lines.append(
                    f"| {ac} / {stream} | {first.sum()} | {counts.min()} / {counts.max()} | "
                    f"{1e3 / args.fps:.3f} / {periods.mean() * 1e3:.3f} | "
                    f"{periods.std(ddof=1) * 1e3:.4f} | {stream_rate_bps / 1e6:.4f} / {rate:.4f} |")
            else:
                assert len(set(size)) == 1, "Poisson streams send MSDUs of one size"
                mean_model_s = 8 * size[0] / stream_rate_bps
                gaps = np.diff(t)
                p = stats.kstest(gaps, "expon", args=(0, mean_model_s)).pvalue
                poisson[ac].append((p, gaps.mean() / mean_model_s,
                                    gaps.std(ddof=1) / gaps.mean(), len(t)))

    lines = ["| AC | Streams | MSDUs per stream | Mean inter-arrival, measured / model | "
             "CV (model 1) | KS: share of p < 0.05 |", "| :--- | ---: | ---: | ---: | ---: | ---: |"]
    everything = []
    for ac in sorted(poisson) + ["All"]:
        v = np.asarray(everything if ac == "All" else poisson[ac])
        everything += [] if ac == "All" else poisson[ac]
        se = v[:, 1].std(ddof=1) / np.sqrt(len(v))
        lines.append(f"| {ac} | {len(v)} | {v[:, 3].mean():.0f} | {v[:, 1].mean():.4f} ± {se:.4f} | "
                     f"{v[:, 2].mean():.3f} | {100 * (v[:, 0] < 0.05).mean():.0f} % |")
    p_all = np.asarray(everything)[:, 0]
    lines += ["", f"KS test of the {len(p_all)} p-values against the uniform distribution: "
              f"p = {stats.kstest(p_all, 'uniform').pvalue:.2f}. ± is the standard error over "
              "the streams."]
    if burst_lines:
        lines += ["", "| Burst stream | Frames | MSDUs per frame (min / max) | "
                  "Frame period, model / measured [ms] | Period STD [ms] | "
                  "Mean rate, model / measured [Mb/s] |",
                  "| :--- | ---: | ---: | ---: | ---: | ---: |"] + burst_lines

    text = "\n".join(lines) + "\n"
    with open(os.path.join(args.results, "traffic.md"), "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
