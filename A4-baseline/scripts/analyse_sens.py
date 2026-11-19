#!/usr/bin/env python3
"""Sensitivity of the Fig. 8 baseline to parameters the paper does not report.

Usage:
    python analyse_sens.py [--results ../results/sens] [--reference ../reference/mangold_fig8.csv]

Inputs
    <results>/raw/*.csv     written by edca-fig8 (run.sh sens)
Outputs (in <results>)
    sens.md                 throughput per AC for every variant and load
"""
import argparse
import os

from a4lib import ACS, group, interp, mean_ci, read_raw, read_reference

LABEL = {
    "baseline": "Baseline (500 packets, 500 ms, no beacons, retry limit 7)",
    "queue-50p": "MAC queue 50 packets",
    "queue-5000p": "MAC queue 5000 packets",
    "lifetime-50ms": "MSDU lifetime 50 ms",
    "lifetime-5000ms": "MSDU lifetime 5000 ms",
    "beacons-on": "Beacons on",
    "retry-limit-4": "Retry limit 4",
}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", default=os.path.join(here, "..", "results", "sens"))
    ap.add_argument("--reference", default=os.path.join(here, "..", "reference", "mangold_fig8.csv"))
    args = ap.parse_args()

    points = group(read_raw(args.results), "tag", "load_mbps", "ac")
    ref = read_reference(args.reference)
    loads = sorted({k[1] for k in points})
    tags = list(LABEL)
    assert {k[0] for k in points} == set(tags), "simulated variants and LABEL differ"
    n_runs = sorted({len(v) for v in points.values()})

    with open(os.path.join(args.results, "sens.md"), "w") as fh:
        fh.write(f"Throughput per AC [Mb/s], mean ± 95 % CI half width over "
                 f"{'/'.join(map(str, n_runs))} runs. One parameter changed per row.\n")
        for load in loads:
            fh.write(f"\nOffered traffic {load:g} Mb/s per AC\n\n| Variant | "
                     + " | ".join(ACS) + " | Total |\n| :--- |" + " ---: |" * (len(ACS) + 1) + "\n")
            for tag in tags:
                cells, total = [], 0.0
                for ac in ACS:
                    mean, _, ci = mean_ci([r["throughput_mbps"] for r in points[(tag, load, ac)]])
                    total += mean
                    cells.append(f"{mean:.2f} ± {ci:.2f}")
                fh.write(f"| {LABEL[tag]} | " + " | ".join(cells) + f" | {total:.2f} |\n")
            paper = [abs(interp(ref[ac], load)) for ac in ACS]
            fh.write("| Paper, Fig. 8 | " + " | ".join(f"{p:.2f}" for p in paper)
                     + f" | {sum(paper):.2f} |\n")
    print(open(os.path.join(args.results, "sens.md")).read())


if __name__ == "__main__":
    main()
