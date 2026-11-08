"""Collect the PhysicsNeMo surrogate v2 results (run on GB10; set S to the surrogate run folder) into one poster source file, with source hashes."""
import json, hashlib
S = "<surrogate-run>/"
fs = ["metrics.json", "screening_metrics.json", "thermal_metrics.json", "REPORT.md", "MANIFEST_SHA256.json"]
out = {"label": "PhysicsNeMo 2.2.0 local fin-efficiency surrogate v2 (FullyConnected 4x64 SiLU, supervised data loss, not a PINN); GB10",
       "scope": "local Al 6061 fin domain only (L 24-28 mm, t 0.205-0.245 mm); thermal closure at fixed radiator rise; not freeze/restart, not spacecraft optimisation",
       "source_sha256": {f: hashlib.sha256(open(S + f, "rb").read()).hexdigest() for f in fs},
       "metrics": json.load(open(S + "metrics.json")), "screening": json.load(open(S + "screening_metrics.json")),
       "thermal": json.load(open(S + "thermal_metrics.json"))}
out["timing_batch_max"] = max(int(k) for k in out["metrics"]["timing"]["cuda"])  # derived from timing keys
json.dump(out, open("SURROGATE_V2.json", "w"), indent=1); print("ok")
