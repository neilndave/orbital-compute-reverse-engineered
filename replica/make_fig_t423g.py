import json, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
H = os.path.dirname(os.path.abspath(__file__)); d = json.load(open(f"{H}/results/t423g.json"))
G = [("Compute rack (+spares)", ["rack", "shielding_radiation"], "#264653"), ("Array (+deploy in structure)", ["array"], "#e9c46a"), ("Radiator + coolant loop", ["radiator", "coolant_loop"], "#2a9d8f"),
     ("Power electronics + harness", ["power_electronics", "harness"], "#f4a261"), ("Structure + deploy", ["structure_mech"], "#8d99ae"), ("Propulsion/ADCS + avionics", ["propulsion_adcs", "avionics_links"], "#6d597a"),
     ("MMOD bumper + adapter", ["mmod_bumper", "adapter"], "#b56576"), ("Growth margin", ["margin"], "#e76f51")]
fig, ax = plt.subplots(1, 2, figsize=(16, 6.6), gridspec_kw=dict(width_ratios=[1.25, 1]))
x = 0; ticks = []; labs = []
for b, bud, cap in (("Jun8", 2143, 2130), ("Aug4", 3333, 3267)):
    for nm, short in (("C1_margin_forward", "C1 margin-fwd"), ("C2_compute_limited", "C2 compute-ltd")):
        L = d[b][nm]["lines"]; bot = 0
        for g, keys, c in G:
            v = sum(L.get(k, 0) for k in keys); ax[0].bar(x, v, bottom=bot, color=c, label=g if (b == "Jun8" and nm.startswith("C1")) else None, edgecolor="w", lw=.4)
            if v > 120: ax[0].text(x, bot + v / 2, f"{v:.0f}", ha="center", va="center", fontsize=7, color="w")
            bot += v
        pr = d[b][nm]["prop"]; ax[0].text(x, bot + 60, f"{bot:.0f} kg\n{d[b][nm]['kwt']:.1f} kW/t, {d[b][nm]['N98']} sats\nrack {d[b][nm]['k_rack']:.2f} kg/kW\nwing {d[b][nm]['wing']:.0f} W/kg", ha="center", fontsize=7.5)
        ticks.append(x); labs.append(f"{b[:3]}\n{short}"); x += 1
    ax[0].hlines(bud, x - 2.45, x - .55, color="k", ls="--"); ax[0].text(x - 1.5, bud + 1000, f"SpaceX-implied budget {bud:,} kg (dashed)", ha="center", fontsize=8, color="k"); x += .8
ax[0].set_xticks(ticks); ax[0].set_xticklabels(labs, fontsize=8); ax[0].set_ylabel("satellite mass, kg (all-in: incl. bumper, adapter, growth)"); ax[0].set_ylim(0, 5200)
ax[0].legend(fontsize=7, loc="upper left", ncol=2); ax[0].set_title("A. Calibrated 'SpaceX-like' designs vs SpaceX-implied mass budget (ESTIMATE)", fontsize=10)
import sys; sys.path.insert(0, H)
def wing(n): return 319.7 / (n + 319.7 / 884.0)
for b, c in (("Jun8", "#2a9d8f"), ("Aug4", "#e76f51")):
    iso = d[b]["iso_rack_vs_n"]; ns_ = [float(k) for k in iso]; ax[1].plot([wing(n) for n in ns_], [iso[str(k)] if str(k) in iso else iso[k] for k in iso], "o-", color=c, label=f"{b}: all-in {'70' if b=='Jun8' else '75'} kW/t (C1 margins)")
for yv, lab in ((7.83, "HPE GB200 rack 7.8"), (3.8, "t423d stretch rack 3.8"), (1.39, "first-principles rack 1.39")):
    ax[1].axhline(yv, color="gray", ls=":"); ax[1].text(525, yv + .1, lab, fontsize=7, ha="right")
for b, nm, m in (("Jun8", "C1_margin_forward", "s"), ("Jun8", "C2_compute_limited", "^")): ax[1].plot(d[b][nm]["wing"], d[b][nm]["k_rack"], m, ms=10, color="k", mfc="none", label=("C1 point (square)" if m=="s" else "C2 point (triangle, 10% growth, other margins lower)"))
ax[1].axvline(200, color="r", alpha=.3); ax[1].set_xlabel("array wing W/kg (884 W/kg cell, blanket n varied)"); ax[1].set_ylabel("rack kg/kW needed"); ax[1].legend(fontsize=8); ax[1].set_title("B. Rack kg/kW vs wing W/kg that reproduce 70/75 (all-in)", fontsize=10); ax[1].set_ylim(0, 8.5)
plt.tight_layout(); plt.savefig(f"{H}/figures/fig_t423g_calibrated.png", dpi=130)
