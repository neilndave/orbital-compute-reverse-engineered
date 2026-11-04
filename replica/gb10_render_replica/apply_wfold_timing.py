#!/usr/bin/env python3
"""Key the render's width-fold duration (fleet_kin TAU_W, placeholder 14 s) to the Newton wfold result.
usage: apply_wfold_timing.py <Jun|Aug> <work dir that holds newton_array/wfold_n<N>_w*.json>      (Jun n=5, Aug n=6)
Prints the file results/<tag>/wfold_timing_<B>.env to be sourced before the render (export FLEET_TAU_W=...).  Uses the SLOWEST latched run found (t_all_latched, s after release of the width fold) -> conservative clip timing.
If no result is found it writes the 14 s placeholder and says so (STATEMENT of status, not a result)."""
import sys, glob, json, pathlib
B = sys.argv[1]; W = pathlib.Path(sys.argv[2]); n = {"Jun": 5, "Aug": 6}[B]
W0SEL = sys.argv[sys.argv.index("--w0") + 1] if "--w0" in sys.argv else None   # [t445] pick ONE drive speed (the design W0 = 0.17 rad/s); without --w0 the slowest of ALL W0 runs (incl. the 0.10 sweep point, 28 s) would be taken
ts = [json.load(open(p)).get("t_all_latched") for p in glob.glob(str(W / (f"**/wfold_n{n}_w{W0SEL}.json" if W0SEL else f"**/wfold_n{n}_w*.json")), recursive=True)]
ts = [t for t in ts if t is not None]
H = pathlib.Path(__file__).resolve().parent; out = H / "work" / f"wfold_timing_{B}.env"; out.parent.mkdir(exist_ok=True)
APPLY = "--apply" in sys.argv     # [t441] the stage plans (clearance-verified) assume the 14 s width fold: a different FLEET_TAU_W at render time is NOT covered by that proof -> default keeps 14 s and only REPORTS the Newton times; --apply = deliberate override (then re-plan + re-check clearance)
if ts and not APPLY: tau = 14.0; msg = f"Newton wfold n={n}: t_all_latched over {len(ts)} run(s) = {sorted(round(t, 1) for t in ts)} s (REPORT ONLY); keeping the 14 s the plans were checked with (use --apply to override, then re-plan)"
elif ts: tau = round(max(ts), 1); msg = f"Newton wfold n={n}: slowest t_all_latched {tau} s over {len(ts)} run(s)  (--apply: plans must be re-checked)"
else: tau = 14.0; msg = "NO Newton wfold result found: keeping the 14 s PLACEHOLDER"
# [t445] the accordion (FLEET_TAU_N0, repo 27 s = TAU_W0 13 + TAU_W 14) starts when the width fold ends -> keep that tie when TAU_W changes
out.write_text(f"export FLEET_TAU_W={tau}\nexport FLEET_TAU_N0={round(13.0 + tau, 2)}\n"); print(msg, "->", out)
