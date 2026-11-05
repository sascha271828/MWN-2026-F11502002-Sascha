# <center>A3 — Literature Review</center>

- [A3 — Literature Review](#a3--literature-review)
  - [1 Overview](#1-overview)
  - [2 Literature Review](#2-literature-review)
  - [3 Revised Project Proposal](#3-revised-project-proposal)
  - [4 Reflections on last Submission and Presentation / Considerations for A4](#4-reflections-on-last-submission-and-presentation--considerations-for-a4)

## 1 Overview
 
| Document | Content |
| :--- | :--- |
| [Literature Review](doc/literature-review.md) | Three IEEE papers: problem, importance, challenges, system model, experimental results, ns-3 settings, consequences for the project |
| [Revised Project Proposal](doc/revised-project-proposal.md) | Updated proposal in the planning template, with a table of all changes since A1 |
 
 
## 2 Literature Review
 
The assigned paper by Mangold et al. remains the basis of the project and is therefore part of the literature review.
Two further papers were found on IEEE Xplore and selected based on the following criteria:
1. They analyse 802.11e EDCA with per AC metrics (throughput, delay).
2. They contain a simulation section with an explicit parameter table, so that the setting can be translated into ns-3.
3. They model what Mangold et al. only describe qualitatively (AIFS and CW per AC, virtual collisions, retry limit).
Both papers cite the work of the Mangold group and extend Bianchi's analytical model of the legacy DCF (G. Bianchi, "Performance analysis of the IEEE 802.11 distributed coordination function," IEEE JSAC, vol. 18, no. 3, pp. 535-547, Mar. 2000) to EDCA.
 
| # | Paper | Role in the project |
| :-- | :--- | :--- |
| 1 | [Analysis of IEEE 802.11e for QoS support in wireless LANs](doc/literature-review.md#1-analysis-of-ieee-80211e-for-qos-support-in-wireless-lans) (Mangold et al., 2003) | Assigned paper, source of the A4 baseline (Fig. 8) |
| 2 | [Performance analysis of IEEE 802.11e contention-based channel access](doc/literature-review.md#2-performance-analysis-of-ieee-80211e-contention-based-channel-access) (Kong et al., 2004) | Analytical EDCA model; shows that AIFS differentiation can starve low priority ACs |
| 3 | [Throughput and delay performance of IEEE 802.11e enhanced distributed channel access (EDCA) under saturation condition](doc/literature-review.md#3-throughput-and-delay-performance-of-ieee-80211e-enhanced-distributed-channel-access-edca-under-saturation-condition) (Huang and Liao, 2007) | Analytical EDCA model with 802.11a timing and four ACs; definitions of MAC delay and jitter |
 
 
## 3 Revised Project Proposal
 
The research question from A1 is unchanged: 

**Does EDCA prioritisation behave as in Fig. 8 of Mangold et al. when AC_VI carries bursty 3GPP traffic instead of Poisson traffic at the same mean load?**

The literature review changed how the question is answered.
The baseline is now defined correctly (Fig. 8 is a load sweep, with all frames at 24 Mb/s), it is complemented by an analytical cross-check based on Kong et al. or Huang and Liao, the metrics include access delay and jitter per AC in addition to throughput, and the TXOP limit becomes an explicit parameter of the modification.
The full proposal, including a table of all changes and their reasons, is in the [Revised Project Proposal](doc/revised-project-proposal.md).
 
 

## 4 Reflections on last Submission and Presentation / Considerations for A4

The feedback on A2 and the presentation raised points about the correctness and the assumptions of my first scenario.
They are not addressed in A3, because A3 is about the literature and the proposal.
They will be addressed in A4, as part of the baseline reproduction, since the A4 simulation reuses the same setup and generator:

1. **Verify the cause of the delays.** Check in Wireshark that the measured delays come from the expected mechanism (pose packets on AC_VO waiting behind AC_VI TXOP bursts) and not from a configuration error.
2. **Repeat the verification.** Run the traffic model verification again on the extended generator (with exponential inter-arrival times added for the baseline), so that both the Poisson and the 3GPP traffic are checked against their models.
3. **Eye buffer timing.** TR 26.926 allows both options, but its recommended configurations (Table 6.4-1) send both eye buffers at the same time, except VR2-6 (interleaved). A2 used the staggered variant. In A4, I switch the default to "same time" and keep staggered as a sensitivity variant, since it changes the burst size (2M every 1/F instead of M every 1/(2F)).
4. **Saturation.** I ran into saturation during the A2 simulations. In A4, I will first check every scenario with a temporarily increased channel capacity (for example a higher PHY rate) to confirm that the simulation itself works. Then I will monitor queue drops and queue length in every run, so that saturation is always detected rather than mistaken for a protocol effect.

