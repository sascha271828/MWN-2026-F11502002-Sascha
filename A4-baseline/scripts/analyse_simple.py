#!/usr/bin/env python3
"""Validation ladder: ns-3 against the reference model for saturated subsets
of the ACs, from one AC alone (closed form) to all four (end point of Fig. 8).

Usage:
    python analyse_simple.py [--results ../results/simple] [--model ../results/model]
                             [--reference ../reference/mangold_fig8.csv]

Inputs
    <results>/raw/*.csv     written by edca-fig8 (run.sh simple)
    <model>/model.csv       written by edca_model.py
    <reference>             digitised Fig. 8, used for the four AC case
Outputs (in <results>)
    simple.csv              per (case, AC): ns-3 mean and CI, model values
    simple.md               the same as tables for the study note
"""
import argparse
import csv
import os

from a4lib import ACS, group, interp, mean_ci, read_raw, read_reference

CASES = ["VO", "VI", "BE", "BK", "VO+VI", "VO+VI+BE", "VO+VI+BE+BK"]


def read_model(path):
    """{(case, rule, ac): (throughput, std error or None, method)}. The exact
    chain is preferred over the closed form (identical) and over Monte Carlo."""
    rank = {"exact": 0, "closed": 1, "mc": 2}
    best = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            key = (r["case"], r["rule"], r["ac"])
            if key not in best or rank[r["method"]] < rank[best[key][2]]:
                se = float(r["std_error_mbps"]) if r["std_error_mbps"] else None
                best[key] = (float(r["throughput_mbps"]), se, r["method"])
    return best


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", default=os.path.join(here, "..", "results", "simple"))
    ap.add_argument("--model", default=os.path.join(here, "..", "results", "model"))
    ap.add_argument("--reference", default=os.path.join(here, "..", "reference", "mangold_fig8.csv"))
    args = ap.parse_args()

    by_case = group(read_raw(args.results), "tag", "ac")
    model = read_model(os.path.join(args.model, "model.csv"))
    ref = read_reference(args.reference)

    out = []
    for case in CASES:
        active = ["AC_" + a for a in case.split("+")]
        for ac in ACS:
            rows = by_case[(case, ac)]  # KeyError if a case was not simulated
            mean, _, ci = mean_ci([r["throughput_mbps"] for r in rows])
            if ac not in active:
                assert mean == 0.0, f"{case}: {ac} is switched off but delivered packets"
                continue
            m_edca, se, method = model[(case, "edca", ac)]
            m_legacy = model[(case, "legacy", ac)][0]
            sat_load = rows[0]["load_mbps"]
            paper = interp(ref[ac], sat_load) if case == "VO+VI+BE+BK" else None
            retry = sum(r["drop_retry"] for r in rows) / len(rows)
            out.append(dict(case=case, ac=ac, n_runs=len(rows), ns3=mean, ci=ci, edca=m_edca,
                            edca_se=se, method=method, legacy=m_legacy, paper=paper,
                            drop_retry=retry))

    with open(os.path.join(args.results, "simple.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["case", "ac", "n_runs", "ns3_mbps", "ns3_ci95_mbps", "model_edca_mbps",
                    "model_edca_se_mbps", "model_method", "model_legacy_mbps", "paper_fig8_mbps",
                    "ns3_minus_model_mbps", "drop_retry_per_run"])
        for o in out:
            w.writerow([o["case"], o["ac"], o["n_runs"], f"{o['ns3']:.4f}", f"{o['ci']:.4f}",
                        f"{o['edca']:.4f}", "" if o["edca_se"] is None else f"{o['edca_se']:.4f}",
                        o["method"], f"{o['legacy']:.4f}",
                        "" if o["paper"] is None else f"{abs(o['paper']):.2f}",
                        f"{o['ns3'] - o['edca']:+.4f}", f"{o['drop_retry']:.0f}"])

    n_runs = sorted({o["n_runs"] for o in out})
    with open(os.path.join(args.results, "simple.md"), "w") as fh:
        fh.write(f"Saturation throughput [Mb/s], ns-3 mean ± 95 % CI half width over "
                 f"{'/'.join(map(str, n_runs))} runs.\n\n")
        fh.write("Step 1: one AC alone, against the closed form\n\n")
        fh.write("| AC | ns-3 | Closed form | Difference |\n| :--- | ---: | ---: | ---: |\n")
        for o in out:
            if "+" not in o["case"]:
                fh.write(f"| {o['ac']} | {o['ns3']:.3f} ± {o['ci']:.3f} | {o['edca']:.3f} | "
                         f"{100 * (o['ns3'] / o['edca'] - 1):+.2f} % |\n")
        fh.write("\nSteps 2 to 4: several saturated ACs, against the reference model\n\n")
        fh.write("| Case | AC | ns-3 | Model, EDCA rule | ns-3 minus model | Model, legacy rule "
                 "| Paper Fig. 8 |\n| :--- | :--- | ---: | ---: | ---: | ---: | ---: |\n")
        for o in out:
            if "+" in o["case"]:
                edca = f"{o['edca']:.3f}" + ("" if o["edca_se"] is None else f" ± {o['edca_se']:.3f}")
                fh.write(f"| {o['case']} | {o['ac']} | {o['ns3']:.3f} ± {o['ci']:.3f} | {edca} "
                         f"({o['method']}) | {o['ns3'] - o['edca']:+.3f} | {o['legacy']:.3f} | "
                         + ("" if o["paper"] is None else f"{abs(o['paper']):.2f}") + " |\n")
        fh.write("\nModel: exact = Markov chain, mc = Monte Carlo (± standard error over the "
                 "seeds). EDCA rule = ns-3 and IEEE 802.11-2020, legacy rule = DCF like "
                 "countdown.\n")
    print(open(os.path.join(args.results, "simple.md")).read())


if __name__ == "__main__":
    main()
