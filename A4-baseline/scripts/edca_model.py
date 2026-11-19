#!/usr/bin/env python3
"""Reference model for the saturated EDCA backoff entities of ONE station.

This is the independent reference for the ns-3 baseline (Scenario 2 of the
project proposal). It contains no ns-3 code, only the EDCA rules:

  * every AC has a saturated queue (always a frame to send)
  * all ACs sit in the same station, so only virtual (internal) collisions
    occur: the highest priority AC transmits, the others double their CW and
    draw a new backoff, no airtime is lost
  * retry counter per AC (QSRC, IEEE 802.11-2020 10.23.2.2, as in ns-3
    Txop::UpdateFailedCw): CW = min(CWmax, 2^QSRC * (CWmin + 1) - 1). A
    failure with QSRC already at the retry limit resets QSRC and CW.
  * one data frame per TXOP, error free channel, every frame is ACKed

One "round" is one frame exchange:

    | SIFS | m idle slots | DATA | SIFS | ACK |
             m = min over ACs of (AIFSN + backoff counter)

Three levels, from simple to full:

  closed form   one AC alone:  S = L / (T_ex + AIFS + CWmin/2 * slot)
  exact chain   stationary distribution of the Markov chain over the round
                start states (counter and QSRC of every AC). Only feasible for
                small state spaces, used for AC_VO + AC_VI.
  Monte Carlo   the same round rule with random draws, any set of ACs.

Countdown rules (the experimental variable of the model):

  edca    IEEE 802.11-2020 and ns-3 (ChannelAccessManager::UpdateBackoff):
          a counter is decremented at the slot boundary at the end of AIFS and
          at every following idle slot boundary. An AC that is interrupted
          after d idle slots past its AIFS has counted down d + 1.
  legacy  DCF like countdown: one decrement per completed idle slot after
          AIFS. An interrupted AC has counted down d.

In both rules an undisturbed AC transmits at AIFS + counter * slot.

Usage:
    python edca_model.py --rounds 400000 --seeds 10 --out ../results/model
"""
import argparse
import csv
import itertools
import math
import os
from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------- parameters
# IEEE 802.11a OFDM PHY, 20 MHz. All times in microseconds.
SLOT_US = 9
SIFS_US = 16
PREAMBLE_SIGNAL_US = 20  # PLCP preamble 16 us + SIGNAL 4 us
SYMBOL_US = 4
SERVICE_TAIL_BITS = 16 + 6

# Scenario of Fig. 8 (Mangold et al. 2003), as configured in edca-fig8.cc
RATE_MBPS = 24             # data and ACK
MSDU_BYTES = 512           # incl. LLC/SNAP, IP, UDP
MAC_OVERHEAD_BYTES = 26 + 4  # QoS data header + FCS
ACK_BYTES = 14
RETRY_LIMIT = 7            # ns-3 WifiMac::FrameRetryLimit (dot11ShortRetryLimit)


@dataclass(frozen=True)
class Ac:
    name: str
    aifsn: int
    cw_min: int
    cw_max: int


# Table 1 of the paper, in priority order (index 0 wins a virtual collision)
TABLE1 = {
    "AC_VO": Ac("AC_VO", 2, 3, 7),
    "AC_VI": Ac("AC_VI", 2, 7, 15),
    "AC_BE": Ac("AC_BE", 3, 15, 1023),
    "AC_BK": Ac("AC_BK", 7, 15, 1023),
}
PRIORITY = ["AC_VO", "AC_VI", "AC_BE", "AC_BK"]
RULES = ("edca", "legacy")

CASES = [
    ["AC_VO"], ["AC_VI"], ["AC_BE"], ["AC_BK"],
    ["AC_VO", "AC_VI"],
    ["AC_VO", "AC_VI", "AC_BE"],
    ["AC_VO", "AC_VI", "AC_BE", "AC_BK"],
]
EXACT_MAX_STATES = 5000  # the exact chain is only built for small state spaces


# ---------------------------------------------------------------- frame timing
def ofdm_duration_us(psdu_bytes, rate_mbps):
    """Duration of an 802.11a PPDU [us]: preamble + SIGNAL + data symbols."""
    bits_per_symbol = rate_mbps * SYMBOL_US  # Mb/s * us = bit
    n_sym = math.ceil((SERVICE_TAIL_BITS + 8 * psdu_bytes) / bits_per_symbol)
    return PREAMBLE_SIGNAL_US + SYMBOL_US * n_sym


T_DATA_US = ofdm_duration_us(MSDU_BYTES + MAC_OVERHEAD_BYTES, RATE_MBPS)
T_ACK_US = ofdm_duration_us(ACK_BYTES, RATE_MBPS)
# busy part of one round: SIFS (start of every AIFS) + DATA + SIFS + ACK
T_EXCHANGE_US = SIFS_US + T_DATA_US + SIFS_US + T_ACK_US
MSDU_BITS = 8 * MSDU_BYTES


def round_duration_us(m_slots):
    return T_EXCHANGE_US + m_slots * SLOT_US


# ---------------------------------------------------------------- closed form
def single_ac_saturation_mbps(ac):
    """One saturated AC alone: a new counter, uniform in [0, CWmin], after
    every frame. bit / us = Mb/s."""
    mean_slots = ac.aifsn + ac.cw_min / 2
    return MSDU_BITS / round_duration_us(mean_slots)


# ---------------------------------------------------------------- round rule
def cw_of(ac, qsrc):
    """Contention window after qsrc consecutive failures"""
    return min(ac.cw_max, 2 ** qsrc * (ac.cw_min + 1) - 1)


def resolve_round(acs, counters, qsrcs, rule):
    """Deterministic part of one round.

    acs      list of Ac in priority order
    counters backoff counter of every AC at the start of the round [slots]
    qsrcs    retry counter (consecutive virtual collisions) of every AC
    Returns (m, winner, colliders, counters_after, qsrcs_after). The counters
    of the winner and of the colliders still have to be drawn from
    [0, cw_of(ac, qsrc_after)].
    """
    access = [ac.aifsn + c for ac, c in zip(acs, counters)]
    m = min(access)
    ready = [i for i, a in enumerate(access) if a == m]
    winner, colliders = ready[0], ready[1:]

    counters_after = list(counters)
    qsrcs_after = list(qsrcs)
    for i, ac in enumerate(acs):
        if i == winner:
            qsrcs_after[i] = 0                              # success: CW = CWmin
        elif i in colliders:                                # virtual collision
            qsrcs_after[i] = qsrcs[i] + 1 if qsrcs[i] < RETRY_LIMIT else 0
        else:
            idle_after_aifs = m - ac.aifsn
            if idle_after_aifs >= 0:
                done = idle_after_aifs + (1 if rule == "edca" else 0)
                assert done <= counters[i], "a waiting AC cannot have reached zero"
                counters_after[i] = counters[i] - done
    return m, winner, colliders, counters_after, qsrcs_after


# ---------------------------------------------------------------- exact chain
def exact_chain(acs, rule):
    """Stationary throughput per AC [Mb/s] from the Markov chain embedded at
    the round starts. State: (counter, QSRC) of every AC. Returns None if the
    state space is larger than EXACT_MAX_STATES."""
    n = len(acs)
    start = tuple((0, 0) for _ in acs)
    index = {start: 0}
    todo = [start]
    rows = []  # per state: (state index, m, winner, {next state index: probability})
    while todo:
        state = todo.pop()
        counters = [s[0] for s in state]
        qsrcs = [s[1] for s in state]
        m, winner, colliders, c_after, q_after = resolve_round(acs, counters, qsrcs, rule)
        drawers = [winner] + colliders
        windows = [cw_of(acs[i], q_after[i]) for i in drawers]
        p = 1.0 / math.prod(w + 1 for w in windows)
        trans = {}
        for draw in itertools.product(*[range(w + 1) for w in windows]):
            c_next = list(c_after)
            for i, d in zip(drawers, draw):
                c_next[i] = d
            nxt = tuple((c_next[i], q_after[i]) for i in range(n))
            if nxt not in index:
                index[nxt] = len(index)
                todo.append(nxt)
                if len(index) > EXACT_MAX_STATES:
                    return None
            trans[index[nxt]] = trans.get(index[nxt], 0.0) + p
        rows.append((index[state], m, winner, trans))

    size = len(index)
    P = np.zeros((size, size))
    m_of = np.zeros(size)
    win_of = np.zeros(size, dtype=int)
    for s, m, winner, trans in rows:
        m_of[s], win_of[s] = m, winner
        for t, p in trans.items():
            P[s, t] = p
    assert np.allclose(P.sum(axis=1), 1.0), "transition rows must sum to 1"

    # stationary distribution: pi (P - I) = 0 with sum(pi) = 1
    A = np.vstack([P.T - np.eye(size), np.ones(size)])
    b = np.zeros(size + 1)
    b[-1] = 1.0
    pi, *_ = np.linalg.lstsq(A, b, rcond=None)
    assert np.allclose(A @ pi, b, atol=1e-9), "stationary distribution not found"
    assert pi.min() > -1e-9, "negative stationary probability"

    mean_round_us = float(pi @ (T_EXCHANGE_US + m_of * SLOT_US))
    return [MSDU_BITS * float(pi[win_of == i].sum()) / mean_round_us for i in range(n)], size


# ---------------------------------------------------------------- Monte Carlo
def monte_carlo(acs, rule, rounds, seed):
    """Throughput per AC [Mb/s] from `rounds` simulated rounds."""
    rng = np.random.default_rng(seed)
    n = len(acs)
    qsrcs = [0] * n
    counters = [int(rng.integers(0, ac.cw_min + 1)) for ac in acs]
    wins = [0] * n
    time_us = 0
    for _ in range(rounds):
        m, winner, colliders, counters, qsrcs = resolve_round(acs, counters, qsrcs, rule)
        for i in [winner] + colliders:
            counters[i] = int(rng.integers(0, cw_of(acs[i], qsrcs[i]) + 1))
        wins[winner] += 1
        time_us += round_duration_us(m)
    return [MSDU_BITS * w / time_us for w in wins]


def mean_se(samples):
    a = np.asarray(samples, dtype=float)
    se = a.std(ddof=1) / math.sqrt(len(a)) if len(a) > 1 else float("nan")
    return float(a.mean()), float(se)


# ---------------------------------------------------------------- main
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rounds", type=int, required=True, help="Monte Carlo rounds per seed")
    ap.add_argument("--seeds", type=int, required=True, help="Monte Carlo seeds 1..N")
    ap.add_argument("--out", default=os.path.join(here, "..", "results", "model"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    print(f"T_data {T_DATA_US} us, T_ack {T_ACK_US} us, SIFS {SIFS_US} us, slot {SLOT_US} us, "
          f"busy part of a round {T_EXCHANGE_US} us")

    rows = []
    for names in CASES:
        acs = [TABLE1[n] for n in names]
        case = "+".join(n[3:] for n in names)
        for rule in RULES:
            if len(acs) == 1:
                rows.append((case, rule, "closed", names[0], single_ac_saturation_mbps(acs[0]), ""))
            exact = exact_chain(acs, rule)
            if exact is not None:
                thr, size = exact
                for n, t in zip(names, thr):
                    rows.append((case, rule, f"exact({size} states)", n, t, ""))
            per_seed = [monte_carlo(acs, rule, args.rounds, seed)
                        for seed in range(1, args.seeds + 1)]
            for i, n in enumerate(names):
                mean, se = mean_se([s[i] for s in per_seed])
                rows.append((case, rule, "mc", n, mean, se))

    path = os.path.join(args.out, "model.csv")
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["case", "rule", "method", "ac", "throughput_mbps", "std_error_mbps"])
        for case, rule, method, ac, thr, se in rows:
            w.writerow([case, rule, method.split("(")[0], ac, f"{thr:.4f}",
                        f"{se:.4f}" if se != "" else ""])
    with open(os.path.join(args.out, "model.txt"), "w") as fh:
        fh.write(f"rounds={args.rounds}\nseeds=1..{args.seeds}\nnumpy={np.__version__}\n"
                 f"t_data_us={T_DATA_US}\nt_ack_us={T_ACK_US}\nretry_limit={RETRY_LIMIT}\n")

    print(f"{'case':<13}{'rule':<8}{'method':<20}{'AC':<7}{'Mb/s':>8}{'  SE':>8}")
    for case, rule, method, ac, thr, se in rows:
        print(f"{case:<13}{rule:<8}{method:<20}{ac:<7}{thr:>8.3f}"
              + (f"{se:>8.3f}" if se != "" else ""))
    print(f"written: {path}")


if __name__ == "__main__":
    main()
