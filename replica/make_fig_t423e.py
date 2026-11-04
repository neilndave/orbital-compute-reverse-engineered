import json, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
H = os.path.dirname(os.path.abspath(__file__)); fp = json.load(open(f"{H}/results/t423e_fp.json"))
fig, ax = plt.subplots(1, 3, figsize=(19, 6.4), gridspec_kw=dict(width_ratios=[1.15, 1, 1]))
# A: technology W/kg (log), cell vs wing, demonstrated/claimed/lab
T = [("ROSA/iROSA wing (flown)", 100, 124, "wing", "flown"), ("UltraFlex wing (flown/qual)", 150, 150, "wing", "flown"), ("MegaFlex wing (claim)", 155, 200, "wing", "claim"),
     ("Solestial SHJ 60um (claim, mfr)", 500, 600, "module", "claim"), ("CIGS/PI 15% + light support (paper est.)", 182, 500, "module", "est"),
     ("IMM-alpha 4J bare cell (datasheet calc)", 884, 884, "cell", "data"), ("MicroLink ELO 20cm2 cell (mfr)", 2379, 3000, "cell", "claim"),
     ("Perovskite flexible 23-48 W/g (lab, AM1.5)", 23000, 47800, "cell", "lab")]
col = {"flown": "#2a9d8f", "data": "#264653", "claim": "#e9c46a", "est": "#f4a261", "lab": "#e76f51"}
for i, (n, lo, hi, lv, k) in enumerate(T):
    ax[0].barh(i, hi - lo + 0.04 * lo, left=lo, color=col[k], edgecolor="k", height=.6); ax[0].text(hi * 1.12, i, f"{lo:,.0f}" + (f"-{hi:,.0f}" if hi != lo else "") + f" [{lv}]", va="center", fontsize=8)
ax[0].set_yticks(range(len(T))); ax[0].set_yticklabels([t[0] for t in T], fontsize=8); ax[0].set_xscale("log"); ax[0].set_xlim(60, 400000); ax[0].invert_yaxis()
ax[0].axvspan(200, 212, color="red", alpha=.25); ax[0].text(206, -0.8, "wing threshold 200/212 (stretch core)", fontsize=7, color="red", ha="center")
ax[0].axvline(250, color="k", ls="--", lw=.8); ax[0].text(255, 7.6, "250 floor", fontsize=7)
ax[0].set_xlabel("specific power, W/kg (BOL, AM0 unless noted; levels differ - see table)"); ax[0].set_title("A. Array specific power by technology (level labelled)", fontsize=10)
# B: ladder
for j, b in enumerate(("Jun8", "Aug4")):
    L = fp[b]["ladder"]; x0 = j * 7
    names = ["t423d\nstretch", "+array\nFP", "+rack\nFP", "+PCDU\nFP", "+struct\nFP", "+harness\nFP"]
    for i, s in enumerate(L):
        ax[1].bar(x0 + i, s["kwt"], color="#2a9d8f", width=.38, align="center"); ax[1].bar(x0 + i + .4, s["kwt_ab"], color="#e76f51", width=.38, align="center")
    ax[1].hlines({"Jun8": 70, "Aug4": 75}[b], x0 - .5, x0 + 5.9, color="k", ls="--"); ax[1].text(x0 + 2.5, {"Jun8": 70, "Aug4": 75}[b] + 3, f"SpaceX {'70' if b=='Jun8' else '75'} kW/t ({b})", fontsize=8, ha="center")
    ax[1].set_xticks(list(range(0, 6)) + list(range(7, 13))); ax[1].set_xticklabels(names + names, fontsize=6)
ax[1].bar([], [], color="#2a9d8f", label="core"); ax[1].bar([], [], color="#e76f51", label="+add-backs"); ax[1].legend(fontsize=8); ax[1].set_ylabel("kW/t (peak IT, wet)"); ax[1].set_title("B. First-principles ladder (Jun 8 | Aug 4)", fontsize=10)
# C: satellites per Starship
labs = []; v = []; 
for b, tg in (("Jun8", 98000 / (150 / 70 * 1000)), ("Aug4", 98000 / (250 / 75 * 1000))):
    for k, nm, c in (("ref_credible", "flown-class", "#8d99ae"), ("ref_stretch300", "t423d stretch", "#e9c46a"), ("FP_base", "FP base", "#2a9d8f"), ("FP_bold", "FP bold", "#264653")):
        r = fp[b][k]; ax[2].bar(len(labs), r["N98"], color=c); ax[2].bar(len(labs) + .0, r["N98_ab"], color="none", edgecolor="k", hatch="//"); labs.append(f"{b[:3]}\n{nm}"); ax[2].text(len(labs) - 1, r["N98"] + 1, f"{r['N98']}/{r['N98_ab']}", ha="center", fontsize=8)
    ax[2].hlines(tg, len(labs) - 4.5, len(labs) - .5, color="k", ls="--"); ax[2].text(len(labs) - 2.5, tg + 6, f"SpaceX-implied {tg:.0f}", fontsize=8, ha="center")
ax[2].set_xticks(range(len(labs))); ax[2].set_xticklabels(labs, fontsize=7); ax[2].set_ylabel("satellites per Starship (98 t); label = core/add-back (hatched)"); ax[2].set_title("C. Satellites per Starship", fontsize=10)
fig.suptitle("t423e - how high can array W/kg go, and what a first-principles stack gives vs SpaceX 70/75 kW/t (600-725 km LTAN 6; ESTIMATE labels in INTERIM_t423e.md)", fontsize=11)
plt.tight_layout(); plt.savefig(f"{H}/figures/fig_t423e_firstprinciples.png", dpi=130)
