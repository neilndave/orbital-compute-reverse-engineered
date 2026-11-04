#!/usr/bin/env python3
"""[t460 copy of yokehold_plan.py honouring K.N0_SAT / FLEET_N0_SAT]
[t442, t445 corrected] yoke hand-over fix for a stage-plan JSON.
CAUSE (STATEMENT from box scans): when a yoke body's planned path ends (t1) fleet_kin switches that yoke to the kinematic (Newton-chain) pose, which is anchored to the planned PLATES pose and only reaches the planned final yoke pose when the plates have also reached theirs.  With per-class plans the yoke path ended 1.8-2.2 s EARLIER than the plates (e.g. sat 0: yoke t1 18.66 s, plates1 t1 20.66 s) -> a jump to a mid-fold pose: yoke_bus -0.38 m, pod_own -0.33 m (0.02 s scan).
FIX (1, class 24 only so far): if the planned FINAL yoke pose differs from the kinematic final pose (the planner read the yoke at tau=13 s, before it had settled), retarget the last waypoint.  FIX (2): append a HOLD at the final waypoint to yoke0/yoke1 until the kinematic yoke pose has settled onto the planned final pose (found numerically per group of identical plans, 0.02 s grid).
usage (cwd = an overlay's experiments/poster dir, env as in fleet_replica_env.sh, FLEET_STAGEPLAN=IN.json):  python yokehold_plan.py IN.json OUT.json"""
import sys, os, json
sys.path.insert(0, os.getcwd())
import numpy as np
import fleet_kin_T45 as K
src, dst = sys.argv[1], sys.argv[2]
d = json.load(open(src)); fl = K.Fleet(); groups = {}
for k, v in d.items():
    assert not v.get("info", {}).get("yokehold_t442"), "already held: start from the original plan"
    groups.setdefault(json.dumps(v["bodies"]), []).append(int(k))
for key, sats in groups.items():
    s = sats[0]; sa = fl.sats[s]; ng = len(sa.n_cols); bs = K.PLAN[str(s)]["bodies"]
    assert [bs[ng + 2 + w]["name"] for w in (0, 1)] == ["yoke0", "yoke1"]
    old = [bs[ng + 2 + w]["t1"] for w in (0, 1)]
    for w in (0, 1): bs[ng + 2 + w]["t1"] = -1.0
    TF = K.N0_SAT.get(s, K.TAU_N0) - 0.5   # [t460] per-sat accordion start
    LATE = max(old) > TF + 1e-9      # [t445b] plan (plates/yoke) finishes AFTER the accordion has started: hand over at the yoke's own t1 onto the kinematic pose AT t1 (it is moving), no hold, no pop
    if LATE: TF = max(old); print(f"   group {s}: planned yoke t1 {TF:.2f} s is later than the accordion start ({K.TAU_N0:.1f} s) -> final yoke waypoint = kinematic pose at tau = t1 (continuous hand-over)", flush=True)
    fl.local(sa, TF); kfin = [sa._yoke[0][w] + sa.fD for w in (0, 1)]      # kinematic yoke pose just BEFORE the accordion starts (tau = K.TAU_N0 - 0.5; the yoke is static relative to the plates until then, afterwards it correctly follows the Newton accordion h(t)), plan frame
    for sk in sats:
        for w in (0, 1):
            b = d[str(sk)]["bodies"][ng + 2 + w]; dlt = float(np.abs(np.array(b["wps"][-1][0]) - kfin[w]).max())
            if dlt > 5e-4:
                print(f"   sat {sk} {b['name']}: planned final differs from the kinematic final by {dlt:.3f} m (planner took the yoke at tau=13 s, not settled) -> retargeted", flush=True)
                b["wps"][-1] = [kfin[w].tolist(), b["wps"][-1][1]]
    for w in (0, 1):
        bs[ng + 2 + w]["_w"][-1] = (kfin[w], bs[ng + 2 + w]["_w"][-1][1])
    taus = np.arange(0, TF, 0.02); bad = []
    if LATE: taus = taus[:0]
    for tau in taus:
        fl.local(sa, tau); y = sa._yoke[0]
        bad.append(max(np.abs(y[w] - (bs[ng + 2 + w]["_w"][-1][0] - sa.fD)).max() for w in (0, 1)) > 5e-4)
    bad = np.where(bad)[0]
    if len(bad) and bad[-1] == len(taus) - 1: print(f"   WARNING group {sats[0]}: the yoke has not settled by tau {TF:.1f} s (accordion start FLEET_TAU_N0 - 0.5)", flush=True)
    Th = float(taus[bad[-1]] + 0.02) if len(bad) else 0.0
    for w in (0, 1): bs[ng + 2 + w]["t1"] = old[w]
    print(f"group of sats {sats[0]}..{sats[-1]} (n={len(sats)}): yoke t1 {old[0]:.2f} -> hold until tau {Th:.2f}", flush=True)
    for sk in sats:
        for w in (0, 1):
            b = d[str(sk)]["bodies"][ng + 2 + w]
            if Th > b["t1"] + 1e-9:
                b["wps"].append(b["wps"][-1]); b["durs"].append(Th - b["t1"]); b["t1"] = Th
        d[str(sk)]["t_ready"] = max(d[str(sk)]["t_ready"], max(b["t1"] for b in d[str(sk)]["bodies"]))
        d[str(sk)].setdefault("info", {})["yokehold_t442"] = Th
json.dump(d, open(dst, "w")); print("->", dst)
