#!/usr/bin/env python3
"""Digitise Fig. 8 of Mangold et al. (IEEE Wireless Communications, Dec. 2003).

The figure is embedded in the IEEE Xplore PDF as vector graphics, so the marker
positions can be read from the drawing commands instead of from pixels. The
script reads the marker centres of the four curves, converts them to data
coordinates with the axis tick marks and writes a CSV.

Usage:
    python digitise_fig8.py <paper.pdf> [--page 8] [--out ../reference/mangold_fig8.csv]

Requires PyMuPDF (pip install pymupdf). The PDF itself is not part of the
repository (copyright), only the resulting numbers are.
"""
import argparse
import csv
import math

import pymupdf

# Figure box and legend box on the page [pt], found by inspecting page.get_drawings()
PLOT = pymupdf.Rect(84, 45, 318, 220)
LEGEND = pymupdf.Rect(223, 75, 311, 117)

# Axis calibration from the tick marks [pt] -> value [Mb/s]
X_TICKS = {109.3: 3, 131.4: 6, 153.2: 9, 175.8: 12, 198.0: 15, 220.2: 18}
Y_TICKS = {191.0: 2, 167.4: 4, 143.8: 6, 120.2: 8, 96.1: 10, 73.0: 12}


def linfit(ticks):
    """Least squares line value = a * pt + b through the tick marks."""
    n = len(ticks)
    sx = sum(ticks)
    sy = sum(ticks.values())
    sxx = sum(p * p for p in ticks)
    sxy = sum(p * v for p, v in ticks.items())
    a = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    return a, (sy - a * sx) / n


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, default=8, help="0 based page index of Fig. 8")
    ap.add_argument("--out", default="mangold_fig8.csv")
    args = ap.parse_args()

    page = pymupdf.open(args.pdf)[args.page]
    ax, bx = linfit(X_TICKS)
    ay, by = linfit(Y_TICKS)

    closed = []  # (cx, cy, half size) of diamonds and circles
    vert, horiz, diag = [], [], []  # centres of short marker strokes
    for d in page.get_drawings():
        if d["color"] is None:  # white fill underlay of a marker, the outline follows
            continue
        items = d["items"]
        i = 0
        while i < len(items):
            it = items[i]
            # a closed marker: 4 consecutive segments returning to the start point
            if i + 3 < len(items) and all(s[0] in ("l", "c") for s in items[i : i + 4]):
                p0, p4 = it[1], items[i + 3][-1]
                pts = [s[1] for s in items[i : i + 4]]
                xs, ys = [p.x for p in pts], [p.y for p in pts]
                w, h = max(xs) - min(xs), max(ys) - min(ys)
                if abs(p0.x - p4.x) < 0.05 and abs(p0.y - p4.y) < 0.05 and 2.5 < w < 5.5 and abs(w - h) < 0.3:
                    closed.append(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, w / 2))
                    i += 4
                    continue
            if it[0] == "l":
                a, b = it[1], it[2]
                dx, dy = b.x - a.x, b.y - a.y
                length = math.hypot(dx, dy)
                c = ((a.x + b.x) / 2, (a.y + b.y) / 2)
                if 4.2 < length < 4.7 and abs(dx) < 0.05:
                    vert.append(c)
                elif 4.2 < length < 4.7 and abs(dy) < 0.05:
                    horiz.append(c)
                elif 4.2 < length < 4.7 and abs(abs(dx) - abs(dy)) < 0.1:
                    diag.append(c)
            i += 1

    def inside(c):
        p = pymupdf.Point(c[0], c[1])
        return PLOT.contains(p) and not LEGEND.contains(p)

    def pairs(seq):
        """A marker consists of two strokes with the same centre."""
        out = []
        for k, c in enumerate(seq):
            if any(math.hypot(c[0] - o[0], c[1] - o[1]) < 0.3 for o in seq[k + 1 :]):
                out.append(c)
        return out

    def cross(a, b):
        return [c for c in a if any(math.hypot(c[0] - o[0], c[1] - o[1]) < 0.3 for o in b)]

    curves = {
        "AC_VO": pairs(diag),                                  # x markers
        "AC_VI": [c[:2] for c in closed if c[2] < 2.0],        # circles (r = 1.6 pt)
        "AC_BE": cross(vert, horiz),                           # + markers
        "AC_BK": [c[:2] for c in closed if c[2] >= 2.0],       # diamonds (2.4 pt)
    }

    rows = []
    for ac, pts in curves.items():
        seen = set()
        for c in sorted(p for p in pts if inside(p)):
            x = round(ax * c[0] + bx, 2)
            y = round(max(ay * c[1] + by, 0.0), 2)
            if (x, y) not in seen:
                seen.add((x, y))
                rows.append((ac, x, y))

    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ac", "offered_mbps", "throughput_mbps"])
        w.writerows(rows)
    for ac in curves:
        print(ac, [(x, y) for a, x, y in rows if a == ac])
    print(f"x: {ax:.5f} Mb/s per pt, y: {ay:.5f} Mb/s per pt, {len(rows)} points -> {args.out}")


if __name__ == "__main__":
    main()
