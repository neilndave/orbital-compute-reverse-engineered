"""t438 figure: count per Starship for the final Jun and Aug designs vs the SpaceX-quoted 46 / 30, with credibility of each assumption.  Data: box_gtc/results/t438/passes.jsonl, margin_table.json (ESTIMATE)."""
import json, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
recs = {}
for l in open("box_gtc/results/t438/passes.jsonl"):
    r = json.loads(l); recs[r["pass_"]] = r
n = lambda t: (recs[t]["res"]["layers"]["n"], recs[t]["res"]["books"]["n"])
mt = json.load(open("box_gtc/results/t438/margin_table.json"))
fig, ax = plt.subplots(1, 2, figsize=(17, 6.8), gridspec_kw={"width_ratios": [1.0, 1.25]})
a = ax[0]
rows = [("Jun final\nleaf 6, fold 5, 10 mm pitch,\nrack+equip 800, adapter 0.05", n("f_J_L60_f5"), "#1f77b4", 46),
        ("Jun, repo fold 4\n(same, fold 4)", n("f_J_L60_f4"), "#9ec3e6", 46),
        ("Jun, adapter 0.10\n(fold 5)", n("m_J_ad10_f5"), "#9ec3e6", 46),
        ("Jun, C2 point / MID\n(fold 5; same array area)", n("m_J_C2_f5"), "#9ec3e6", 46),
        ("Aug final = config E\nleaf 6, fold 6, same rest", n("f_A_E"), "#d95f02", 30),
        ("Aug, fold 5\n(option, fewer assumptions)", n("m_A_E_f5"), "#f1a46a", 30)]
for i, (lab, (l, b), c, t) in enumerate(rows):
    a.barh(i - 0.18, l, 0.34, color=c, label="layers = design count" if i == 0 else None); a.text(l + .4, i - .18, f"{l}", va="center", fontsize=9)
    a.barh(i + 0.18, b, 0.34, color=c, alpha=.45, hatch="//", edgecolor="white", label="books = upside" if i == 0 else None); a.text(b + .4, i + .18, f"{b}", va="center", fontsize=8)
    a.plot([t, t], [i - .45, i + .45], color="k", lw=2)
a.set_yticks(range(len(rows))); a.set_yticklabels([r[0] for r in rows], fontsize=8); a.invert_yaxis(); a.set_xlim(0, 56)
a.set_xlabel("satellites per Starship, volume-limited (ESTIMATE, p27 packer, step 0.1 m); black tick = SpaceX-quoted 46 (Jun) / 30 (Aug)")
a.set_title("Final designs vs the SpaceX-quoted counts\nJun 46 = zero slack (mass cap 98 t / 46); Aug 31 = +1 slack", fontsize=10); a.legend(fontsize=8, loc="lower right")
b = ax[1]; b.axis("off")
lines = [("Assumption", "Jun", "Aug", "Credibility / precedent"),
 ("Array leaf pitch", "6 mm", "6 mm", "EDGE: Mega-ROSA >50 kW/m3 = 6.0 mm (vendor claim);\nflown ROSA 40 kW/m3 = 7.4 mm (STATEMENT)"),
 ("2nd-stage width fold n", "5", "6 (5 packs 33)", "ASSUMED: repo baseline n=4; Newton fold case\nprepared, untested (ESTIMATE)"),
 ("Radiator pitch", "10 mm", "10 mm", "ESTIMATE: 4.3 mm clearance; panel sag 0.85 mm\nat 6 g (CalculiX, box CPU)"),
 ("Rack + equipment density", "800", "800", "STRETCH-but-public: GB200 NVL72 949, DGX H100 847 kg/m3"),
 ("Adapter / gap", "0.05 / 0.02 m", "0.05 / 0.02 m", "ASSUMED, sensitive: 0.10 m costs 3 sats (Jun 43)"),
 ("Array/rack split point", "C1", "C1", "C1 = public-credible array (0.96 kg/m2); count is\nthe same at MID and C2 (46)"),
 ("kW / kg / kW per t", "150/2130/70.4", "250/3267/76.5", "meets the 70 / 75 kW/t claims; FCC 4 t, 200 m2 radiator OK"),
 ("Margin used", f"{mt['Jun']['absorbed_total_kg']:.0f}/{mt['Jun']['margin_line_before_kg']:.0f} kg\n({mt['Jun']['margin_used_pct']}%)", f"{mt['Aug']['absorbed_total_kg']:.0f}/{mt['Aug']['margin_line_before_kg']:.0f} kg\n({mt['Aug']['margin_used_pct']}%)", "load path + fold hinge, per sat, inside the margin line;\ntotal mass unchanged"),
 ("Stack first mode (axial/lat)", "6.9 / 3.3 Hz", "7.0 / 3.4 Hz", "OPEN RISK: below Falcon-guide 25/10 Hz rec.\n(STATEMENT); Starship has no stated requirement")]
y = 1.0
for i, (c1, c2, c3, c4) in enumerate(lines):
    w = "bold" if i == 0 else "normal"; b.text(0.0, y, c1, fontsize=8, fontweight=w, va="top"); b.text(0.24, y, c2, fontsize=8, fontweight=w, va="top"); b.text(0.42, y, c3, fontsize=8, fontweight=w, va="top"); b.text(0.61, y, c4, fontsize=7.4, fontweight=w, va="top"); y -= 0.1 if i else 0.07
b.set_title("Assumptions and their precedent", fontsize=10)
fig.suptitle("t438: final replica designs, count per Starship vs the SpaceX-quoted 46 (Jun) / 30 (Aug)", fontsize=11)
fig.text(0.5, 0.005, "All values ESTIMATE/ASSUMED unless marked STATEMENT; vendor claims labelled; our satellite only, no SpaceX imagery.", ha="center", fontsize=7.5)
fig.tight_layout(rect=(0, 0.02, 1, 0.95)); fig.savefig("figures/fig_t438_final_designs.png", dpi=170); print("ok")
