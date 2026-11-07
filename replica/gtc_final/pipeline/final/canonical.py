"""Canonical results file: every JSON output of the pipeline (stages + final), floats normalised to 10 significant digits, keys sorted;
raw-byte sha256 of pipeline-GENERATED json files omitted (their numbers are all included instead). Script and vendored-input hashes are kept.
Its sha256 is the single reproducibility hash compared across clean checkouts (box x86 and GB10 aarch64)."""
import json, os, glob, hashlib
ROOT = os.environ.get("GTCFC_ROOT", "/tmp/gtcfc_root")
GEN = lambda k: k.startswith(("stages/", "final/")) and k.endswith(".json")   # pipeline-generated file: raw-byte hash is platform dependent (last-bit float formatting)
def norm(v):
    if isinstance(v, float): return float(f"{v:.10g}")
    if isinstance(v, dict): return {k: ("<generated-file hash omitted>" if (k == "source_file_sha256" or (GEN(k) and isinstance(w, str) and len(w) == 64)) else norm(w)) for k, w in v.items()}
    if isinstance(v, list): return [norm(w) for w in v]
    return v
files = sorted(p for p in glob.glob(ROOT + "/stages/**/*.json", recursive=True) + glob.glob(ROOT + "/final/*.json") if not p.endswith("RESULTS_CANONICAL.json") and "/GB10_" not in p)   # GB10 parity result is a post-pipeline check (timing/host fields)
out = {os.path.relpath(p, ROOT): norm(json.load(open(p))) for p in files}
s = json.dumps(out, sort_keys=True, separators=(",", ":")); open("RESULTS_CANONICAL.json", "w").write(s)
h = hashlib.sha256(s.encode()).hexdigest(); open("RESULTS_CANONICAL.sha256", "w").write(h + "  RESULTS_CANONICAL.json\n"); print("files", len(files), "sha256", h)
