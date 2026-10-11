# <center>A2 — ns-3 Setup & First Scenario</center>
- [A2 — ns-3 Setup \& First Scenario](#a2--ns-3-setup--first-scenario)
  - [1. ns-3 Setup](#1-ns-3-setup)
  - [2. First Scenario](#2-first-scenario)
    - [2.1 Traffic model](#21-traffic-model)
    - [2.2 Scenario](#22-scenario)
    - [2.3 Build and run](#23-build-and-run)
    - [2.4 Results](#24-results)
    - [2.5 Traffic model verification](#25-traffic-model-verification)
    - [2.6 Issues and lessons learned](#26-issues-and-lessons-learned)



## 1. ns-3 Setup

I installed **ns-3.48** (the latest release as of 28.09.2026) on my laptop running **Fedora Linux 44**, following the official [installation guide](doc/ns-3-installation.pdf) from the [ns-3 website](https://www.nsnam.org/documentation/).

Nothing broke during installation, configuration or the build. The unit test suite passed (see the detailed documentation for the test summary).

The full installation process and the platform details are documented [here](doc/installation_process.md).




## 2. First Scenario

The full documentation, including the reasoning behind the choices, is in [doc/first_scenario.md](doc/first_scenario.md). Source code: [src/xr-wifi/](src/xr-wifi/), analysis script: [scripts/plot_distributions.py](scripts/plot_distributions.py), results: [results/](results/).

### 2.1 Traffic model

- The linked "TS 26.926" is actually the **Technical Report TR 26.926 V19.0.0** (Release 19). In 3GPP numbering, the xx.9xx range is reserved for informative reports, so no TS with this number exists ([details](doc/first_scenario.md#11-tr-not-ts)).
- I use the **XR split rendering model of clause 6.5.3** (taken from TR 38.838), the only fully parameterised model in the report, plus the **pose uplink model of clause 5.9.2** ([details](doc/first_scenario.md#12-choice-of-the-model)).
- DL video: truncated Gaussian frame size with mean $M = R \cdot 10^6 / (2F) / 8$, STD 10.5 % of M, bounds ±50 %, sent periodically with truncated Gaussian jitter. With R = 10 Mbit/s and F = 60 fps: M = 10 417 byte every 8.33 ms (two staggered eye buffers per frame).
- UL pose: 60 byte payload every 10 ms.
- The generator is a **custom ns-3 application** (`XrTrafficApp`), generated with AI and verified statistically. Built-in applications cannot produce a frame size distribution, and the custom app is reusable for A4 ([details](doc/first_scenario.md#3-traffic-generator)).

### 2.2 Scenario

```
 STA  <---- DL XR video, AC_VI (TID 5) ----  AP
      ----- UL pose,     AC_VO (TID 6) ---->
```

802.11a as in the Mangold et al. paper, QoS (EDCA) enabled, constant rate 54 Mbit/s, 1 AP and 1 STA at 5 m. The access category is selected through the IP ToS byte ([details and assumptions](doc/first_scenario.md#4-scenario)).

### 2.3 Build and run

Symlink to run the source code from the ns-3 tree:
```
ln -s ~/projects/MWN-2026-F11502002-Sascha/A2-ns3-setup/src/xr-wifi \
  ~/ns-allinone-3.48/ns-3.48/scratch/xr-wifi
```

Build only the needed modules, then run. For further runs, change the run number: the seed stays fixed and a different random number substream is used.
```
~/ns-allinone-3.48/ns-3.48/ns3 configure --enable-modules="wifi;applications;internet;flow-monitor;mobility" --disable-examples --disable-tests

~/ns-allinone-3.48/ns-3.48/ns3 build

~/ns-allinone-3.48/ns-3.48/ns3 run "xr-wifi --enableUplink=true --simTime=20 --run=1 --outDir=$HOME/projects/MWN-2026-F11502002-Sascha/A2-ns3-setup/results/run1"

~/ns-allinone-3.48/ns-3.48/ns3 run "xr-wifi --enableUplink=true --simTime=20 --run=2 --outDir=$HOME/projects/MWN-2026-F11502002-Sascha/A2-ns3-setup/results/run2"
```

Plotting, in a venv that isolates the Python dependencies:
```
source ~/projects/MWN-2026-F11502002-Sascha/.venv/bin/activate

python ~/projects/MWN-2026-F11502002-Sascha/A2-ns3-setup/scripts/plot_distributions.py --results ~/projects/MWN-2026-F11502002-Sascha/A2-ns3-setup/results/run1

deactivate
```

### 2.4 Results

![First Run of Scenario](doc/06_scenario_run1.png)

| Flow | Metric | Run 1 | Run 2 |
| :--- | :--- | ---: | ---: |
| DL video (AC_VI) | Tx / Rx packets | 17 255 / 17 255 | 17 246 / 17 246 |
| | Throughput | 10.20 Mbit/s | 10.20 Mbit/s |
| | Mean / max delay | 1.29 / 5.31 ms | 1.29 / 6.88 ms |
| UL pose (AC_VO) | Tx / Rx packets | 1 899 / 1 899 | 1 899 / 1 899 |
| | Mean / max delay | 0.38 / 6.32 ms | 0.36 / 3.38 ms |

Wireshark confirms the setup on the air: video frames carry TID 5, pose frames TID 6, both at 54 Mbit/s on channel 36, and the I/O graph shows the video bursts recurring about every 8.33 ms.

![Wireshark, DL video frames with TID 5](doc/08_wireshark_dl_video.png)
![Wireshark I/O graph](doc/10_wireshark_io_graph.png)

A simple airtime model reproduces the numbers: one frame exchange takes 312 µs, the fragments of an eye buffer are sent in one TXOP, the channel load is about 29 % and the predicted mean DL delay of 1.35 ms is within 5 % of the measured value. The pose packets wait behind the video TXOPs, so the higher priority AC_VO is delayed by AC_VI bursts ([details](doc/first_scenario.md#63-plausibility-check-with-an-airtime-model)).

### 2.5 Traffic model verification

![Packet size, PMF and CDF, run 1](results/run1/plots/packet_size.png)
![Frame inter-arrival time, PDF and CDF, run 1](results/run1/plots/inter_arrival.png)

| Quantity | Model | Run 1 | Run 2 |
| :--- | ---: | ---: | ---: |
| Frame size mean / STD [B] | 10 417 / 1094 | ≈ 10 400 / 1092 | ≈ 10 410 / 1084 |
| Jitter STD [ms] | 1.76 | 1.72 | 1.74 |
| Inter-arrival mean / STD [ms] | 8.333 / 2.49 | 8.332 / 2.45 | 8.333 / 2.42 |
| KS p-values (size, jitter, inter-arrival) | | 0.77, 0.25, 0.73 | 0.85, 0.24, 0.48 |

All KS p-values are well above 0.05: the generated packet sizes and inter-arrival times are consistent with the TR 26.926 model. The jitter STD is 1.76 ms rather than 2 ms because truncation at ±2 STD narrows the distribution, and the inter-arrival STD is √2 times the jitter STD ([plots and derivation](doc/first_scenario.md#7-traffic-model-verification)).

### 2.6 Issues and lessons learned

- **Bug found by the verification:** `ns3::MilliSeconds()` only accepts integers and silently truncated the jitter. The code ran fine; only the KS test against the model revealed it.
- **ARP pending queue:** the first frame was sent before address resolution, and 4 fragments were dropped. Fixed by enlarging the queue.
- **Build time:** reduced by building only the needed modules and using ccache.

Limitations and next steps (A4: paper topology, 24/6 Mbit/s, one frame per TXOP, more replications) are listed [here](doc/first_scenario.md#9-limitations-and-next-steps).