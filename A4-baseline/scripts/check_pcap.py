#!/usr/bin/env python3
"""Check the AP traces (run.sh pcap) against the EDCA timing.

Between the starts of two consecutive downlink QoS data frames of the AP lie

    DATA 204 us + SIFS 16 us + ACK 28 us + AIFS[AC] + k slots
  = 264 us + 9 us * m,      m = AIFSN[AC] + k,  k >= 0 (backoff or idle slots)

AC = access category of the second frame. ns-3 aligns every channel access to
the slot grid that starts at the end of the last busy period, so this also
holds after idle periods (then k includes the idle slots). The pcap stores
times in microseconds, so a gap may deviate by 1 us from the grid (rounding,
17 ns propagation delay). Any other gap, or m < AIFSN, would be an error.

Usage:
    python check_pcap.py [--results ../results/pcap]
Output: <results>/pcap.md
"""
import argparse
import glob
import os
import re
import struct
from collections import defaultdict

import edca_model as em

SLOT_US = em.SLOT_US
GAP0_US = em.T_DATA_US + em.SIFS_US + em.T_ACK_US + em.SIFS_US  # 264 us, AIFS without slots
AC_OF_TID = {6: "AC_VO", 7: "AC_VO", 4: "AC_VI", 5: "AC_VI",  # IEEE 802.11 UP -> AC
             0: "AC_BE", 3: "AC_BE", 1: "AC_BK", 2: "AC_BK"}
PCAP_MAGIC_US = 0xA1B2C3D4


def downlink_data(path):
    """(time [us], TID) of every QoS data frame sent by the AP (FromDS = 1)"""
    data = open(path, "rb").read()
    assert struct.unpack("<I", data[:4])[0] == PCAP_MAGIC_US, f"{path}: not a microsecond pcap"
    assert struct.unpack("<I", data[20:24])[0] == 127, f"{path}: link type is not radiotap"
    frames, off = [], 24
    while off < len(data):
        sec, usec, incl, _ = struct.unpack("<IIII", data[off:off + 16])
        pkt = data[off + 16:off + 16 + incl]
        off += 16 + incl
        rt = struct.unpack("<H", pkt[2:4])[0]       # radiotap header length
        fc0, fc1 = pkt[rt], pkt[rt + 1]
        is_qos_data = (fc0 >> 2) & 3 == 2 and (fc0 >> 4) & 15 == 8
        from_ds = fc1 & 3 == 2
        if is_qos_data and from_ds:
            frames.append((sec * 1_000_000 + usec, pkt[rt + 24] & 0x0F))  # 3-address QoS control
    return frames


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", default=os.path.join(here, "..", "results", "pcap"))
    args = ap.parse_args()
    files = sorted(glob.glob(os.path.join(args.results, "*.pcap")))
    if not files:
        raise SystemExit(f"no pcap files in {args.results}, run 'run.sh pcap' first")

    lines = ["Gap between the starts of consecutive downlink QoS data frames of the AP = "
             f"{GAP0_US} µs + 9 µs · m. m counts the slots after SIFS: AIFSN plus backoff "
             "(or idle) slots.", "",
             "| Trace | AC | Frames | Off the 9 µs grid | Smallest m (AIFSN) |",
             "| :--- | :--- | ---: | ---: | ---: |"]
    for path in files:
        frames = downlink_data(path)
        assert len(frames) > 100, f"{path}: only {len(frames)} downlink data frames"
        per_ac = defaultdict(list)
        off_grid = defaultdict(int)
        for (t0, _), (t1, tid) in zip(frames, frames[1:]):
            ac = AC_OF_TID[tid]
            m, r = divmod(t1 - t0 - GAP0_US, SLOT_US)
            if r == SLOT_US - 1:      # 1 us rounding below the next slot
                m, r = m + 1, 0
            if r > 1:
                off_grid[ac] += 1
                continue
            per_ac[ac].append(m)
        name = re.sub(r"-0-0\.pcap$", "", os.path.basename(path))
        for ac in em.PRIORITY:
            if ac not in per_ac and not off_grid[ac]:
                continue
            p = em.TABLE1[ac]
            ms = per_ac[ac]
            lines.append(f"| {name} | {ac} | {len(ms) + off_grid[ac]} | {off_grid[ac]} | "
                         f"{min(ms)} ({p.aifsn}) |")
            assert off_grid[ac] == 0, f"{path}: {ac} has gaps off the slot grid"
            assert min(ms) >= p.aifsn, f"{path}: {ac} transmitted before its AIFS"
    text = "\n".join(lines) + "\n"
    with open(os.path.join(args.results, "pcap.md"), "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
