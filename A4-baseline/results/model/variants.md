Saturation throughput [Mb/s], reference model, Monte Carlo, 3 seeds of 150000 frame exchanges. One change per row against Table 1.

| Countdown rule | Change | AC_VO | AC_VI | AC_BE | Total |
| :--- | :--- | ---: | ---: | ---: | ---: |
| Paper, Fig. 8 | | 12.82 | 1.30 | 0.00 | 14.12 |
| edca | Table 1 | 11.23 | 2.73 | 0.12 | 14.08 |
| edca | AIFSN of AC_VI = 3 | 12.46 | 1.35 | 0.17 | 13.98 |
| edca | CWmin of AC_VI = 15 | 11.78 | 2.09 | 0.17 | 14.03 |
| edca | backoff in [0, CW - 1] | 12.18 | 1.98 | 0.04 | 14.20 |
| legacy | Table 1 | 12.12 | 1.80 | 0.03 | 13.95 |
| legacy | AIFSN of AC_VI = 3 | 13.31 | 0.54 | 0.04 | 13.89 |
| legacy | CWmin of AC_VI = 15 | 12.58 | 1.31 | 0.03 | 13.92 |
| legacy | backoff in [0, CW - 1] | 13.18 | 0.92 | 0.00 | 14.10 |
