#!/usr/bin/env bash
# Runs the A4 experiments: every configuration x every run number.
#
# Usage (from anywhere):
#   NS3_DIR=~/ns-allinone-3.48/ns-3.48 ./run.sh <experiment> [results-root]
#
#   fig8     Fig. 8 of the paper: all four ACs at the same load, load sweep
#   simple   validation ladder: saturated subsets of the ACs
#            (VO, VI, BE, BK alone, VO+VI, VO+VI+BE, VO+VI+BE+BK)
#   pilot    burstiness pilot: AC_VI as Poisson, as periodic bursts with random
#            phases and with aligned phases, at the same mean load
#   sens     sensitivity to the parameters the paper does not report (MAC
#            queue size, MSDU lifetime, beacons, retry limit) at two load points
#   traffic  arrival logs for the traffic model verification (verify_traffic.py)
#   all      the five above
#
# Environment variables (all optional):
#   NS3_DIR      ns-3 root, default ~/ns-allinone-3.48/ns-3.48
#   RUNS         run numbers for fig8 and pilot, default "1 2 3 4 5 6 7 8 9 10"
#   SIMPLE_RUNS  run numbers for simple, default "1 2 3 4 5"
#   SENS_RUNS    run numbers for sens, default "1 2 3"
#   TRAFFIC_RUNS run numbers for traffic, default "1 2 3 4 5 6 7 8"
#   SENS_LOADS   sens: offered traffic per AC [Mb/s], default "3.6 30"
#                (collapse of AC_BK and saturation)
#   MEAS         measurement window per run [s], default 30
#   LOADS        fig8: offered traffic per AC [Mb/s], default: load points of Fig. 8
#   SAT_LOAD     simple: offered traffic of an active AC [Mb/s], default 30
#   PILOT_LOADS  pilot: offered traffic per AC [Mb/s]. Default 2.94912 5.89824
#                8.84736 = 4, 8 and 12 MSDUs of 512 byte per video frame at
#                60 frames/s and 3 streams, so every MSDU of a burst is full.
#   PILOT_FPS    pilot: video frame rate per stream, default 60
#   JOBS         parallel simulations, default: number of CPU cores
#   EXTRA        extra arguments for edca-fig8, e.g. "--queueSize=100p"
#
# Each run writes its own CSV to <results-root>/<experiment>/raw/, so the runs
# can be executed in parallel. Existing files are skipped: delete a file (or
# the folder) to repeat a point. The analysis scripts merge the raw files.
set -euo pipefail

EXPERIMENT="${1:?usage: run.sh fig8|simple|pilot|sens|traffic|all [results-root]}"
NS3_DIR="${NS3_DIR:-$HOME/ns-allinone-3.48/ns-3.48}"
RUNS="${RUNS:-1 2 3 4 5 6 7 8 9 10}"
SIMPLE_RUNS="${SIMPLE_RUNS:-1 2 3 4 5}"
SENS_RUNS="${SENS_RUNS:-1 2 3}"
SENS_LOADS="${SENS_LOADS:-3.6 30}"
TRAFFIC_RUNS="${TRAFFIC_RUNS:-1 2 3 4 5 6 7 8}"
MEAS="${MEAS:-30}"
LOADS="${LOADS:-1.5 3 3.6 4.2 4.5 6 7.5 9 12 15 18 30}"
SAT_LOAD="${SAT_LOAD:-30}"
PILOT_LOADS="${PILOT_LOADS:-2.94912 5.89824 8.84736}"
PILOT_FPS="${PILOT_FPS:-60}"
JOBS="${JOBS:-$(nproc)}"
EXTRA="${EXTRA:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(mkdir -p "${2:-$SCRIPT_DIR/../results}" && cd "${2:-$SCRIPT_DIR/../results}" && pwd)"

# ---------------------------------------------------------------- job lists
# one line per simulation: <output stem> <arguments of edca-fig8>
jobs_fig8() {
    for load in $LOADS; do
        for run in $RUNS; do
            echo "fig8/raw/load_${load}_run_${run} --tag=fig8 --load=$load --run=$run"
        done
    done
}

jobs_simple() {
    local s="$SAT_LOAD"
    while read -r tag vo vi be bk; do
        for run in $SIMPLE_RUNS; do
            echo "simple/raw/${tag}_run_${run} --tag=$tag --load=$s --run=$run" \
                 "--loadVO=$vo --loadVI=$vi --loadBE=$be --loadBK=$bk"
        done
    done <<CASES
VO $s 0 0 0
VI 0 $s 0 0
BE 0 0 $s 0
BK 0 0 0 $s
VO+VI $s $s 0 0
VO+VI+BE $s $s $s 0
VO+VI+BE+BK $s $s $s $s
CASES
}

jobs_pilot() {
    for load in $PILOT_LOADS; do
        for run in $RUNS; do
            local stem="pilot/raw/load_${load}"
            echo "${stem}_poisson_run_${run} --tag=pilot --load=$load --run=$run" \
                 "--viModel=poisson --delayFile=$ROOT/${stem}_poisson_run_${run}.delay"
            for phase in random aligned; do
                echo "${stem}_burst-${phase}_run_${run} --tag=pilot --load=$load --run=$run" \
                     "--viModel=burst --viFps=$PILOT_FPS --viPhase=$phase" \
                     "--delayFile=$ROOT/${stem}_burst-${phase}_run_${run}.delay"
            done
        done
    done
}

jobs_sens() {
    while read -r tag args; do
        for load in $SENS_LOADS; do
            for run in $SENS_RUNS; do
                # no trailing blank: xargs -L would join the line with the next one
                echo "sens/raw/${tag}_load_${load}_run_${run} --tag=$tag --load=$load --run=$run${args:+ $args}"
            done
        done
    done <<VARIANTS
baseline
queue-50p --queueSize=50p
queue-5000p --queueSize=5000p
lifetime-50ms --queueDelayMs=50
lifetime-5000ms --queueDelayMs=5000
beacons-on --beacons=true
retry-limit-4 --retryLimit=4
VARIANTS
}

jobs_traffic() {
    # all ACs Poisson at 3 Mb/s per AC (nothing is saturated), every MSDU logged
    for run in $TRAFFIC_RUNS; do
        echo "traffic/raw/poisson_run_${run} --tag=traffic --load=3 --run=$run" \
             "--arrivalFile=$ROOT/traffic/raw/poisson_run_${run}.arrivals"
    done
    # AC_VI as bursts, 8 MSDUs per frame
    echo "traffic/raw/burst_run_1 --tag=traffic --load=5.89824 --run=1 --viModel=burst" \
         "--viFps=$PILOT_FPS --arrivalFile=$ROOT/traffic/raw/burst_run_1.arrivals"
}

case "$EXPERIMENT" in
    fig8|simple|pilot|sens|traffic) EXPERIMENTS="$EXPERIMENT" ;;
    all) EXPERIMENTS="fig8 simple pilot sens traffic" ;;
    *) echo "unknown experiment: $EXPERIMENT" >&2; exit 1 ;;
esac

cd "$NS3_DIR"
./ns3 build edca-fig8

one() {
    local stem="$1"; shift
    local f="$ROOT/$stem.csv"
    [[ -s "$f" ]] && return 0
    ./ns3 run --no-build "edca-fig8 --measTime=$MEAS --verbose=false --outFile=$f.tmp $* $EXTRA"
    mv "$f.tmp" "$f"
    echo "done $stem"
}
export -f one
export ROOT MEAS EXTRA

for exp in $EXPERIMENTS; do
    mkdir -p "$ROOT/$exp/raw"
    # record what was run, so that it can be repeated
    {
        echo "date=$(date -Iseconds)"
        echo "ns3=$(cat VERSION 2>/dev/null || echo unknown)"
        echo "seed=1"
        echo "measTime=$MEAS"
        echo "extra=$EXTRA"
        case "$exp" in
            fig8)   echo "runs=$RUNS"; echo "loads=$LOADS" ;;
            simple) echo "runs=$SIMPLE_RUNS"; echo "satLoad=$SAT_LOAD" ;;
            pilot)  echo "runs=$RUNS"; echo "loads=$PILOT_LOADS"; echo "fps=$PILOT_FPS" ;;
            sens)   echo "runs=$SENS_RUNS"; echo "loads=$SENS_LOADS" ;;
            traffic) echo "runs=$TRAFFIC_RUNS" ;;
        esac
    } > "$ROOT/$exp/sweep.txt"
    "jobs_$exp" | xargs -P "$JOBS" -L 1 bash -c 'one "$@"' _
    echo "Raw results in $ROOT/$exp/raw ($(ls "$ROOT/$exp/raw" | grep -c '\.csv$') runs)"
done
