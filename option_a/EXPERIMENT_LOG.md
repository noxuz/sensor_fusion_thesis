# Option A — experiment log

Canonical pipeline: this folder. After each training run, copy `results.json` numbers into the table below (do not rely on notebook outputs; Jupyter overwrites).

Shared setup unless a row says otherwise:

- Data: `make_dataset.m` → `dataset.csv` (19 col) + `filterstate.csv`
- Split: chronological, 15% val / 15% test, gap between slices
- Optim: Adam, train-only normalization, CUDA
- Metrics on TEST vs GT; EKF is `insfilterMARG` on the same timestamps
- No GT pose in the network inputs

| Run | Date | What changed | Window / hop | Target | TEST A ATE / RTE / quat | EKF ATE / RTE / quat | Verdict |
|---|---|---|---|---|---|---|---|
| **A0** | 2026-09-05 | First increment model. Conv1d→LSTM→MLP, flatten all LSTM steps, 7-D head. | 11 samples (~69 ms) / 1 sample | per-step Δpos (3) + unit Δq (4) | **3.26 m / 0.43 m / 140.7°** | **0.80 m / 0.33 m / 7.45°** | Fail. Δq stuck at **180° every epoch**. Per-step Δpos ~2.4 mm looked fine; integration drifted. Not an architecture problem — 160 Hz Δq is ~identity. |
| **A1** | 2026-09-05 | Same backbone. LSTM last hidden. 6-D head. | **1.0 s / 0.1 s** | hop Δpos (3) + axis-angle (3) | **56.90 m / 7.49 m / 75.7°** | **0.80 m / 0.23 m / 7.46°** | Local Δθ **worked** (test Δθ RMSE **2.73°**, not 180°). Local Δpos RMSE **0.25 m/hop** is huge; 210 hops then explode (ATE 57 m). Fewer windows (971/210/210). Representation fix ≠ usable odometry. |
| **A2** | 2026-09-05 | 1 s mean velocity + `pos += v*dt`. Confirmed via `test_vel_rmse_m_s` in `results.json`. | 1.0 s / 0.1 s | vel (3) + hop axis-angle | **2.29 m / 0.44 m / 2.83°** | **0.80 m / 0.23 m / 7.46°** | First real A2 run. Pos still loses to EKF (~3× ATE) but is in the same league as A0 without a dead quat. **Quat beats EKF** (2.83° vs 7.46°). Vel RMSE 0.23 m/s; Δθ RMSE 0.10°. |
| **A3** | 2026-09-05 | 1 s hop + residual `δv` + K=3 unroll + val-ATE ckpt. n=97/21/21. GPS-vel int ATE/RTE **1.26 / 0.50**. | **1.0 s / 1.0 s** | δv (3) + hop axis-angle | **1.43 m / 0.44 m / 9.80°** | **0.85 m / 0.51 m / 7.48°** | Hop fix helped ATE (2.29→1.43). Residual **lost to raw GPS-vel integrate** (1.43 vs 1.26). Bias still 0.14 m/s. Vel RMSE worse (0.30). **Quat died** (2.83°→9.80°, late spike). RTE unchanged 0.44. Starved (97 windows) + unnormalized loss + ATE-only ckpt. |
| **A4** | 2026-09-05 | A3 hop kept. Residual dropped. Y-norm back. Ckpt `ATE+quat/90`. K=3. n=97/21/21. GPS-vel **1.26 / 0.50**. | **1.0 s / 1.0 s** | mean vel (3) + hop axis-angle | **2.64 m / 0.52 m / 16.0°** | **0.85 m / 0.51 m / 7.48°** | Fix failed. Worse than A3 and A2. Local Δθ 2.50° but integrated quat ramps to ~25°. Vel RMSE 0.32, bias 0.20 m/s. Loss-scale was not the main quat killer — **97 windows is**. |
| **A5** | 2026-09-05 | Overlap train (0.1 s extract, n=961/210/210) + 1 s integrate. 1 s Δθ. GPS-vel **1.10 / 0.45**. | **1.0 s / extract 0.1, int 1.0** | 1 s vel + **1 s** axis-angle | **2.61 m / 0.55 m / 9.42°** | **0.78 m / 0.20 m / 7.43°** | Data volume back, quat not. Local Δθ 3.06°/s vs A2’s 0.10°/0.1 s. Vel 0.35, bias 0.18. **1 s Δθ is the quat killer**, not sample count alone. |
| **A6** | 2026-09-05 | 0.1 s Δθ + 1 s pos integrate. n=961/210/210. GPS-vel **1.10 / 0.45**. | extract 0.1 / pos 1.0 / rot 0.1 | 1 s vel + **0.1 s** axis-angle | **2.24 m / 0.49 m / 5.67°** | **0.78 m / 0.20 m / 7.46°** | Close. Local Δθ **0.12°** (A2 was 0.10°). Quat beats EKF again. ATE ≈ A2. Vel 0.34 still loses to GPS-vel. Unroll + ATE ckpt left quat 2× A2. |
| **A7** | 2026-09-05 | A6 + residual `δv`, no unroll, ckpt `ATE+quat/30`. GPS-vel **1.10 / 0.45**. | extract 0.1 / pos 1.0 / rot 0.1 | δv + 0.1 s axis-angle | **1.38 m / 0.44 m / 12.8°** | **0.78 m / 0.20 m / 7.46°** | Best learned ATE so far, still loses to GPS-vel. **Quat died again** (5.67°→12.8°, spike ~17°). Same pattern as A3: residual/ATE pressure spends the shared 6-D head. |
| **A8** | 2026-09-05 | Dual-head TCN. Selected **ATE ckpt** (`ATE+quat/30`). Val other ckpt: ATE 1.65 / quat **1.99°**. GPS-vel **1.10 / 0.45**. | extract 0.1 / pos 1.0 / rot 0.1 | δv + 0.1 s axis-angle | **0.93 m / 0.32 m / 14.3°** | **0.78 m / 0.20 m / 7.46°** | First ATE **below GPS-vel**. Vel 0.23, bias 0.09. Dual head works — val quat ckpt is 2°. Selection picked the dead-quat ATE winner. |
| **A8q** | 2026-09-05 | Same A8 weights, **quat checkpoint** on TEST (`results_a8_both.json`). Frozen as `option_a_a8q.pth` / `results_a8q.png`. | same | same | **1.12 m / 0.31 m / 4.95°** | **0.78 m / 0.20 m / 7.46°** | The missing row. Quat beats EKF (4.95° vs 7.46°). ATE ties GPS-vel (1.12 vs 1.10). **Do not overwrite the a8q files.** |
| **A9** | 2026-09-05 | Retrain of the A8 recipe (dual-head TCN, same split/targets/integrate), fresh seed. Quat ckpt. Current `results.json` (`RUN_ID=A9_TCN`). | extract 0.1 / pos 1.0 / rot 0.1 | δv + 0.1 s axis-angle | **1.53 m / 0.33 m / 5.03°** | **0.78 m / 0.20 m / 7.46°** | Did **not** beat A8q (1.12 / 0.31 / 4.95°). val best-quat ckpt 1.38 m / 2.25°; local Δθ RMSE 0.11°, vel RMSE 0.23, bias 0.10 m/s. One retrain misses the frozen row → A8q is a good-but-lucky snapshot. **A8q stays frozen; cited in Ch. 5/6 as the seed-variance caveat.** |

## A0 details (from executed notebook + `results.json`)

- device `cuda`; n = 15766 / 3382 / 3382
- train loss 25.6 → 16.2 over 100 epochs; val Δpos ~3.5e-3 → 4.0e-3 m/step (no real val gain)
- test Δpos RMSE 0.00236 m/step; test Δq **180°**
- last_train_loss 1.01 (after best-on-val restore this is not the selection metric)

**Why A0 was changed (do not “fix” with a Transformer first):**

1. Unit Δq at 160 Hz is numerically flat → orientation head never learns.
2. 69 ms window is shorter than the GPS hold (1 s) and shorter than IONet/RoNIN (1–2 s).
3. Chaining thousands of tiny Δpos errors is what produced ATE 3.26 m vs EKF 0.80 m.

## A1 details (from `results.json` + `results.png`)

- device `cuda`; n = 971 / 210 / 210 hops (~21 s of TEST)
- test hop RMSE: Δpos **0.25 m**, Δθ **2.73°**
- Integrated A is a large wrong loop (error up to ~80 m); EKF stays on GT
- Quat error ~40–70° then a spike past 160° at the end of TEST

**Read of A1:** changing the *target* did what we wanted for the diagnostic (Δθ left 180°). It did **not** beat the EKF. 25 cm of error every 0.1 s with any bias will walk tens of metres.

## A2 design notes

- `v = (pos[t] - pos[t − 1 s]) / 1 s` — smooth mean velocity, not the noisy 0.1 s hop Δpos.
- Hop axis-angle unchanged (A1's Δθ RMSE 2.73° was usable).
- Integrate `pos += v * HOP_SEC` so a 0.25 m/s velocity error is 2.5 cm per hop, not 25 cm.

## A1 design notes

- Input still 12 ch (MARG + GPS vel).
- Target increment is over the **hop** (0.1 s), context is **1 s** — so overlapping windows are not integrated 10×.
- Axis-angle: `quat → rotvec` with `q` / `-q` folded (`w ≥ 0`).
- Integrate: `pos += Δpos`; `q ← q ⊗ quat(rotvec)`.
- RTE hop-aware (`sec/hop` steps).
- Writes `results.json`, `results.npz`, `results.png`, `option_a.pth`.

## A3 plan (five-angle review, 2026-09-05)

Sources: Information, Head, Time, Loss, Data agents; synthesis `f67ff60c`.

**Ran (`RUN_ID=A3_RES`). See table. Do not treat as a win.**

1. Hop = 1 s (match mean-v window), GAP = 1. Stops applying one 1 s average ten times per second.
2. Residual vel: `v̂ = v_gps_last + δv`, loss on `δv` in m/s.
3. Unroll K=3 hops in the train loss; checkpoint on val ATE (not window MSE).
4. Extra eval only (not a training change): GPS-vel integrate baseline + first/last 10 s per-axis ATE.

**Do not:** new backbone; hop-Δpos (A1); ZOH LLA into the 12-D stream; add prev pose; touch the quat head.

**Judge A3 on the same TEST (120–141 s):** RTE ≤ 0.30 m, vel RMSE ≤ 0.12 m/s, |vel bias| ≪ 0.14 m/s, ATE ≲ 1.2 m. Beat EKF ATE only if ≤ 0.80 m. Also first/last 10 s per-axis and a **velocity-only EKF** ablation (fair baseline). Quat must stay ≲ 3°.

**Framing:** EKF ATE uses GPS position; A is open-loop integrate of GPS-vel residuals. RTE + vel-only EKF are the fair position comparison. Quat 2.83° vs 7.46° is already like-for-like.

## A4 plan (fix A3, 2026-09-05)

Keep hop = 1 s. Drop residual (`δv` lost to GPS-vel integrate). Restore A2 mean-velocity target + Y normalization. Checkpoint `val ATE + quat/90`. Keep K=3 unroll.

**Ran (`RUN_ID=A4_BAL`). Worse than A3. Do not keep.**

## A5 plan (overlap train / 1 s integrate, 2026-09-05)

Train on 0.1 s-strided 1 s windows (~960, A2 volume). Target = 1 s mean vel + 1 s axis-angle. Integrate **every 1 s** at val/test. Y-norm, dense window loss + K=3 unroll on the 1 s grid, ckpt `ATE+quat/90`. GAP = 10 (1 s).

**Ran (`RUN_ID=A5_OVLP`). 1 s Δθ kept quat dead. See table.**

## A6 plan (0.1 s rot / 1 s pos, 2026-09-05)

A5 showed sample count was not enough: 1 s Δθ RMSE 3.06° vs A2’s 0.10° / 0.1 s. A6 = A2 rotation target + A3 position hop.

**Ran (`RUN_ID=A6_MIX`). Close: quat beats EKF, ATE still GPS-vel’s problem.**

## A7 plan (residual vel on A6 rot, 2026-09-05)

Keep 0.1 s Δθ. `v̂ = v_gps + δv`, 1 s pos integrate. Drop unroll. Ckpt `ATE + quat/30`. Floor if δv→0 is GPS-vel ATE 1.10 m.

**Ran (`RUN_ID=A7_RES`). Best ATE, dead quat. Shared 6-D head.**

## A8 plan (dual-head TCN, 2026-09-05)

1D TCN (64 ch, dilations 1/2/4/8) + separate vel/rot heads. Same A7 targets/integrate. Two val ckpts; pick `ATE+quat/30`.

**Implemented (`RUN_ID=A8_TCN`). Awaiting Restart + Run All.**

## A9 (retrain / seed check, source of current `results.json`)

Same A8 recipe, re-run with a fresh seed to see whether A8q reproduces. It did not: TEST 1.53 / 0.33 / 5.03° vs A8q's 1.12 / 0.31 / 4.95°. Orientation held (local Δθ RMSE 0.11°, quat 5.03°) but ATE drifted up ~0.4 m. This is the seed-variance evidence the thesis uses (Ch. 5 ablation, Ch. 6 future work "several random seeds on A8q would be more valuable than another architecture"). **A8q (`option_a_a8q.pth`) stays the defended row; do not promote A9.**

## Later ideas (not runs yet)

- Position-only A vs EKF if quat integration still dies.
- B (recursive closed-loop) stays Trabajo Futuro.

## How to append a run

1. Run All on `train.ipynb`.
2. Open `results.json`.
3. Add a row to the table (A2, A3, …) with the one-line “what changed.”
