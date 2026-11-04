# t438 derisk (a, second half): flexible-blanket fold strain / stiffness screening at the chosen leaf pitch.  ESTIMATE / ASSUMED inputs, analytic, box CPU.
# Z-fold hairpin: blanket (substrate + cells) pitch p; the fold zone carries NO cells (cell strings end before each fold line), so only the substrate bends.  Bending strain of a layer of thickness t at centreline radius Rc:  eps = t / (2 Rc).
# Rc = (p - t_stack)/2 where t_stack is the thickness of the folded sheet pair at the hairpin (substrate only in the fold zone).   Inputs below are ASSUMED handbook-class values, not repo or SpaceX numbers.
import json, math, pathlib
sub_um = [25, 50, 75]                  # ASSUMED Kapton-class substrate thickness in the fold zone (um)
yield_eps = 0.03                       # ASSUMED Kapton-class yield strain (~3 %, datasheet-class; plastic crease above it, elongation-to-break far higher)
cell_eps = 0.002                       # ASSUMED crystalline-cell fracture strain scale (~0.1-0.2 %): cells must stay flat, off the fold line
cell_stack_mm = (0.3, 0.5)             # ASSUMED blanket thickness with cells (t436b)
R = {}
for p in (7.4, 6.0, 5.0, 4.0):
    row = {}
    for t in sub_um:
        Rc = (p - 2 * t / 1000) / 2    # mm: hairpin of two substrate layers
        row[f"substrate_{t}um"] = dict(Rc_mm=round(Rc, 2), eps_pct=round(100 * t / 1000 / (2 * Rc), 2), ok_below_yield=bool(t / 1000 / (2 * Rc) < yield_eps))
    # if the cell-bearing blanket had to bend at the same hairpin (it must not):
    Rc_c = (p - 2 * cell_stack_mm[1]) / 2
    row["cells_bent_would_need_Rc_mm"] = round(Rc_c, 2)
    row["cell_strain_pct_if_bent_0.4mm_stack"] = round(100 * 0.4 / (2 * max((p - 0.8) / 2, 1e-3)), 1) if p > 0.8 else None
    row["cell_free_fold_zone_mm_each_fold"] = round(math.pi * (p / 2), 1)       # arc length of the hairpin (centreline ~ pi*Rc)
    R[f"pitch_{p}mm"] = row
# deployed-blanket stiffness is NOT a launch-stow issue; stowed-stack check: bearing pressure at the bottom of a 20-leaf stack at 6 g (blanket 0.96 kg/m2 C1 Jun)
sig_per_leaf_kgm2 = 0.962; n = 20; P_bearing_Pa = sig_per_leaf_kgm2 * n * 9.81 * 6 * 1.25
R["stowed_bearing_pressure_6g_FS1.25_Pa"] = round(P_bearing_Pa, 0)
R["stowed_bearing_pressure_note"] = "about %.1f kPa on the bottom blanket of one 20-leaf stack (blanket weight only, flat hold-down) -- negligible vs any cell/coverglass load limit; the real hold-down (spring plate) force is a design choice (ASSUMED)" % (P_bearing_Pa / 1e3)
R["label"] = "ESTIMATE/ASSUMED: analytic hairpin bending strain only; no creep/crease-fatigue, no deployment-torque or tension test; real blankets (ROSA 7.4 mm flown pitch = STATEMENT, Redwire flysheet) are rolled/z-folded with proprietary details"
R["verdict_rule"] = "pass if substrate strain at the chosen pitch is below the assumed 3 % yield strain with cells kept off the fold line"
json.dump(R, open(pathlib.Path(__file__).resolve().parent / "results/t438/blanket_check.json", "w"), indent=1); print(json.dumps(R, indent=1))
