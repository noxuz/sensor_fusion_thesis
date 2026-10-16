# Literature Review Notes — Deep-Learning IMU/GPS Sensor Fusion

Working notes for the Estado del Arte (Ch. 2) and Marco Teórico (Ch. 3) of the thesis.
**Thesis in one line:** a `Conv1d → LSTM → MLP` network that regresses state (position + quaternion) from MARG IMU (accel/gyro/mag) + GPS velocity + previous state, trained on MATLAB `insfilterMARG`-simulated data.

> ⚠ **Before final submission, verify every citation** (authors, venue, vol/issue/pages, DOI) from the publisher record. Items flagged "⚠ verify" had missing vol/pages in the preprint PDF.

---

## 1. Estado del Arte — comparison table

| Ref | Yr | Sensors | Learning model | Filter / hybrid | Output | Data | Metric | Headline result |
|---|---|---|---|---|---|---|---|---|
| RIDI [2] | 2018 | IMU (acc+gyro) | SVM + SVR (shallow) | Model-based integ.; orient. from Android fusion | 2D velocity → double-integrated position | Own (Tango GT) | MPE (% dist.) | < ~3% of distance |
| IONet [1] | 2018 | IMU (acc+gyro) | Bi-LSTM | None (pure DL) | Polar displacement (Δl, Δψ) | Own (Vicon/Tango GT) | Pos-error CDF | ~30–40% better than PDR |
| RoNIN [3] | 2020 | IMU (acc+gyro) | ResNet / LSTM / TCN | None at inference (KF only to refine training GT) | 2D velocity + heading | RoNIN 42.7 h, 100 subj. | ATE / RTE | ATE ≈ 3.5 m (seen) / 5.1 m (unseen) |
| OriNet [4] | 2020 | IMU (**gyro only**) | Multi-LSTM + MLP | None ("acts like EKF") | **Quaternion**, uses **prev. quaternion** | EuRoC MAV | Quaternion dist. θ_D | ~80% better vs. baseline; +30% vs. VINS-Mono |
| TLIO [5] | 2020 | IMU (acc+gyro) | 1D ResNet + uncertainty | **Stochastic-cloning EKF (tight hybrid)** | 3D displacement + cov → EKF state | Proprietary head-mounted | ATE/RTE/drift | −27% yaw, −33% pos drift vs. RoNIN-3D |
| AI-IMU [6] | 2020 | IMU (acc+gyro) | 1D CNN | **IEKF; net learns noise cov** | Adapts pseudo-meas. noise → state | KITTI | t_rel %, r_rel | ~1.10% translational error |
| Al-Sharman [7] | 2020 | IMU (attitude) | DNN (dropout, LM) | **KF; DNN refines KF output** | Denoised attitude | Sim + OptiTrack hover | RMSEE | roll 0.274→0.029 (sim) |
| Wang T-LSTM [8] | 2025 | IMU + INS-derived vel/att (12-D) | Transformer + LSTM | **15-state KF; predicts pseudo-GNSS** | 4-D GNSS pseudo-increments → KF | psins vehicle (STIM300) | RMSE | −90% vs. INS; −40% vs. LSTM/Transformer |
| Survey [9] | 2020 | — | Taxonomy | model / learning / hybrid | — | — | — | Anchor for framing |
| **This thesis** | 2024 | **MARG (acc+gyro+mag) + GPS vel + prev state** | **Conv1d→LSTM→MLP** | **None (direct regression)** | **Position + quaternion** | **MATLAB `insfilterMARG` (simulated)** | MSE (pos + quat) | *(to be re-evaluated — see caveats)* |

**Where the thesis sits / the gap:** almost all learned inertial odometry above is **IMU-only (acc+gyro), magnetometer-disabled, no GPS, real datasets**. This thesis is distinctive in (a) using the **full MARG suite incl. magnetometer + GPS velocity**, (b) a 7-D pose head (position + quaternion), and (c) training on **simulated `insfilterMARG` data**. Teacher-forced GT `prev_state` is **rejected** as the method to defend (see §6). Hybrid learning+filter (TLIO, AI-IMU, Al-Sharman, Wang) is the most crowded of the three remaining options, not the automatic upgrade.

---

## 2. Per-paper notes

### [1] IONet — Chen et al., AAAI 2018 (arXiv:1802.02209)
- **Idea:** break continuous integration; segment IMU into independent 2 s windows; Bi-LSTM regresses polar displacement (Δl, Δψ) → trajectory. IMU only; no filter.
- **Data/eval:** own dataset, Vicon/Tango GT; ~30–40% better than PDR; generalizes to trolley/stroller.
- **Limitation:** degrades on high-bias IMUs and unseen users; attachments trained separately.
- **Use for thesis:** canonical "DL replaces integration"; motivates windowing. Distinguish by MARG+GPS and full-state (incl. quaternion) output.
- **Quote:** "We propose to break the cycle of continuous integration, and instead segment inertial data into independent windows." (Abstract)

### [2] RIDI — Yan et al., ECCV 2018 (arXiv:1712.09004), pp. 621–636
- **Idea:** SVM classifies phone placement → per-type SVR regresses 2D velocity in gravity-aligned frame → least-squares bias correction → double integration. Shallow ML; orientation from Android (KF-style) fusion.
- **Data/eval:** own Tango-GT dataset; MPE < ~3% of travel distance.
- **Limitation:** flat-floor 2D, zero initial velocity; explicitly names **deep neural networks** as future work.
- **Use for thesis:** origin of "learn velocity then integrate" + gravity-aligned normalization; contrast shallow SVR vs. end-to-end DL.
- **Quote:** "Acquiring more training data and evaluating the accuracy of more data-hungry methods such as deep neural networks is one of our future works." (Sec. 6.2)

### [3] RoNIN — Herath, Yan & Furukawa, ICRA 2020 (arXiv:1905.12853) ⚠ verify pages 3146–3152
- **Idea:** large in-the-wild benchmark + 3 backbones (ResNet/LSTM/TCN) regressing 2D velocity from 1 s IMU window; heading-agnostic coordinate frame (HACF); robust velocity losses. No EKF at inference.
- **Data/eval:** RoNIN dataset 42.7 h / 100 subjects; ATE/RTE; ATE ≈ 3.5 m (seen)/5.1 m (unseen), far beating RIDI/IONet.
- **Limitation:** heavily reliant on device-orientation quality; magnetometer disabled.
- **Use for thesis:** adopt **ATE/RTE** metrics; architecture reference (LSTM/TCN). Position thesis as adding GPS + quaternion regression.
- **Quote:** "RoNIN uses a heading-agnostic coordinate frame (HACF), that is, any coordinate frame whose Z axis is aligned with gravity." (Sec. 4.1)

### [4] OriNet — Esfahani et al., IEEE RA-L 5(2):399–406, 2020, doi:10.1109/LRA.2019.2959507
- **Idea:** **closest precedent to the thesis's orientation design.** Multi-channel LSTM + MLP regress quaternion displacements from **gyro + Δt + previous-state quaternion**; averaging/weighting gates for robustness; GA gyro-bias calibration. Pure DL (no filter) but "acts like an EKF."
- **Data/eval:** EuRoC MAV; quaternion distance θ_D; ~80% better than baseline, +30% vs. VINS-Mono; prev-quaternion input gave +95% vs. their earlier model.
- **Limitation:** needs the same "particular" IMU and initial world quaternion; accelerometer unused.
- **Use for thesis:** **strongest justification for feeding the previous state and using LSTM for quaternion regression.**
- **Quote:** "similar to an EKF, the network can learn to perform an analysis and do the update process based on the previous state measurements and current values…" (Sec. IV-B)

### [5] TLIO — Liu et al., IEEE RA-L 2020 (arXiv:2007.01867) ⚠ verify vol.5,no.4,pp.5653–5660
- **Idea:** **tight learning+filter hybrid.** 1D ResNet regresses 3D displacement **+ uncertainty**; fused as measurement update in a **stochastic-cloning EKF** that also estimates velocity and biases.
- **Data/eval:** proprietary head-mounted, VIO pseudo-GT; −27% yaw drift, −33% pos drift vs. RoNIN-3D; uncertainty statistically consistent.
- **Limitation:** IMU used twice (breaks EKF independence); fails on unusual motions.
- **Use for thesis:** reference architecture for the **tight hybrid** upgrade path; contrast with thesis's filter-free regression.
- **Quote:** "…tightly fuse the relative state measurement into a stochastic cloning EKF to solve for pose, velocity and sensor biases." (Abstract)

### [6] AI-IMU Dead-Reckoning — Brossard et al., IEEE T-IV 2020 (arXiv:1904.06064) ⚠ verify vol.5,no.4,pp.585–595
- **Idea:** **complementary hybrid.** Invariant EKF with pseudo-measurements (near-zero lateral/vertical velocity); a small 1D CNN learns the **measurement-noise covariance** (when to trust the constraints). Net never sees the state.
- **Data/eval:** KITTI; ~1.10% translational error, IMU-only, competitive with LiDAR/stereo; survives GPS outage.
- **Limitation:** fixed process noise Q; cross-vehicle generalization open.
- **Use for thesis:** key citation for "learning + KF = tuning the filter, not replacing it."
- **Quote:** "The key components of the method are the Kalman filter and the use of deep neural networks to dynamically adapt the noise parameters of the filter." (Abstract)

### [7] Al-Sharman et al. — IEEE T-IM 69(1):24–34, 2020, doi:10.1109/TIM.2019.2895495
- **Idea:** DNN (3 hidden layers, dropout, Levenberg–Marquardt) takes **KF attitude estimates** as input, true states as target, learns to remove residual noise. DNN-refines-KF hybrid.
- **Data/eval:** multirotor sim + OptiTrack hover; RMSEE; large reductions (roll 0.274→0.029 sim).
- **Limitation:** real-flight noise non-Gaussian → needs retuning/retraining.
- **Use for thesis:** hybrid learning+KF for **attitude/orientation** specifically — parallels the thesis's orientation focus.
- **Quote:** "A deep neural network (DNN) is trained… to identify the associated measurement noise models and filter them out." (Abstract)

### [8] Wang et al. — Transformer–LSTM GNSS/INS, IEEE VTC2025-Fall (arXiv/DOI:10.1109/VTC2025-Fall65116.2025.11309847)
- **Idea:** **closest GNSS/INS + DL analog.** Transformer+LSTM on 12-D (IMU + INS-derived vel/att) predicts **4-D GNSS pseudo-increments**; during GNSS outage these feed a **15-state KF** for closed-loop INS correction.
- **Data/eval:** psins land-vehicle (STIM300, 125 Hz IMU / 1 Hz GNSS); 50 s outage; horizontal RMSE 5.48 m vs. 82.39 m (pure INS), −40% vs. LSTM/Transformer alone.
- **Limitation:** single dataset / single outage scenario.
- **Use for thesis:** justifies attention/LSTM temporal modeling for INS and the "predict GNSS obs to aid a KF" paradigm; gives a 3-way taxonomy of AI-aided GNSS/INS models.
- **Quote:** "The predicted GNSS pseudo-increments are then fused with INS outputs via the Kalman filter (KF) for state updates." (Abstract)

### [9] Survey — Chen et al., "DL for Localization and Mapping," arXiv:2006.12567, 2020 ⚠ verify if citing journal version
- **Idea/taxonomy:** odometry (visual, **visual-inertial §3.2**, **inertial §3.3**, LiDAR), mapping, global localization, SLAM; trichotomy **model-based / learning-based / hybrid**.
- **Open challenges:** end-to-end vs. hybrid (data hunger), lack of unified benchmark, real-world deployment, interpretability/uncertainty.
- **Use for thesis:** the framing anchor for Ch. 2 §2.5; its open challenges directly back the thesis's own caveats (sim-only, no closed-loop benchmark).
- **Quote:** "Hybrid approaches combine both hand-crafted algorithms and learning models." (Fig. 1 caption)

---

## 3. Working IEEE reference list (VERIFY before final)

```
[1]  C. Chen, X. Lu, A. Markham, and N. Trigoni, "IONet: Learning to Cure the Curse of Drift in
     Inertial Odometry," in Proc. AAAI Conf. Artif. Intell., 2018. arXiv:1802.02209.
[2]  H. Yan, Q. Shan, and Y. Furukawa, "RIDI: Robust IMU Double Integration," in Proc. ECCV, 2018,
     pp. 621–636. arXiv:1712.09004.
[3]  S. Herath, H. Yan, and Y. Furukawa, "RoNIN: Robust Neural Inertial Navigation in the Wild:
     Benchmark, Evaluations, and New Methods," in Proc. IEEE ICRA, 2020, pp. 3146–3152.  # ⚠ verify pages
     arXiv:1905.12853.
[4]  M. A. Esfahani, H. Wang, K. Wu, and S. Yuan, "OriNet: Robust 3-D Orientation Estimation With a
     Single Particular IMU," IEEE Robot. Autom. Lett., vol. 5, no. 2, pp. 399–406, Apr. 2020,
     doi: 10.1109/LRA.2019.2959507.
[5]  W. Liu et al., "TLIO: Tight Learned Inertial Odometry," IEEE Robot. Autom. Lett., vol. 5, no. 4,
     pp. 5653–5660, Oct. 2020. arXiv:2007.01867.  # ⚠ verify vol/pages
[6]  M. Brossard, A. Barrau, and S. Bonnabel, "AI-IMU Dead-Reckoning," IEEE Trans. Intell. Veh.,
     vol. 5, no. 4, pp. 585–595, Dec. 2020. arXiv:1904.06064.  # ⚠ verify vol/pages
[7]  M. K. Al-Sharman, Y. Zweiri, M. A. K. Jaradat, R. Al-Husari, D. Gan, and L. D. Seneviratne,
     "Deep-Learning-Based Neural Network Training for State Estimation Enhancement: Application to
     Attitude Estimation," IEEE Trans. Instrum. Meas., vol. 69, no. 1, pp. 24–34, Jan. 2020,
     doi: 10.1109/TIM.2019.2895495.
[8]  J. Wang, S. Xu, Y. Xing, J. Lu, and H. Hu, "A Pseudo-Increment Prediction Method for GNSS/INS
     Integrated Navigation Based on Transformer–LSTM During GNSS Outages," in Proc. IEEE VTC2025-Fall,
     2025, doi: 10.1109/VTC2025-Fall65116.2025.11309847.
[9]  C. Chen, B. Wang, C. X. Lu, N. Trigoni, and A. Markham, "A Survey on Deep Learning for Localization
     and Mapping: Towards the Age of Spatial Machine Intelligence," arXiv:2006.12567, 2020.  # ⚠ verify journal ver.

# Foundations (Marco Teórico)
[10] R. E. Kalman, "A New Approach to Linear Filtering and Prediction Problems," J. Basic Eng., vol. 82,
     no. 1, pp. 35–45, 1960.
[11] P. D. Groves, Principles of GNSS, Inertial, and Multisensor Integrated Navigation Systems, 2nd ed.
     Norwood, MA, USA: Artech House, 2013.
[12] I. Goodfellow, Y. Bengio, and A. Courville, Deep Learning. Cambridge, MA, USA: MIT Press, 2016.
[13] S. Hochreiter and J. Schmidhuber, "Long Short-Term Memory," Neural Comput., vol. 9, no. 8,
     pp. 1735–1780, 1997.
[14] D. P. Kingma and J. Ba, "Adam: A Method for Stochastic Optimization," in Proc. ICLR, 2015.
     arXiv:1412.6980.
[15] Y. LeCun, L. Bottou, Y. Bengio, and P. Haffner, "Gradient-Based Learning Applied to Document
     Recognition," Proc. IEEE, vol. 86, no. 11, pp. 2278–2323, 1998.
[16] N. Srivastava, G. Hinton, A. Krizhevsky, I. Sutskever, and R. Salakhutdinov, "Dropout: A Simple Way
     to Prevent Neural Networks from Overfitting," J. Mach. Learn. Res., vol. 15, pp. 1929–1958, 2014.
```
Primary tool docs (cite in Metodología): MATLAB `insfilterMARG`, `imuSensor`, `gpsSensor`; PyTorch `Conv1d`, `LSTM`.

---

## 4. Ch. 2 — Estado del Arte (proposed outline)

- **2.1 Classical GNSS/INS integrated navigation** — KF/EKF, loosely vs. tightly coupled, MARG fusion (`insfilterMARG` lineage). [10], [11]
- **2.2 Learning-based inertial odometry**
  - 2.2.1 Shallow learning: RIDI [2]
  - 2.2.2 Deep sequence models: IONet [1], RoNIN [3]
  - 2.2.3 Learned orientation: OriNet [4]
- **2.3 Hybrid learning + filtering** — TLIO [5], AI-IMU [6], Al-Sharman [7]
- **2.4 Deep learning for GNSS/INS integration & outage aiding** — Wang [8]
- **2.5 Synthesis & gap** — survey [9] trichotomy (model / learning / hybrid); then the **three design options** of §6 (increments / learned recursive filter / hybrid). Do not present hybrid as the only “modern” path. State the rejected setup: GT teacher-forced `prev_state`.
- **4.x Desarrollo — design alternatives (MUST DRAFT)** — same three options, decision, and why Q/R-free learning was or was not kept. See §6.

---

## 5. Ch. 3 — Marco Teórico (proposed skeleton)

Term-by-term glossary (program convention), each with a numbered display equation + citation where noted.

- **3.1 Navigation fundamentals**
  - 3.1.1 Reference frames: body, NED, geographic (lat/lon/alt) — [11]
  - 3.1.2 Attitude representations: Euler angles, rotation matrices, **quaternions** (algebra + quaternion distance θ_D) — eqs — [11], [4]
- **3.2 Inertial and satellite sensors**
  - 3.2.1 IMU / MARG: accelerometer, gyroscope, magnetometer; noise models (bias, noise density, random walk) — eqs — [11]; MATLAB `imuSensor`
  - 3.2.2 GNSS: position/velocity observables, accuracy — [11]; NEO-M8N datasheet
- **3.3 Classical sensor fusion**
  - 3.3.1 State-space model — eq
  - 3.3.2 Kalman filter: predict/update, Q & R, Kalman gain, Riccati — eqs — [10], [11]
  - 3.3.3 EKF / error-state / MARG fusion (`insfilterMARG`) — [11]; MATLAB docs
- **3.4 Deep learning foundations**
  - 3.4.1 Neuron, MLP, ReLU — eqs — [12]
  - 3.4.2 Convolution / `Conv1d` — eq — [15], [12]
  - 3.4.3 Recurrent networks & **LSTM** (gate equations) — eqs — [13]
  - 3.4.4 Loss functions: MSE, quaternion angular distance — eqs — [12], [4]
  - 3.4.5 Optimization: gradient descent, SGD, **Adam** — eqs — [14]
  - 3.4.6 Regularization & normalization: dropout, feature/target scaling — [16], [12]
  - 3.4.7 Training methodology: train/val/test split, batching, epochs — [12]
  - 3.4.8 Dead reckoning; teacher forcing / exposure bias; scheduled sampling; closed-loop (autoregressive) evaluation — [1], [4]; Bengio et al. 2015 if option B is chosen
- **3.5 Evaluation metrics** — RMSE, position error, **ATE / RTE**, quaternion distance θ_D — eqs — [3], [4]

---

## 6. Three method options (MUST appear in the thesis) — A is the defended method

User (Sep 2026): forget GT teacher-forced training. Document all three options.
**Decision: ship A in the main thesis** (increments + integrate + ATE/RTE vs EKF). **B = Trabajo Futuro** (or a short appendix pilot only if it actually converges). **C = literature only** (already TLIO/AI-IMU/Wang). Do not put a half-dead B in the main results table.

**Teacher forcing (rejected as the claim, keep as a diagnostic if useful):**
during training, `prev_state` = ground-truth pose at *t−1*. The net never sees its own error. Easy to fit; overstates in-flight performance. OriNet [4] uses a previous quaternion this way. Do **not** sell this as the contribution.

### Option A — Drop `prev_state`: learned increments (IONet / RoNIN style)
- **Inputs:** MARG + GPS velocity only (no pose).
- **Outputs:** Δposition / Δquaternion (or velocity), then integrate = **learned dead reckoning** (+ GPS vel as a measurement, not a pose prior).
- **Q/R:** none. Matches the “all is learned, no noise-parameter retrieval” taste.
- **Already in the literature?** Yes for **IMU-only** increments ([1], [2], [3]). **MARG + GPS-vel → 3-D increment + quaternion, vs `insfilterMARG` on the same sim**, is a thinner but cleaner gap. Not a new paradigm.

### Option B — Learned recursive filter (own `prev_state`, train closed-loop)
- **Inputs:** sensors + **the network’s last prediction** (not GT, not EKF).
- **Train closed-loop:** practice the way you fly. **Scheduled sampling** = ramp from GT `prev_state` → own `prev_state` so early epochs do not explode. Wheels come off; not a third method.
- **Q/R:** none. The net *is* the filter.
- **Already in the literature?** Closest is OriNet [4] (prev quat) but **teacher-forced**, gyro-only, no GPS. Seq2seq scheduled sampling (Bengio 2015) is standard in NLP, **rare as the main story for GNSS/INS pose**. Among the three, this is the **least occupied** niche in *our* paper set.

### Option C — Hybrid: keep `insfilterMARG`, learn the rest
- **Inputs:** sensors + **EKF pose** (from `dataset_v2_filterstate.csv`), or net learns Q/R / a residual / pseudo-GNSS.
- **Q/R:** back unless the net *replaces* them (AI-IMU).
- **Already in the literature?** **Yes — this is the developed 2020–2025 line.** TLIO [5] learned Δ + EKF; AI-IMU [6] CNN → filter noise; Al-Sharman [7] DNN refines KF attitude; Wang [8] Transformer–LSTM → pseudo-GNSS → KF. Doing “our LSTM + `insfilterMARG`” is an **implementation of a known pattern**, not a new class of method.

### Novelty ranking (for this reading list / master’s scope)

| Rank | Option | Novelty vs. our papers | Risk |
|---|---|---|---|
| **1 (most novel)** | **B — recursive net, closed-loop train** | Not what TLIO/AI-IMU/Wang do; OriNet is the cousin but not closed-loop full pose + GPS | Harder to train |
| 2 | **A — increments, no pose input** | Occupied for IMU-only; our sensors/target/baseline still a fair MSC increment | Redesign heads/metrics |
| **3 (least novel)** | **C — hybrid** | User is right: this *is* the paper farm | Easier; contribution = beat EKF / drop hand-tuned R |

**Do not confuse “most published” with “best.”** C is safest to implement and easiest to compare to [5]–[8]. B is the one that still honors “no Q/R, all learned” *and* is not already the plot of those papers. A is the same philosophy as B without a pose feedback state.

### Where this is written in the document (when drafting)

1. **Ch. 2 §2.5** — three options as the methodological fork after the survey trichotomy; cite who already did C.
2. **Ch. 3 §3.4.8** — terms: dead reckoning, teacher forcing, closed-loop training, scheduled sampling (only if B).
3. **Ch. 4** — subsection **“Design alternatives for the learned estimator”**: A/B/C table, rejected teacher forcing, **the choice and why** (including the Q/R-free argument).
4. **Ch. 1 Novedad** — A vs EKF on the same sim, Q/R-free increments; B named as the recursive extension not trained here.
5. **Ch. 6 Trabajo Futuro** — option B (closed-loop recursive net); option C explicitly deferred as already published.

**Decision: A.** `train_v2.ipynb` is the increment-odometry notebook (no pose in the inputs).
