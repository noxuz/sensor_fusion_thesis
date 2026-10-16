# Option B — experiment log (Trabajo Futuro)

Recursive net: sensors + **own** previous pose. Scheduled sampling during training. Closed-loop TEST.

**Not the defended method.** Do not put a half-dead B row in the main Ch. 5 table. A8q stays the Option A result (`option_a/option_a_a8q.pth`).

Data: `../option_a/dataset.csv` + `filterstate.csv` (run `option_a/make_dataset.m` once).

| Run | Date | What | TEST ATE / RTE / quat | Notes |
|---|---|---|---|---|
| **B0** | 2026-09-05 | Dual-head TCN + prev **pose** (pos+quat). SS 1→0. K=10 at 0.1 s pos. | **2.57 / 0.45 / 9.19°** | Lost to A8q. Teacher-forced **0.07 / 0.06 / 0.19°**. Closed ≈ GPS-vel; TF is a NED-position lookup. |
| **B1** | 2026-09-05 | Prev **vel+quat** (no NED pos). A8 1 s pos integrate. K=40. SS anneal 40% then p_gt=0. | **1.42 / 0.30 / 2.09°** | Knobs worked. Quat beats A8q (4.95°) and EKF (7.46°). ATE lost to A8q (1.12) and GPS-vel (1.10). Teacher 1.26 / 0.26 / 0.12° — gap is honest now, not a pose lookup. Still Ch. 6, not the defended row. |

## Design (B0)

- Inputs: 1 s MARG+GPS-vel window **and** previous pose (pos + quat).
- Outputs: δv + 0.1 s axis-angle (same heads as A8).
- Integrate every 0.1 s: `pos += (v_gps+δv)*0.1`, `q ← q ⊗ quat(Δθ)`.
- Train: sequences of 10 hops; `p_gt` linear 1→0 over the first 60% of epochs (Bengio scheduled sampling).
- Eval: seed first TEST pose from GT, then **never** GT again.
- Diagnostic print: teacher-forced TEST (GT prev) so the exposure-bias gap is visible.

## Design (B1)

- Inputs: sensors + **last velocity and quaternion only** (no NED position).
- Position integrate matches A8: `pos += v̂·1.0` on 1 s hops; quat still 0.1 s.
- Train: K=40 (4 s); `p_gt` 1→0 over the first 40% of epochs, then 0.
- Official ATE/RTE on the 1 s trajectory (same as A8q).
- TCN / LR / λ unchanged.
