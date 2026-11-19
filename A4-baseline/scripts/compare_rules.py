#!/usr/bin/env python3
"""Fig. 8 with two backoff countdown rules in ns-3 against the paper.

  standard  stock ns-3.48 (IEEE 802.11-2020 EDCA countdown)
  legacy    ns-3.48 with patches/legacy-countdown.patch (DCF like countdown)

Usage:
    python compare_rules.py [--standard ../results/fig8] [--legacy ../results-legacy/fig8]
                            [--reference ../reference/mangold_fig8.csv]

Inputs: summary.csv of both sweeps (plot_fig8.py). Output: <legacy>/rules.md
"""
import argparse
import csv
import os

from a4lib import ACS, interp, read_reference

LOADS = [3.6, 4.5, 7.5, 12.0, 30.0]  # collapse of BK, of BE, of VI, knee of VO, saturation


def read_summary(results):
    """{(load, ac): (mean throughput, CI half width, runs)}"""
    with open(os.path.join(results, "summary.csv"), newline="") as fh:
        return {(float(r["load_mbps"]), r["ac"]):
                (float(r["throughput_mbps"]), float(r["ci95_mbps"]), int(r["n_runs"]))
                for r in csv.DictReader(fh)}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--standard", default=os.path.join(here, "..", "results", "fig8"))
    ap.add_argument("--legacy", default=os.path.join(here, "..", "results-legacy", "fig8"))
    ap.add_argument("--reference", default=os.path.join(here, "..", "reference", "mangold_fig8.csv"))
    args = ap.parse_args()

    std, leg = read_summary(args.standard), read_summary(args.legacy)
    ref = read_reference(args.reference)
    runs = lambda s: "/".join(map(str, sorted({v[2] for v in s.values()})))

    lines = [f"Throughput per AC [Mb/s], mean ± 95 % CI half width. Standard rule: {runs(std)} "
             f"runs, legacy rule: {runs(leg)} runs. Paper: digitised Fig. 8, interpolated.", "",
             "| Load | AC | Paper | ns-3, standard rule | ns-3, legacy rule |",
             "| ---: | :--- | ---: | ---: | ---: |"]
    for load in LOADS:
        for ac in ACS:
            s, l = std[(load, ac)], leg[(load, ac)]
            lines.append(f"| {load:g} | {ac} | {abs(interp(ref[ac], load)):.2f} | "
                         f"{s[0]:.2f} ± {s[1]:.2f} | {l[0]:.2f} ± {l[1]:.2f} |")
    text = "\n".join(lines) + "\n"
    with open(os.path.join(args.legacy, "rules.md"), "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
