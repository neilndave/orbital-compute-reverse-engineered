# Provenance tracer: logs every file a pipeline stage opens (reads and writes) under GTCFC_ROOT to trace/<stage>.jsonl. No behaviour change.
import os, sys, json
_root = os.environ.get("GTCFC_ROOT"); _stage = os.environ.get("GTCFC_STAGE")
if _root and _stage:
    _log = os.path.join(_root, "trace", _stage + ".jsonl"); _seen = set()
    _LIVE = []  # all inputs are already vendored under the portable runtime root
    def _hook(ev, args):
        if ev != "open" or not args or not isinstance(args[0], (str, bytes, os.PathLike)): return
        try:
            p = os.path.abspath(os.fsdecode(args[0]))
        except Exception: return
        for _a, _b in _LIVE:
            if p.startswith(_a): p = _b + p[len(_a):]
        if not p.startswith(_root) or "/trace/" in p or "__pycache__" in p: return
        m = args[1] if len(args) > 1 and isinstance(args[1], str) else "r"; fl = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
        w = any(c in m for c in "wax+") or bool(fl & (os.O_WRONLY | os.O_RDWR | os.O_CREAT))
        k = (p, w)
        if k in _seen: return
        _seen.add(k)
        with open(_log, "a") as f: f.write(json.dumps(dict(path=os.path.relpath(p, _root), write=w)) + "\n")
    sys.addaudithook(_hook)
