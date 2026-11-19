"""Shared helpers of the A4 analysis scripts: reading the raw ns-3 results,
confidence intervals, colours. All scripts use these, so every experiment is
aggregated in the same way."""
import csv
import glob
import math
import os
from collections import defaultdict

from scipy import stats

ACS = ["AC_VO", "AC_VI", "AC_BE", "AC_BK"]
# colour follows the entity (AC or arrival model), a marker or line style
# repeats it, so identity never depends on colour alone
COLOR = {"AC_VO": "#2a78d6", "AC_VI": "#eb6834", "AC_BE": "#1baf7a", "AC_BK": "#eda100"}
MARKER = {"AC_VO": "x", "AC_VI": "o", "AC_BE": "+", "AC_BK": "D"}
INK, MUTED, GRID = "#1a1a19", "#6b6a63", "#e4e3dc"

NUMERIC = ("load_mbps", "offered_mbps", "throughput_mbps", "tx_pkts", "rx_pkts",
           "mean_delay_ms", "std_delay_ms", "drop_queue", "drop_lifetime", "drop_retry",
           "tx_frames", "rx_frames", "mean_frame_delay_ms", "queue_pkts")


def read_raw(results):
    """All rows of <results>/raw/*.csv as dicts, numeric columns as float,
    run as int. One row is one (configuration, run, AC)."""
    files = sorted(glob.glob(os.path.join(results, "raw", "*.csv")))
    if not files:
        raise SystemExit(f"no raw results in {results}/raw, run scripts/run.sh first")
    rows = []
    for f in files:
        with open(f, newline="") as fh:
            for r in csv.DictReader(fh):
                for k in NUMERIC:
                    r[k] = float(r[k])
                if "ack_timeouts" in r:  # only written with --uplinkPose=true
                    r["ack_timeouts"] = float(r["ack_timeouts"])
                r["run"] = int(r["run"])
                check_packet_balance(r, f)
                rows.append(r)
    return rows


def check_packet_balance(r, source):
    """Every generated packet must be delivered or counted as a MAC drop.
    The difference can only be what sits in the MAC queue at the two edges of
    the measurement window, so it is bounded by the queue size. A larger
    difference means packets disappear somewhere else (for example above the
    MAC because of an unresolved ARP entry), and the run must not be used."""
    lost = r["tx_pkts"] - r["rx_pkts"] - r["drop_queue"] - r["drop_lifetime"] - r["drop_retry"]
    bound = r["queue_pkts"] + 20
    assert abs(lost) <= bound, (f"{source}: {r['ac']} has {lost:.0f} packets that are neither "
                                f"delivered nor dropped by the MAC (bound {bound:.0f})")


def group(rows, *keys):
    """{(key values): [rows]} in order of first appearance"""
    out = {}
    for r in rows:
        out.setdefault(tuple(r[k] for k in keys), []).append(r)
    return out


def mean_ci(values, conf=0.95):
    """mean, sample std, half width of the two sided Student t interval.
    The values are the results of independent runs (replications)."""
    n = len(values)
    mean = sum(values) / n
    if n < 2:
        return mean, 0.0, float("nan")
    std = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
    return mean, std, stats.t.ppf(0.5 + conf / 2, n - 1) * std / math.sqrt(n)


def read_reference(path):
    ref = defaultdict(list)
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            ref[r["ac"]].append((float(r["offered_mbps"]), float(r["throughput_mbps"])))
    return {ac: sorted(p) for ac, p in ref.items()}


def interp(points, x, tol=0.3):
    """Linear interpolation in a sorted list of (x, y). Just outside the range
    (within tol, the digitised x values are only accurate to about 0.1 Mb/s)
    the end point is used, further outside None is returned."""
    if not points:
        return None
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= x <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    for xe, ye in (points[0], points[-1]):
        if abs(x - xe) <= tol:
            return ye
    return None


def style_axes(ax):
    ax.grid(color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelcolor=INK)
