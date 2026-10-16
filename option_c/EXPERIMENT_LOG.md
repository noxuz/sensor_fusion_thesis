# Option C — experiment log (literature pattern, not the defended method)

Hybrid: keep **`insfilterMARG`**, let the net model the leftover error (mean residual + noise σ). That is the practical stand-in for “the model is the noise” without rewriting MATLAB `AccelerometerNoise` / `Rpos` and re-running the filter.

**Not the defended method.** Do not put C in the Ch. 5 main table as the novel claim. A8q stays Option A. B1 stays Ch. 6. C is TLIO / AI-IMU / Al-Sharman / Wang territory.

Data: `../option_a/dataset.csv` + `filterstate.csv`.

| Run | Date | What | TEST ATE / RTE / quat | Notes |
|---|---|---|---|---|
| **C0** | 2026-09-05 | Dual-head TCN + EKF pose (7). δpose + log σ (NLL). `pose = EKF + μ`. | **0.89 / 0.29 / 5.44°** | Beats EKF quat (7.46°), **loses ATE/RTE** to raw EKF (0.78 / 0.20). Mean |C−EKF| ~0.71 m — over-corrected. Unfair vs A8q on ATE (sits on LLA filter). Literature pattern, not Ch. 5. |

## Design (C0)

- Filter stays frozen (`filterstate.csv`). No new Q/R inside `insfilterMARG`.
- Inputs: 1 s MARG+GPS-vel window **and** the EKF pose at the window end.
- Outputs: μ = (δpos, 0.1 s axis-angle) and log σ (6). Gaussian NLL on the EKF error.
- Apply independently at each window (the EKF is always on). Official ATE/RTE on 1 s hops.
- Full AI-IMU (CNN → new Q → rerun EKF) is not this run.
