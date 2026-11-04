# t434: poster figure "Where a SpaceX-like rack sits": C1-to-C2 band in rack kg/kW vs wing W/kg.  Reads results/t434_region.json.  ESTIMATE unless tagged.
import json, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); d = json.load(open(f"{H}/results/t434_region.json"))
plt.rcParams.update({"font.size": 13, "axes.titlesize": 17, "axes.labelsize": 15})
fig, ax = plt.subplots(figsize=(13.5, 8.2))
def curve(key): p = sorted(d["iso"][key]); return np.array([a for a, b, n in p]), np.array([b for a, b, n in p])
COL = {"Jun8": "#1f7a6d", "Aug4": "#d1603d"}
for b in ("Jun8", "Aug4"):
    x1, y1 = curve(f"{b}|C1"); x2, y2 = curve(f"{b}|C2")
    xs = np.linspace(max(x1.min(), x2.min()), 523, 200); a1 = np.interp(xs, x1, y1); a2 = np.interp(xs, x2, y2)
    ax.fill_between(xs, a1, a2, color=COL[b], alpha=0.22 if b == "Jun8" else 0.12, lw=0)
    ax.plot(x1, y1, "-", color=COL[b], lw=2.4, label=f"{b[:3]} ({'150 kW, 70' if b=='Jun8' else '250 kW, 75'} kW/t): lower edge = C1 margins")
    ax.plot(x2, y2, "--", color=COL[b], lw=2.4, label=f"{b[:3]}: upper edge = C2 margins")
    for nm, m, sz in (("C1", "s", 15), ("MID", "D", 12), ("C2", "^", 16)):
        p = d["points"][f"{b}|{nm}"]; ax.plot(p["wing"], p["k_rack"], m, ms=sz, color=COL[b], mec="k", mew=1.6, zorder=6)
        if b == "Jun8": ax.annotate(f"{nm}\n{p['k_rack']:.2f} kg/kW\n{p['wing']:.0f} W/kg", (p["wing"], p["k_rack"]), xytext=({"C1": (-30, -80), "MID": (44, -78), "C2": (-8, 24)}[nm]), textcoords="offset points", fontsize=11.5, ha="center", fontweight="bold")
# references
ax.axhline(7.83, color="0.35", ls=":", lw=2); ax.text(588, 7.93, "HPE GB200 NVL72 rack, 7.8 kg/kW (STATEMENT, public spec)", ha="right", fontsize=12, color="0.25")
ax.axvspan(71, 124, color="#7b6fd0", alpha=0.22, lw=0); ax.text(97.5, 6.55, "flown ROSA wings\n71–124 W/kg\n(Redwire flysheet,\nSTATEMENT)", ha="center", va="center", fontsize=11.5, color="#3b2f93", fontweight="bold")
ax.plot(194, 600 / 188.0, "*", ms=26, color="#f2c230", mec="k", mew=1.4, zorder=7)
ax.annotate("our adopted 254-panel stack\nrack 3.2 kg/kW, wing 194 W/kg\n(7.0 t, 188 kW; repo O5 lines)", (194, 600 / 188.0), xytext=(58, 4.75), textcoords="data", fontsize=11.5, arrowprops=dict(arrowstyle="->", lw=1.4), va="center", ha="left")
ax.axvline(250, color="r", alpha=0.0)
ax.set_xlim(40, 590); ax.set_ylim(0, 8.6)
ax.set_xlabel("array wing specific power, W per kg of wing (BOL, 884 W/kg cell; blanket mass varied)")
ax.set_ylabel("compute-rack mass, kg per kW of IT power")
ax.set_title("SpaceX-like region: every (rack, wing) pair in the band reproduces SpaceX's 70/75 kW/t\nand 46/30 satellites per Starship inside the FCC limits (4 t, 200 m² radiator, 1,500 m² array)", loc="left")
ax.legend(loc="upper left", fontsize=11, framealpha=0.95, bbox_to_anchor=(0.0, 0.995))
ax.grid(alpha=0.25)
fig.text(0.01, 0.005, "ESTIMATE (t423g calibration; margins = C1 margin-forward vs C2 compute-limited, MID = mean of the two). Squares = C1, diamonds = MID, triangles = C2.  \nBaseline wing value is IT kW per array kg (≈6–7% below the BOL wing basis of the band; INFERENCE).\n"
         "Band width = how much margin SpaceX could be carrying: C1 spends mass on margins (growth 20.5%, 5% spare compute, 2 spare pumps), C2 spends it on compute.", fontsize=9.5, va="bottom", linespacing=1.3)
plt.tight_layout(rect=(0, 0.07, 1, 1)); plt.savefig(f"{H}/figures/fig_t434_spacex_region.png", dpi=200)
