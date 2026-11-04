"""t436b figure: (left) satellites per Starship for the stretch vs credibility-adjusted configs; (right) leaf pitch vs stowed power density against public flexible-array figures."""
import json, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
R = "box_gtc/results/t436b/passes.jsonl"
recs = [json.loads(l) for l in open(R)]
def get(tag, sid):
    for r in recs:
        if r["pass_"] == tag and r["id"].startswith(sid): return r["res"]["layers"]["n"], r["res"]["books"]["n"]
    return None
# (label, jun tag, aug tag, step)
cfgs = [
 ("A  stretch: leaf 4, fold 4 (repo)\n(rack 1097 kg/m3, step 0.1; t436)", None, None, "0.1"),
 ("B  A with public rack 949", "b_stretch949", "b_stretch949", "0.25"),
 ("C  leaf 4 + fold 6", "d_L4_f6_a05", "d_L4_f6_a05", "0.25"),
 ("D  leaf 5 + fold 6", "e_s01_L5_f6_a05", "e_s01_L5_f6_a05", "0.1"),
 ("E  leaf 6 + fold 6", "e_s01_L6_f6_a05", "e_s01_L6_f6_a05", "0.1"),
 ("F  E with adapter 0.10", "e_s01_L6_f6_a10", "e_s01_L6_f6_a10", "0.1"),
 ("G  leaf 7.5 (flown ROSA) + fold 8", "e_s01_L75_f8_a05", "e_s01_L75_f8_a05", "0.1"),
 ("H  leaf 6, fold 4 (repo), adapter 0.10", "b_L6_r800_a10", "b_L6_r800_a10", "0.25"),
]
A_ref = {"J": (49, 50), "A": (30, 32)}  # t436 step-0.1 reference (stretch)
fig, ax = plt.subplots(1, 2, figsize=(15.5, 6.6), gridspec_kw={"width_ratios": [1.45, 1]})
a = ax[0]; y = np.arange(len(cfgs)); h = 0.19
for i, (lab, tj, ta, st) in enumerate(cfgs):
    j = A_ref["J"] if tj is None else get(tj, "J8"); au = A_ref["A"] if ta is None else get(ta, "A4")
    for k, (v, c, off, nm) in enumerate([(j[0], "#1f77b4", 1.5, "Jun layers"), (j[1], "#7fb2e5", 0.5, "Jun books"), (au[0], "#d95f02", -0.5, "Aug layers"), (au[1], "#f1a46a", -1.5, "Aug books")]):
        a.barh(i - off * h, v, h * 0.95, color=c, label=nm if i == 0 else None, hatch="//" if st == "0.25" else None, edgecolor="white", lw=0.3)
        a.text(v + 0.4, i - off * h, str(v), va="center", fontsize=7)
a.axvline(46, color="#1f77b4", ls="--", lw=1.3, label="Jun mass ceiling 46"); a.axvline(30, color="#d95f02", ls="--", lw=1.3, label="Aug mass ceiling 30")
a.axvline(45, color="#1f77b4", ls=":", lw=1.3, label="Jun 45 if load-path mass not absorbed"); a.axvline(29, color="#d95f02", ls=":", lw=1.3, label="Aug 29 if not absorbed")
a.set_yticks(y); a.set_yticklabels([c[0] for c in cfgs], fontsize=8); a.invert_yaxis()
a.set_xlabel("satellites per Starship, volume-limited (ESTIMATE, p27 packer; hatched = step 0.25 m, solid = step 0.1 m)")
a.set_title("How many fit once the stow levers are made credible\n(all: radiator pitch 10 mm, equipment 800 kg/m3, adapter 0.05 m unless stated)", fontsize=10)
a.legend(fontsize=7, loc="lower right", ncol=2); a.set_xlim(0, 80)
b = ax[1]; p = np.linspace(2, 12, 100); P = 0.2976 / p * 1000  # kW/m3, from checks.json: 74.4 kW/m3 at 4 mm
b.plot(p, 297.6 / p, color="k", lw=2, label="blanket-only power density, replica C1 array\n(0.962 kg/m2, ~332 W/kg wing; ESTIMATE)")
for v, nm, c in [(40, "ROSA flown ~40 kW/m3 (STATEMENT)", "#2ca02c"), (50, "Mega-ROSA >50 (claim)", "#9467bd"), (60, "SOLAROSA 60-80 (claim/target)", "#d62728")]:
    b.axhline(v, color=c, ls="--", lw=1.1); b.text(11.9, v + 1.5, nm, ha="right", fontsize=7.5, color=c)
b.axhspan(60, 80, color="#d62728", alpha=0.08)
for pp, nm in [(4, "4 mm"), (5, "5 mm"), (6, "6 mm"), (7.5, "7.5 mm")]:
    b.plot([pp], [297.6 / pp], "o", color="k"); b.annotate(nm, (pp, 297.6 / pp), textcoords="offset points", xytext=((-34, -14) if pp==7.5 else (6, 6)), fontsize=8)
b.axvspan(2, 3, color="#999999", alpha=0.25); b.text(2.05, 150, "2-3 mm:\nbeyond any\npublic claim", fontsize=8)
b.set_xlabel("leaf pitch (mm)"); b.set_ylabel("stowed power density (kW/m3, blanket pack only)")
b.set_title("Leaf pitch vs public flexible-array precedent\n(rigid 2-4 mm leaf is out: 1.2-1.3 kg/m2 and ~500x too soft)", fontsize=10)
b.set_ylim(0, 160); b.legend(fontsize=7.5, loc="upper right", bbox_to_anchor=(1, 0.88))
fig.suptitle("t436b: are the four stow assumptions credible?  Replica count per Starship (46 Jun / 30 Aug is the SpaceX-quoted target)", fontsize=11)
fig.text(0.5, 0.005, "Third-party/vendor claims are labelled; no SpaceX imagery. Rows use the C2-point rack (conservative; t438 uses the C1 rack: Jun 46 / Aug 31). Fold n = second-stage pleat count across the 14 m array width (repo baseline n=4; t438 adds a Newton fold-chain case).", ha="center", fontsize=7.5)
fig.tight_layout(rect=(0, 0.02, 1, 0.95)); fig.savefig("figures/fig_t436b_credibility.png", dpi=170)
print("ok")
