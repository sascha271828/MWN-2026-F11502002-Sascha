#!/usr/bin/env python3
"""Sensitivity of the saturated end of Fig. 8 to one-slot details of the EDCA
arbitration between AC_VO and AC_VI.

Uses the Monte Carlo reference model of edca_model.py (one station, four
saturated ACs, virtual collisions only) and changes one detail at a time:

  countdown rule   edca (ns-3, IEEE 802.11-2020) or legacy (DCF like)
  AIFSN of AC_VI   2 (Table 1) or 3
  CWmin of AC_VI   7 (Table 1) or 15
  backoff range    [0, CW] (standard) or [0, CW - 1]

Purpose: show how much the overload split depends on details that the paper
does not report. This is not a fit of the paper's simulator: several different
one-slot changes reproduce the paper about equally well.

Usage:
    python edca_variants.py --rounds 150000 --seeds 3 [--out ../results/model]
Output: <out>/variants.md
"""
import argparse
import os

import numpy as np

import edca_model as em
from edca_model import Ac

PAPER = {"AC_VO": 12.82, "AC_VI": 1.30, "AC_BE": 0.00}  # digitised Fig. 8 at 30 Mb/s


CW_OF = em.cw_of  # standard rule, kept before any replacement


def cw_standard(ac, qsrc):
    return CW_OF(ac, qsrc)


def cw_minus_one(ac, qsrc):
    """backoff drawn from [0, CW - 1] instead of [0, CW]"""
    return max(0, CW_OF(ac, qsrc) - 1)


def run(acs, rule, cw_fun, rounds, seeds):
    """Mean throughput per AC [Mb/s] over the seeds. edca_model.monte_carlo
    calls em.cw_of, which is replaced for the duration of the call."""
    em.cw_of = cw_fun
    try:
        thr = [em.monte_carlo(acs, rule, rounds, s) for s in range(1, seeds + 1)]
    finally:
        em.cw_of = CW_OF
    return np.mean(thr, axis=0)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rounds", type=int, required=True)
    ap.add_argument("--seeds", type=int, required=True)
    ap.add_argument("--out", default=os.path.join(here, "..", "results", "model"))
    args = ap.parse_args()

    T = em.TABLE1
    table1 = [T[k] for k in em.PRIORITY]
    vi_aifsn3 = [T["AC_VO"], Ac("AC_VI", 3, 7, 15), T["AC_BE"], T["AC_BK"]]
    vi_cw15 = [T["AC_VO"], Ac("AC_VI", 2, 15, 15), T["AC_BE"], T["AC_BK"]]
    variants = []
    for rule in ("edca", "legacy"):
        variants += [(rule, "Table 1", table1, cw_standard),
                     (rule, "AIFSN of AC_VI = 3", vi_aifsn3, cw_standard),
                     (rule, "CWmin of AC_VI = 15", vi_cw15, cw_standard),
                     (rule, "backoff in [0, CW - 1]", table1, cw_minus_one)]

    lines = [f"Saturation throughput [Mb/s], reference model, Monte Carlo, {args.seeds} seeds of "
             f"{args.rounds} frame exchanges. One change per row against Table 1.", "",
             "| Countdown rule | Change | AC_VO | AC_VI | AC_BE | Total |",
             "| :--- | :--- | ---: | ---: | ---: | ---: |",
             f"| Paper, Fig. 8 | | {PAPER['AC_VO']:.2f} | {PAPER['AC_VI']:.2f} | "
             f"{PAPER['AC_BE']:.2f} | 14.12 |"]
    for rule, label, acs, cw_fun in variants:
        r = run(acs, rule, cw_fun, args.rounds, args.seeds)
        lines.append(f"| {rule} | {label} | {r[0]:.2f} | {r[1]:.2f} | {r[2]:.2f} | {r.sum():.2f} |")
    text = "\n".join(lines) + "\n"
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "variants.md"), "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
