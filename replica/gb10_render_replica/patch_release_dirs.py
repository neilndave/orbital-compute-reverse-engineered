#!/usr/bin/env python3
"""t440c release plan for TWO/THREE satellites per layer (overlay copy only; the repo is untouched).  The repo release has ONE satellite per layer, direction alternating by layer parity, speed 0.2 m/s.
With two satellites per layer at x = -1.58 / +1.59 m the repo rule sends both the same way at the same speed: the slow attitude change (30-500 s) then makes neighbours collide
(sat-sat checker on the Aug fleet: -0.99 m at T = 261-307 s).  New rule (ASSUMED, illustrative): a satellite off the bay centreline leaves OUTWARD (sign of p0x); even layers at V_EXIT, odd layers at V_EXIT*FLEET_ODD_SPEED (default 2.6: zero sat-sat overlaps at 2.6; 2.0 leaves four AABB gaps of -0.02..-0.08 m but no body overlap; 1.7 leaves 46 events)
so z-neighbours separate; a centreline satellite in a layer that also has side satellites leaves FLEET_CENTRE_DELAY s later (default 25) in the layer-parity direction.  Alone-on-centre satellites: unchanged rule.
usage: patch_release_dirs.py <overlay_dir>"""
import sys, pathlib
q = pathlib.Path(sys.argv[1]) / "experiments/poster"; p = q / "fleet_kin_T45.py"; s = p.read_text()
def rep(old, new):
    global s
    assert s.count(old) == 1, ("patch target not found exactly once", old[:70]); s = s.replace(old, new)
rep("sa.sgx = 1.0 if sa.layer % 2 == 0 else -1.0; sa.Trel = T_STAG * sa.layer;",
    "sa.sgx = 1.0 if sa.layer % 2 == 0 else -1.0; sa.Trel = T_STAG * sa.layer; sa.vx = V_EXIT; side = [o for o in self.sats if o.layer == sa.layer and abs(o.p0[0]) > 0.5]\n"
    "            if '_replica' in LAY and os.environ.get('FLEET_RELEASE_DIRS', '1') == '1':\n"
    "                sa.vx = V_EXIT * (1.0 if sa.layer % 2 == 0 else float(os.environ.get('FLEET_ODD_SPEED', '2.6')))\n"
    "                if abs(sa.p0[0]) > 0.5: sa.sgx = 1.0 if sa.p0[0] > 0 else -1.0\n"
    "                elif side: sa.Trel += float(os.environ.get('FLEET_CENTRE_DELAY', '25'))\n"
    "            pass;")
rep("/ V_EXIT; sa.vy = V_Y", "/ sa.vx; sa.vy = V_Y")
rep("p[0] += sa.sgx * V_EXIT * max(T - sa.Trel, 0.0)", "p[0] += sa.sgx * sa.vx * max(T - sa.Trel, 0.0)")
p.write_text(s)
c = q / "fleet_clearance_T45.py"; t = c.read_text(); o = "sa.sgx * m_sat * K.V_EXIT"
assert t.count(o) == 1; c.write_text(t.replace(o, "sa.sgx * m_sat * sa.vx")); print("patched release directions in", q)
