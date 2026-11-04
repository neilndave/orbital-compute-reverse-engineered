#!/usr/bin/env python3
"""t440b: make the OVERLAY COPY of fleet_stage_plan_T45.py count-generic. The repo planner hard-codes 24 radiator columns + 2 arrays + 2 yokes (+ pod) = body indices 24/25 (arrays), 26/27 (yokes), 28 (pod); the replica has NC = len(sat.n_cols) columns (8 per sat: 4 per wing) so the indices are NC, NC+1, NC+2, NC+3, NC+4.
usage: patch_stage_plan.py <overlay_dir>   (each replacement asserted to match exactly once per line group)"""
import sys, pathlib, re
p = pathlib.Path(sys.argv[1]) / "experiments/poster/fleet_stage_plan_T45.py"; s = p.read_text()
def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, ("patch target count", s.count(old), old[:70]); s = s.replace(old, new)
rep("xc0 = np.mean([bb.Cc0[0] for bb in bodies[:24]])", "NC = len(sa.n_cols); xc0 = np.mean([bb.Cc0[0] for bb in bodies[:NC]])")
rep("order = [26, 27] + sorted(range(24), key=lambda i: -abs(bodies[i].Cc0[0] - xc0)) + [24, 25] + ([28] if n > 28 else [])", "order = [NC + 2, NC + 3] + sorted(range(NC), key=lambda i: -abs(bodies[i].Cc0[0] - xc0)) + [NC, NC + 1] + ([NC + 4] if n > NC + 4 else [])")
rep("order = [26, 27, 24, 25] + sorted(range(24), key=lambda i: abs(bodies[i].Cc0[0] - xc0)) + ([28] if n > 28 else [])", "order = [NC + 2, NC + 3, NC, NC + 1] + sorted(range(NC), key=lambda i: abs(bodies[i].Cc0[0] - xc0)) + ([NC + 4] if n > NC + 4 else [])")
rep("order = [26, 27, 24, 25] + sorted(range(24), key=lambda i: -abs(bodies[i].Cc0[0] - xc0)) + ([28] if n > 28 else [])", "order = [NC + 2, NC + 3, NC, NC + 1] + sorted(range(NC), key=lambda i: -abs(bodies[i].Cc0[0] - xc0)) + ([NC + 4] if n > NC + 4 else [])")
rep("order = [26, 27] + [int(x) for x in _rng.permutation(26)] + ([28] if n > 28 else [])", "order = [NC + 2, NC + 3] + [int(x) for x in _rng.permutation(NC + 2)] + ([NC + 4] if n > NC + 4 else [])")
rep("order = [26, 27] + _f + [x for x in order if x not in _f and x not in (26, 27)]", "order = [NC + 2, NC + 3] + _f + [x for x in order if x not in _f and x not in (NC + 2, NC + 3)]")
# [t442] plates per wing: the repo planner/diag hard-code 80 leaf-section boxes per wing (20 leaves x 4 sections).  The replica has NLEAF*NSEC = 20 x 6 = 120 per wing, so unpatched, "plates0" = the first 80 of wing 0's 120 boxes and "plates1" = wing-0 boxes 80-119 + wing-1 boxes 0-39: both staging bodies had WRONG geometry (a 7 m smear) -> every plan was made against the wrong plates.
rep("if a.kind == \"yoke\" and b.name == \"plates\" + a.name[-1]: Bb = tuple(x[4 * 1:] for x in Bb)", "if a.kind == \"yoke\" and b.name == \"plates\" + a.name[-1]: Bb = tuple(x[K.NSEC:] for x in Bb)")
rep("if b.kind == \"yoke\" and a.name == \"plates\" + b.name[-1]: Ba = tuple(x[4 * 1:] for x in Ba)", "if b.kind == \"yoke\" and a.name == \"plates\" + b.name[-1]: Ba = tuple(x[K.NSEC:] for x in Ba)")
p.write_text(s); print("patched", p)
q = pathlib.Path(sys.argv[1]) / "experiments/poster/fleet_own_diag_T45.py"; s = q.read_text()
old = "g[f\"plates{w}\"] = (qp[w * 80:(w + 1) * 80], qR[w * 80:(w + 1) * 80], np.tile(K.PLATE_BOX / 2, (80, 1)))"
assert s.count(old) == 1; NPL = "(K.NLEAF * K.NSEC)"
s = s.replace(old, "g[f\"plates{w}\"] = (qp[w * %s:(w + 1) * %s], qR[w * %s:(w + 1) * %s], np.tile(K.PLATE_BOX / 2, (%s, 1)))" % ((NPL,) * 5)); q.write_text(s); print("patched", q)
