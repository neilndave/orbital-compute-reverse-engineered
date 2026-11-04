"""Append-only process logger for the AI1 replica orbit/eclipse design loop.  Never rewrites or deletes: every call opens files in 'a' mode.
Times: box clock is Taipei (+0800); PT = Taipei - 16 h.  Both are written to every record."""
import json, time, os, datetime as dt
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "process_log")
os.makedirs(D, exist_ok=True)
def _stamp():
    now = dt.datetime.now().astimezone()
    pt = now.astimezone(dt.timezone(dt.timedelta(hours=-8)))
    return dict(t_box_iso=now.isoformat(timespec="seconds"), t_pt_iso=pt.isoformat(timespec="seconds"), t_unix=round(time.time(), 3))
def log(stream, **kw):
    rec = dict(_stamp(), stream=stream); rec.update(kw)
    with open(os.path.join(D, stream + ".jsonl"), "a") as f:
        f.write(json.dumps(rec, default=float) + "\n")
    return rec
def event(kind, text, **kw):  # kind: decision | surprise | correction | milestone | issue | note
    return log("events", kind=kind, text=text, **kw)
def source(variable, label, url, claim, **kw):  # label: STATEMENT/ESTIMATE/INFERENCE/ASSUMED
    return log("sources", variable=variable, label=label, url=url, claim=claim, **kw)
def meta(iteration, candidate, verdict, reason, est_impact_pct=None, **kw):  # verdict: added | rejected | deferred
    return log("meta_candidates", iteration=iteration, candidate=candidate, verdict=verdict, reason=reason, est_impact_pct=est_impact_pct, **kw)
