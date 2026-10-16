# -*- coding: utf-8 -*-
from docx import Document
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from docx.enum.text import WD_ALIGN_PARAGRAPH

PATH = r"C:\Users\noxuz\OneDrive\Documentos\000000LETESIS\sensor_fusion_thesis\tesis_docx\TOG_SENSOR_FUSION_WIP.docx"


def set_text(p, text):
    if p.runs:
        p.runs[0].text = text
        for r in p.runs[1:]:
            r.text = ""
    else:
        p.add_run(text)


def insert_after(paragraph, text=None, style="Normal", bold_lead=None):
    new_p = OxmlElement("w:p")
    paragraph._element.addnext(new_p)
    new_para = Paragraph(new_p, paragraph._parent)
    new_para.style = style
    if bold_lead:
        r = new_para.add_run(bold_lead)
        r.bold = True
        if text:
            new_para.add_run(text)
    elif text:
        new_para.add_run(text)
    return new_para


def eq(paragraph, text, n):
    p = insert_after(paragraph, f"{text}    ({n})", "Normal")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return p


def add_blocks(after, items):
    cur = after
    for item in items:
        kind = item[0]
        if kind == "h2":
            cur = insert_after(cur, item[1], "Heading 2")
        elif kind == "p":
            cur = insert_after(cur, item[1], "Normal")
        elif kind == "term":
            cur = insert_after(cur, item[2], "Normal", bold_lead=item[1])
        elif kind == "eq":
            cur = eq(cur, item[1], item[2])
    return cur


doc = Document(PATH)

res = None
h_frames = h_sens = h_kf = h_dl = None
junk = []
seen_h1 = False
for p in doc.paragraphs:
    if p.style.name.startswith("Heading 1") and "MARCO TE" in p.text.upper():
        seen_h1 = True
        continue
    if not seen_h1:
        continue
    if p.style.name.startswith("Heading 1"):
        break
    if p.text.startswith("Resumen:") and res is None:
        res = p
    elif p.style.name == "Heading 2":
        t = p.text.strip()
        if t == "Concepto básico 1" or t == "Concepto basico 1":
            h_frames = p
        elif "Esquema" in t:
            h_sens = p
        elif "subtema" in t.lower() and "Subsub" not in t:
            h_kf = p
        elif "Subsubtema" in t:
            h_dl = p
    elif p.text.strip().startswith("[") or "DEBIDAMENTE" in p.text:
        junk.append(p)

if not all([res, h_frames, h_sens, h_kf, h_dl]):
    raise SystemExit(f"missing headings res={res} f={h_frames} s={h_sens} k={h_kf} d={h_dl}")

set_text(
    res,
    "Resumen: This chapter is a term-by-term account of the quantities, sensors, filters, networks and metrics that the rest of the document uses, so that Chapter 4 can name a residual velocity or a quaternion distance without stopping to define them; the tone is that of a glossary, not of a second state of the art, and each term is tied to the citation that this work actually leans on.",
)
set_text(h_frames, "Reference frames and attitude")
set_text(h_sens, "Inertial and satellite sensors")
set_text(h_kf, "Classical sensor fusion")
set_text(h_dl, "Deep learning models used in this work")
for p in junk:
    set_text(p, "")

add_blocks(
    h_frames,
    [
        (
            "p",
            "Navigation is not done in a single set of axes, and mixing them is how a filter, or a network, writes a number that looks precise and points the wrong way; Groves is the reference used here for the geographic, navigation and body frames [11].",
        ),
        (
            "term",
            "Geographic frame. ",
            "A position on the Earth is written as latitude, longitude and altitude, often abbreviated LLA; GPS receivers report this frame, and insfilterMARG consumes it in the update. The defended network never sees LLA, only a velocity already expressed in the navigation frame, because a held latitude in the feature vector would turn absolute trajectory error into a contest the filter had already been given the answer to.",
        ),
        (
            "term",
            "NED. ",
            "The North–East–Down navigation frame is the working frame of this thesis: the first axis points north, the second east, and the third down, so that a positive increment in the third coordinate is a descent. Ground-truth position, GPS velocity and the EKF position in filterstate.csv are all stored in NED, following the MathWorks MARG example [18].",
        ),
        (
            "term",
            "Body frame. ",
            "The accelerometer, gyroscope and magnetometer measure in the vehicle body, i.e. in axes fixed to the IMU. A specific force has to be rotated by the current attitude before it can be integrated as a change of NED velocity; that rotation is the reason attitude and position cannot be learned as two unrelated regressions if one later wants a consistent path [11].",
        ),
        (
            "term",
            "Euler angles. ",
            "Roll, pitch and yaw are an intuitive three-number attitude, and they are also a poor regression target near pitch ±90°, where the representation is singular. This work does not train on Euler angles.",
        ),
        (
            "term",
            "Quaternion. ",
            "A unit quaternion q = (q_w, q_x, q_y, q_z) is a four-vector on the sphere that represents a rotation without that singularity; the product of two quaternions is another rotation, and the inverse of a unit quaternion is its conjugate [11], [4]. The ground-truth and EKF orientations in the dataset are stored in wxyz order. Composition of a previous attitude q with a small increment Δq is written",
        ),
        ("eq", "q_k = q_{k−1} ⊗ Δq_k", 1),
        (
            "p",
            "and the increment itself is obtained, in this work, from a three-dimensional axis-angle vector v = θ u, with θ the rotation angle and u a unit axis, by the map",
        ),
        ("eq", "Δq = (cos(θ/2), u sin(θ/2))", 2),
        (
            "term",
            "Quaternion distance. ",
            "Because q and −q are the same rotation, a useful scalar error is the geodesic angle used by OriNet and kept in Chapter 5 [4],",
        ),
        ("eq", "θ_D = 2 arccos(|q̂ · q|)", 3),
        (
            "p",
            "reported in degrees as a mean over the TEST sequence. A 180° value that never moves, as in the first increment experiment of this project, is a sign that the network has collapsed to an antipodal quaternion, not that the vehicle flipped.",
        ),
    ],
)

add_blocks(
    h_sens,
    [
        (
            "term",
            "IMU. ",
            "An inertial measurement unit, in the six-axis sense, is an accelerometer plus a gyroscope; the accelerometer reports specific force, i.e. acceleration minus gravity in the body frame, and the gyroscope reports angular rate. Integrating those signals is dead reckoning, and it walks off in seconds on a consumer IMU because of bias, noise density and scale-factor error [11].",
        ),
        (
            "term",
            "MARG. ",
            "A magnetic, angular-rate and gravity unit adds a magnetometer to the IMU, which gives an absolute heading observation that a gyro-only integrator does not have. The simulated sensor in this work is MATLAB’s imuSensor in the accel-gyro-mag configuration, with the noise densities and constant biases of the official example [18]; the twelve-channel learning window is accelerometer (3), gyroscope (3), magnetometer (3) and GPS velocity (3).",
        ),
        (
            "term",
            "Sensor noise, bias and density. ",
            "The example IMU is not a white-noise toy: the accelerometer and gyroscope carry a constant bias and a noise density, the magnetometer carries a large constant bias, and those parameters are also used to seed the EKF state. I consider that this is why a Q/R-free network is interesting on this log, and also why it is not a claim about an unseen physical IMU: the noise the net sees is the noise the example already wrote down.",
        ),
        (
            "term",
            "GNSS and GPS velocity. ",
            "A global navigation satellite system receiver, here a simulated gpsSensor standing in for a consumer GPS, produces a geodetic position and a velocity at 1 Hz, with a horizontal and vertical position accuracy of 1.6 m and a velocity accuracy of 0.1 m/s in the generator script. Velocity is zero-order held into the 160 Hz table so that the network always sees a 12-D sample; position LLA is withheld from that table and reserved for the EKF update. Open-loop integration of the held GPS velocity is the dumb baseline of Chapter 5, i.e. what the residual head must beat or tie before anyone talks about beating the filter.",
        ),
        (
            "term",
            "Zero-order hold (ZOH). ",
            "A 1 Hz measurement that is repeated until the next fix, so that a 160 Hz learner has a value on every row. ZOH of magnetometer and GPS velocity is used; ZOH of LLA is not, for the reason already stated.",
        ),
    ],
)

add_blocks(
    h_kf,
    [
        (
            "p",
            "The classical estimator in this document is an extended Kalman filter. Kalman stated the linear recursion in 1960 [10]; Groves is the navigation reading [11]; insfilterMARG is the concrete MARG-plus-GPS implementation that both generates the comparison pose and, in the hybrid pilot, supplies the leftover that a network may try to subtract [18].",
        ),
        (
            "term",
            "State-space model. ",
            "A discrete process and a measurement are written",
        ),
        ("eq", "x_k = f(x_{k−1}, u_k) + w_k,    z_k = h(x_k) + v_k", 4),
        (
            "p",
            "where w_k is process noise with covariance Q and v_k is measurement noise with covariance R. The designer’s labor, when there is no network, is those two matrices.",
        ),
        (
            "term",
            "Kalman filter. ",
            "In the linear case the predict step propagates the mean and the covariance, and the update step computes a gain K that blends the prediction with the measurement [10],",
        ),
        ("eq", "x̂_{k|k−1} = F x̂_{k−1|k−1},    P_{k|k−1} = F P_{k−1|k−1} Fᵀ + Q", 5),
        ("eq", "K_k = P_{k|k−1} Hᵀ (H P_{k|k−1} Hᵀ + R)⁻¹", 6),
        ("eq", "x̂_{k|k} = x̂_{k|k−1} + K_k (z_k − H x̂_{k|k−1})", 7),
        (
            "term",
            "Q and R. ",
            "Q says how much the prediction is trusted; R says how much the sensor is trusted. Swapping their names in a write-up, or putting a magnetometer variance into R as if it were already an angle, is a known way to get a filter that runs and a text that does not match the code. This thesis does not retune Q or R; the example values travel with the simulated IMU.",
        ),
        (
            "term",
            "EKF and insfilterMARG. ",
            "An extended Kalman filter linearizes f and h about the current estimate. insfilterMARG is an error-state EKF for a 22-dimensional MARG-plus-GPS state, including attitude, NED position and velocity, inertial biases and the geomagnetic vector [18]. On the TEST slice used in Chapter 5 it reaches 0.78 m ATE, 0.20 m RTE and 7.46° mean quaternion error. Those numbers already include GPS LLA in the update.",
        ),
        (
            "term",
            "Loosely versus tightly coupled fusion. ",
            "A loosely coupled GNSS/INS filter consumes the receiver’s position and velocity solutions; a tightly coupled filter consumes raw or processed satellite observables [11]. The baseline of this work is loosely coupled in that sense: fusegps is called with LLA and velocity. The learned estimator is looser still: it sees only the velocity channel.",
        ),
    ],
)

add_blocks(
    h_dl,
    [
        (
            "p",
            "The defended estimator is a temporal convolutional network with two linear heads. The terms below are only those that appear in that pipeline or in the alternatives of Chapter 2; Goodfellow et al. are the textbook backdrop [12].",
        ),
        (
            "term",
            "MLP. ",
            "A multilayer perceptron is a stack of affine maps and pointwise nonlinearities; here each head is a two-layer MLP, 128–64–3, on top of a pooled TCN body [12].",
        ),
        (
            "term",
            "ReLU. ",
            "The rectified linear unit, max(0, x), is the nonlinearity inside the TCN blocks and the heads.",
        ),
        (
            "term",
            "Conv1d. ",
            "A one-dimensional convolution slides a kernel along time, across channels; it is the natural layer for a window of IMU samples, and it is the stem of both the increment model and the older Conv1d–LSTM course network [15], [12]. A kernel of length 5 and 64 channels is the stem used in A8q.",
        ),
        (
            "term",
            "TCN. ",
            "A temporal convolutional network is a stack of dilated causal, or here residual, 1-D convolutions whose receptive field grows exponentially with depth. RoNIN already used a TCN as one of three inertial backbones [3]. The A8q body has four residual blocks with dilations 1, 2, 4 and 8; the representation fed to the heads is the concatenation of a global average over time and the last time step.",
        ),
        (
            "term",
            "Residual velocity head. ",
            "The position-related output is not a NED position and not a raw velocity, it is a correction δv such that",
        ),
        ("eq", "v̂ = v_GPS + δv", 8),
        (
            "p",
            "so that a network that outputs zero still reproduces GPS-velocity dead reckoning. The 0.1 s orientation head outputs the axis-angle of (2), not a unit quaternion, because a 160 Hz Δq is almost the identity and was observed to collapse to 180° in the first increment run.",
        ),
        (
            "term",
            "LSTM. ",
            "A long short-term memory cell is a recurrent unit with input, forget and output gates [13]. It is the backbone of IONet and OriNet [1], [4], and of the course-project network that this thesis retired; it is not the frozen A8q body. It is defined here because Chapter 2 cannot be read without it.",
        ),
        (
            "term",
            "Dual head. ",
            "Two small MLPs on a shared trunk, one for δv and one for the axis-angle. A single six-dimensional head was tried; ATE pressure spent the orientation. I consider that split the one architectural decision that actually changed the table, more than the width of the TCN.",
        ),
    ],
)

# remaining sections after the last H2 body — attach to h_dl's last inserted content
# add_blocks already appended after h_dl, so we need a cursor at end of ch3.
# Insert remaining H2s after h_dl as well (they'll appear right after the heading,
# before the DL body, if we call add_blocks(h_dl) again... first call already used h_dl.
# The first add_blocks(h_dl, ...) inserted AFTER h_dl, so new H2s must be inserted
# after the last DL paragraph. Easiest: one more add_blocks from a marker.
# We'll insert the extra sections by finding the last DL paragraph we added —
# "I consider that split..." — then add_blocks from there.

tail = None
for p in doc.paragraphs:
    if "the one architectural decision that actually changed the table" in p.text:
        tail = p
if tail is None:
    raise SystemExit("DL tail not found")

add_blocks(
    tail,
    [
        ("h2", "Training, losses and optimization"),
        (
            "term",
            "Train / validation / test split. ",
            "Windows are extracted every 0.1 s from a one-second context. The log is cut chronologically, about 70 / 15 / 15 with a one-second gap, so that TRAIN, VAL and TEST do not share a hop; TEST is 121–141 s. This is a same-path holdout, not a claim that the net generalizes to another flight [12].",
        ),
        (
            "term",
            "Normalization. ",
            "Feature-wise and target-wise means and standard deviations are computed on TRAIN only and applied to VAL and TEST; without that scaling the position term dominates a joint loss and the orientation is under-learned.",
        ),
        (
            "term",
            "MSE. ",
            "Mean squared error on the standardized residual velocity and on the axis-angle is the training loss of A8q [12]. A geodesic loss on (3) was left as a possible ablation and was not used for the frozen row.",
        ),
        (
            "term",
            "Adam. ",
            "The optimizer is Adam at 10⁻³ [14], with minibatches of 256 and eighty epochs. Early stopping, in practice, is a validation checkpoint, and the checkpoint metric decides which compass one keeps.",
        ),
        (
            "term",
            "Dropout. ",
            "Randomly dropping units during training as a regularizer [16]. It is cited because Al-Sharman uses it and because the course network sketched it; A8q does not rely on it as the main control of overfitting, the chronological split and the dual head do more of that work.",
        ),
        ("h2", "Dead reckoning, teacher forcing and scheduled sampling"),
        (
            "term",
            "Dead reckoning. ",
            "Estimating the present pose from the last pose and a measured or predicted increment, with no external fix. Inertial integration is dead reckoning; IONet’s sentence about breaking continuous integration is the learning version of the same idea [1]. The defended estimator is learned dead reckoning plus a GPS-velocity measurement, not a pose prior.",
        ),
        (
            "term",
            "Teacher forcing. ",
            "During training, the previous state fed to a sequential model is the ground truth, not the model’s own last output. The loss becomes easy and the number overstates closed-loop drift; OriNet’s previous quaternion is in that family if that quaternion is the true one [4]. Teacher forcing is rejected as the claim of this thesis and kept only as a diagnostic column in the recursive pilot.",
        ),
        (
            "term",
            "Exposure bias. ",
            "The mismatch between a teacher-forced train-time input and a self-generated test-time input. B0 made that mismatch theatrical: a six-centimeter teacher-forced ATE and a 2.57 m closed-loop ATE, because the net had been looking up a NED position.",
        ),
        (
            "term",
            "Scheduled sampling. ",
            "Bengio et al.’s on-ramp: the probability of feeding ground truth is annealed toward zero so that the net is gradually asked to live with its own pose [17]. B1 uses a linear anneal over the first 40% of epochs and then stays at zero.",
        ),
        (
            "term",
            "Closed-loop evaluation. ",
            "The first TEST pose is taken from ground truth; after that the estimator consumes only sensors and its own last state. A is closed-loop in the integrator, not in the network, because A has no previous-state input. B is closed-loop in both.",
        ),
        ("h2", "Evaluation metrics"),
        (
            "term",
            "ATE. ",
            "Absolute trajectory error, taken from RoNIN’s evaluation culture [3]: the RMSE of the integrated NED position against ground truth on the 1 s TEST hops,",
        ),
        ("eq", "ATE = √( (1/N) Σ_i ||p̂_i − p_i||² )", 9),
        (
            "p",
            "A constant 0.09 m/s velocity bias becomes about a meter over a 20 s holdout, so ATE punishes drift. The EKF’s ATE is not a fair fight with A, because the filter sees LLA.",
        ),
        (
            "term",
            "RTE. ",
            "Relative trajectory error over a short window, here one second: the mean magnitude of the difference between estimated and true displacements on that hop [3]. A path that is translated but the right shape can have a bad ATE and a decent RTE. A8q’s claim against GPS-velocity integration is an RTE claim, 0.31 m versus 0.45 m.",
        ),
        (
            "term",
            "RMSE. ",
            "Root-mean-square error, the scalar cousin of ATE when the quantity is not a trajectory, e.g. a per-axis velocity or a one-step increment.",
        ),
        (
            "p",
            "Those twelve numbered relations, and the terms around them, are the vocabulary of Chapters 4 and 5; what is not defined here, a Transformer, an invariant EKF, a stochastic-cloning filter, is named in Chapter 2 and left there.",
        ),
    ],
)

alt = PATH.replace("TOG_SENSOR_FUSION_WIP.docx", "TOG_SENSOR_FUSION_WIP_ch3.docx")
try:
    doc.save(PATH)
    print("saved Ch.3 into WIP", "paragraphs", len(doc.paragraphs))
except PermissionError:
    doc.save(alt)
    print("WIP locked; saved sidecar", alt)
