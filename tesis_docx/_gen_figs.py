# -*- coding: utf-8 -*-
"""Generate pipeline block diagram + chronological-split timeline PNGs."""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
sys.stdout.reconfigure(encoding="utf-8")

OUT = "thesis_figs"
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
                     "font.size": 10})

BLUE = "#d9e3f2"; GREEN = "#dcecd9"; GRAY = "#ececec"; ORANGE = "#f3e2cf"
EDGE = "#4a4a4a"

def box(ax, x, y, w, h, text, fc=BLUE, fs=10, bold=False):
    p = FancyBboxPatch((x - w/2, y - h/2), w, h,
                       boxstyle="round,pad=0.02,rounding_size=0.06",
                       linewidth=1.1, edgecolor=EDGE, facecolor=fc)
    ax.add_patch(p)
    ax.text(x, y, text, ha="center", va="center", fontsize=fs,
            fontweight=("bold" if bold else "normal"), zorder=5)

def arrow(ax, x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                 mutation_scale=13, linewidth=1.1, color=EDGE, shrinkA=1, shrinkB=1))

# ============================================================ pipeline diagram
fig, ax = plt.subplots(figsize=(7.4, 8.4))
ax.set_xlim(0, 10); ax.set_ylim(0, 16); ax.axis("off")
cx = 5.0
box(ax, cx, 15.2, 8.6, 1.1,
    "Input window  (1 s @ 160 Hz, 12 channels)\n"
    "accelerometer (3) · gyroscope (3) · magnetometer (3) · GPS velocity (3)", fc=GRAY, fs=9.5)
arrow(ax, cx, 14.65, cx, 14.15)
box(ax, cx, 13.6, 6.2, 0.95, "Conv1d stem   12 \u2192 64,  kernel 5", fc=BLUE)
arrow(ax, cx, 13.12, cx, 12.62)
box(ax, cx, 11.95, 7.4, 1.3,
    "4 \u00d7 dilated residual TCN blocks\n"
    "kernel 5,  dilations 1 / 2 / 4 / 8,  64 channels", fc=BLUE)
arrow(ax, cx, 11.3, cx, 10.8)
box(ax, cx, 10.2, 7.0, 1.0,
    "Temporal pooling\nconcat( mean over time , last step ) = 128", fc=BLUE)
# branch to two heads
arrow(ax, cx, 9.7, 2.9, 9.2)
arrow(ax, cx, 9.7, 7.1, 9.2)
box(ax, 2.9, 8.6, 3.5, 1.15, "Head  \u03b4v\nMLP 128\u201364\u20133", fc=GREEN, fs=9.5)
box(ax, 7.1, 8.6, 3.5, 1.15, "Head  axis\u2013angle \u0394\u03b8\nMLP 128\u201364\u20133", fc=GREEN, fs=9.5)
arrow(ax, 2.9, 8.0, 2.9, 7.4)
arrow(ax, 7.1, 8.0, 7.1, 7.4)
box(ax, 2.9, 6.8, 3.9, 1.15,
    "Residual velocity\n$\\hat{v} = v_{GPS} + \\delta v$", fc=ORANGE, fs=9.5)
box(ax, 7.1, 6.8, 3.9, 1.15,
    "Orientation increment\n$\\Delta q = \\exp(\\Delta\\theta)$", fc=ORANGE, fs=9.5)
arrow(ax, 2.9, 6.2, 2.9, 5.6)
arrow(ax, 7.1, 6.2, 7.1, 5.6)
box(ax, 2.9, 5.0, 3.9, 1.15,
    "Integrate position\n$p \\leftarrow p + \\hat{v}\\,\\cdot 1.0$ s", fc=BLUE, fs=9.5)
box(ax, 7.1, 5.0, 3.9, 1.15,
    "Integrate attitude\n$q \\leftarrow q \\otimes \\Delta q$  (0.1 s)", fc=BLUE, fs=9.5)
arrow(ax, 2.9, 4.4, 4.4, 3.85)
arrow(ax, 7.1, 4.4, 5.6, 3.85)
box(ax, cx, 3.2, 5.2, 1.0, "Estimated pose  ( p , q )", fc=GRAY, bold=True)
arrow(ax, cx, 2.7, cx, 2.2)
box(ax, cx, 1.5, 8.4, 1.15,
    "Evaluation vs. insfilterMARG (EKF)  and  GPS-velocity integration\n"
    "ATE · RTE · mean quaternion distance", fc="#f2d9d9", fs=9.2)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "pipeline.png"), dpi=200, bbox_inches="tight")
plt.close(fig)
print("wrote pipeline.png")

# ============================================================ split timeline
fig, ax = plt.subplots(figsize=(8.6, 2.5))
segs = [
    (0,   1,   "Warmup\n(dropped)", GRAY),
    (1,   97,  "TRAIN\n961 windows", BLUE),
    (97,  99,  "gap", "#ffffff"),
    (99,  120, "VAL\n210", GREEN),
    (120, 121, "gap", "#ffffff"),
    (121, 141, "TEST\n210 (21 @ 1 s)", ORANGE),
]
for x0, x1, lab, c in segs:
    ax.add_patch(plt.Rectangle((x0, 0), x1 - x0, 1, facecolor=c,
                 edgecolor=EDGE, linewidth=1.0))
    if lab != "gap":
        ax.text((x0 + x1) / 2, 0.5, lab, ha="center", va="center", fontsize=9)
    else:
        ax.text((x0 + x1) / 2, 1.18, "1 s gap", ha="center", va="bottom", fontsize=7.5, color="#666")
ax.set_xlim(-2, 143); ax.set_ylim(-0.5, 1.7)
ax.set_yticks([])
ax.set_xticks([0, 20, 40, 60, 80, 100, 120, 140])
ax.set_xlabel("time after warmup (s)")
for s in ["top", "right", "left"]:
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "split_timeline.png"), dpi=200, bbox_inches="tight")
plt.close(fig)
print("wrote split_timeline.png")
