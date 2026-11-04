# t438 (adapted from t436): stowed-stack image of the best packed config (our satellite only; no SpaceX imagery). Data: box_gtc/results/t436/passes.jsonl (tag P2_combo_leaf4, layers arch). ESTIMATE geometry.
import json, sys, math
REPO = "vendor/same_rack"; sys.path[:0] = [f"{REPO}/experiments/parity27", f"{REPO}/experiments/knobs", f"{REPO}/src"]; sys.argv = ["x"]
import repack_stacks_T45 as R
_pk = R._pack
def _pack_sorted(*a, **k):
    H, pl = _pk(*a, **k); return H, sorted(pl, key=lambda p: p['lo_m'][2] + p['orient_m'][2])   # t438: draw higher items last so arrays under radiators stay visible
R._pack = _pack_sorted
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
TAGS = {"J8_C1": "f_J_L60_f5", "A4_C1": "f_A_E"}; COL = dict(array="#e8a33d", radiator="#4a7fb5", bus="#6a9b5a")
runs = {}
for l in open("box_gtc/results/t438/passes.jsonl"):
    r = json.loads(l)
    for pid_, tg in TAGS.items():
        if r["pass_"] == tg: runs[pid_] = r
fig, ax = plt.subplots(2, 3, figsize=(15, 9.4), gridspec_kw=dict(width_ratios=[1.0, 1.15, 1.25]))
names = {"J8_C1": "June final (leaf 6 mm, fold 5): 150 kW, 2,130 kg", "A4_C1": "August final (config E: leaf 6 mm, fold 6): 250 kW, 3,267 kg"}
for row, pid in enumerate(("J8_C1", "A4_C1")):
    r = runs[pid]; seq = r["res"]["layers"]["seq"]; n = r["res"]["layers"]["n"]; its = [(a, b, tuple(c)) for a, b, c in r["items"]]
    # (1) side view of the stack in the bay
    a = ax[row, 0]; zs = [z / 100 for z in range(0, 1725, 5)]
    a.fill_betweenx(zs, [-R.r_allowed(z) for z in zs], [R.r_allowed(z) for z in zs], color="#eeeeee", zorder=0); a.plot([-R.r_allowed(z) for z in zs], zs, "k-", lw=.8); a.plot([R.r_allowed(z) for z in zs], zs, "k-", lw=.8)
    cnt = 0
    for i, s in enumerate(seq):
        c = "#7aa6d6" if i % 2 else "#98c2a3"; w = s["X"]; a.add_patch(Rectangle((-w / 2, s["z0"]), w, s["H"], fc=c, ec="k", lw=.5))
        cnt += s["m"]
    a.set_xlim(-4.3, 4.3); a.set_ylim(0, 17.5); a.set_aspect("equal"); a.set_ylabel("height in bay (m)"); a.set_xlabel("width (m)")
    a.set_title(f"{names[pid]}\n{n} satellites in {len(seq)} levels (side view)", fontsize=10)
    # (2) top view of the most common level
    from collections import Counter
    best = Counter((s["m"], s["X"], s["Y"]) for s in seq).most_common(1)[0][0]; m, X, Y = best
    a = ax[row, 1]; a.add_patch(Circle((0, 0), 4.0, fc="none", ec="k", lw=1)); a.add_patch(Circle((0, 0), 3.95, fc="none", ec="gray", lw=.5, ls="--"))
    for k in range(m):
        y0 = -(m * Y + (m - 1) * 0.05) / 2 + k * (Y + 0.05); a.add_patch(Rectangle((-X / 2, y0), X, Y, fc="#dbe9f5", ec="k", lw=.7))
        H, placed = R._pack(X, Y, False) if k == 0 else (H, placed)
        if k == 0: R.items = its; R._PC = {}; H, placed = R._pack(X, Y, False)
        for p in placed:
            ox, oy, oz = p["orient_m"]; lx, ly, lz = p["lo_m"]; a.add_patch(Rectangle((-X / 2 + lx, y0 + ly), ox, oy, fc=COL[p["kind"]], ec="k", lw=.3, alpha=.9))
    a.set_xlim(-4.3, 4.3); a.set_ylim(-4.3, 4.3); a.set_aspect("equal"); a.set_xlabel("m"); a.set_title(f"one level ({m} satellites, plan view, bay r = 4.0 m)", fontsize=10)
    # (3) one satellite stowed: plan and side
    a = ax[row, 2]; R.items = its; R._PC = {}; H, placed = R._pack(X, Y, False)
    for p in placed:
        ox, oy, oz = p["orient_m"]; lx, ly, lz = p["lo_m"]; a.add_patch(Rectangle((lx, ly), ox, oy, fc=COL[p["kind"]], ec="k", lw=.4))
    a.add_patch(Rectangle((0, 0), X, Y, fc="none", ec="k", lw=1)); 
    for p in placed:
        ox, oy, oz = p["orient_m"]; lx, ly, lz = p["lo_m"]; a.add_patch(Rectangle((lx, -0.5 - H + lz), ox, oz, fc=COL[p["kind"]], ec="k", lw=.4))
    a.add_patch(Rectangle((0, -0.5 - H), X, H, fc="none", ec="k", lw=1)); a.set_xlim(-.3, X + .3); a.set_ylim(-0.5 - H - .3, Y + .3); a.set_aspect("equal")
    a.text(X / 2, Y + .05, f"plan {X:.2f} x {Y:.2f} m", ha="center", fontsize=8); a.text(X / 2, -0.5 - H - .2, f"side: {H:.2f} m thick", ha="center", fontsize=8)
    a.set_title("one stowed satellite: array (orange), radiators (blue), rack+equip (green)", fontsize=8.5); a.set_xlabel("m")
fig.suptitle("t438 final configs: stowed stack of our replica satellites in a Starship-class bay (repo packer, ESTIMATE)\nLevers: 6 mm flexible array leaf, fold 5 (Jun) / 6 (Aug), 10 mm radiator pitch, rack+equipment 800 kg/m3, 0.05 m adapter. Jun 46 / Aug 31 packed (30 kept); loads, dispenser and deployment not checked here.", fontsize=10)
fig.tight_layout(rect=(0, 0, 1, .92)); fig.savefig("figures/fig_t438_stowed_stack_final.png", dpi=170); print("ok")
