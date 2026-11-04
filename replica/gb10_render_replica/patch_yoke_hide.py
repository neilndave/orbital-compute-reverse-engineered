#!/usr/bin/env python3
"""[t445] hide the yoke boom while the satellite is still stowed / coasting (tau < 0), overlay copy only.  FLEET_YOKE_HIDE_STOWED=1 (set in scripts/fleet_replica_env.sh).
CAUSE (STATEMENT, box mesh-OBB check): with a stage plan fleet_kin draws the yoke from tau = 0 on, at 'the pack's top face' -- but the replica pack has NO yoke item (arrays, equip, rack, radiators only) and the layer gap is 0.0355 m while the yoke box is 0.08 m thick.  So a stowed yoke
(a) overlaps the next layer's pod/bus by up to 0.05 m (every adjacent-layer pair, -0.05 m), and (b) for the rot90 3-across layer (sats 24-26, stowed frame stood on end) it stands VERTICAL, 3.6 m tall, through layers 11-13 (mesh-OBB gaps down to -0.76 m).
The repo itself hides the yoke until tau = TAU_STAGE + 26 * TAU_GSTEP (12.9 s) when there is no plan; with FLEET_YOKE_HIDE_STOWED=1 the planned yoke appears at tau = 0 (unfold start, after release + attitude manoeuvre, satellite alone) instead of at the release.
OPEN DESIGN ITEM (not hidden by this patch): the yoke has no stowed volume in the pack.  usage: patch_yoke_hide.py <overlay_dir>"""
import sys, pathlib
p = pathlib.Path(sys.argv[1]) / "experiments/poster/fleet_kin_T45.py"; s = p.read_text()
old = "(0.0 if (PLAN is not None or tau >= TAU_STAGE + TAU_GSTEP * 26) else 1.0e5)"
new = "(0.0 if ((PLAN is not None and not (os.environ.get('FLEET_YOKE_HIDE_STOWED', '0') == '1' and tau < 0.0)) or tau >= TAU_STAGE + TAU_GSTEP * 26) else 1.0e5)"
assert s.count(old) == 1, "patch target not found exactly once"
p.write_text(s.replace(old, new)); print("patched", p)
