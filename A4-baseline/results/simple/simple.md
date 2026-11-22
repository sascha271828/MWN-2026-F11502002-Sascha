Saturation throughput [Mb/s], ns-3 mean ± 95 % CI half width over 5 runs.

Step 1: one AC alone, against the closed form

| AC | ns-3 | Closed form | Difference |
| :--- | ---: | ---: | ---: |
| AC_VO | 13.860 ± 0.002 | 13.861 | -0.01 % |
| AC_VI | 13.064 ± 0.003 | 13.065 | -0.01 % |
| AC_BE | 11.423 ± 0.007 | 11.425 | -0.02 % |
| AC_BK | 10.384 ± 0.003 | 10.383 | +0.02 % |

Steps 2 to 4: several saturated ACs, against the reference model

| Case | AC | ns-3 | Model, EDCA rule | ns-3 minus model | Model, legacy rule | Paper Fig. 8 |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| VO+VI | AC_VO | 11.322 ± 0.018 | 11.318 (exact) | +0.004 | 12.126 |  |
| VO+VI | AC_VI | 2.748 ± 0.020 | 2.753 (exact) | -0.005 | 1.818 |  |
| VO+VI+BE | AC_VO | 11.230 ± 0.024 | 11.223 ± 0.003 (mc) | +0.007 | 12.103 |  |
| VO+VI+BE | AC_VI | 2.726 ± 0.020 | 2.728 ± 0.003 (mc) | -0.002 | 1.817 |  |
| VO+VI+BE | AC_BE | 0.121 ± 0.009 | 0.127 ± 0.001 (mc) | -0.006 | 0.025 |  |
| VO+VI+BE+BK | AC_VO | 11.227 ± 0.023 | 11.223 ± 0.003 (mc) | +0.005 | 12.103 | 12.82 |
| VO+VI+BE+BK | AC_VI | 2.725 ± 0.021 | 2.728 ± 0.003 (mc) | -0.003 | 1.817 | 1.30 |
| VO+VI+BE+BK | AC_BE | 0.125 ± 0.013 | 0.128 ± 0.001 (mc) | -0.003 | 0.025 | 0.00 |
| VO+VI+BE+BK | AC_BK | 0.000 ± 0.000 | 0.000 ± 0.000 (mc) | +0.000 | 0.000 | 0.00 |

Model: exact = Markov chain, mc = Monte Carlo (± standard error over the seeds). EDCA rule = ns-3 and IEEE 802.11-2020, legacy rule = DCF like countdown.
