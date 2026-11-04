import json, time, datetime as dt, os
P = "replica/process_log/t444.jsonl"
def log(check, tool, inputs, results, surprises="", secs=None, verdict=None, **kw):
    now = dt.datetime.now().astimezone(); pt = now.astimezone(dt.timezone(dt.timedelta(hours=-8)))
    rec = dict(t_box_iso=now.isoformat(timespec="seconds"), t_pt_iso=pt.isoformat(timespec="seconds"), stream="t444", check=check, tool=tool, inputs=inputs, results=results, surprises=surprises, wall_s=secs, verdict=verdict, **kw)
    with open(P, "a") as f: f.write(json.dumps(rec, default=float) + "\n")
