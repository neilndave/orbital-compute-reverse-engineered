"""GPU/CPU performance metrics for the AI1 replica runs (GTC material).
Meter samples nvidia-smi at ~1 Hz while a chunk runs and records wall time, GPU-busy seconds, power, energy (Wh), SM clock, memory, temperature,
throttle flags; metrics.csv gets one row per chunk (atomic append), summary.json is rebuilt from it. Reuses (does not duplicate) the 1-minute logger in ~/gb10_work/logs/thermal.csv."""
import csv, json, os, subprocess, threading, time, glob, math
Q = ("temperature.gpu,utilization.gpu,power.draw,clocks.sm,memory.used,clocks_throttle_reasons.hw_slowdown,"
     "clocks_throttle_reasons.sw_thermal_slowdown,clocks_throttle_reasons.hw_thermal_slowdown,clocks_throttle_reasons.sw_power_cap")
FIELDS = ["time_pt", "type", "phase", "chunk", "device", "wall_s", "cpu_s", "gpu_busy_s", "work_n", "work_unit", "rate_per_s", "util_mean", "util_max",
          "power_mean_W", "power_max_W", "energy_Wh", "sm_mhz_mean", "sm_mhz_min", "mem_used_mib_max", "warp_pool_mib", "temp_start_C", "temp_max_C", "zone_max_start_C", "zone_max_C",
          "thermal_throttle_samples", "power_cap_samples", "n_samples", "note"]
def now_pt():
    return subprocess.run(["date", "+%F %T"], env=dict(os.environ, TZ="America/Los_Angeles"), capture_output=True, text=True).stdout.strip()
def _f(s):
    try: return float(str(s).replace("%", "").replace("W", "").replace("MHz", "").replace("MiB", "").strip())
    except Exception: return float("nan")
def have_smi():
    try: return subprocess.run(["nvidia-smi", "-L"], capture_output=True, timeout=10).returncode == 0 and os.environ.get("CUDA_VISIBLE_DEVICES", "x") != ""
    except Exception: return False
def read_gpu():
    """-> dict or None (None when there is no GPU / nvidia-smi)."""
    try:
        o = subprocess.run(["nvidia-smi", f"--query-gpu={Q}", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout.strip().split(",")
        v = [x.strip() for x in o]
        act = lambda s: 1 if s.lower().startswith("active") else 0
        return dict(temp=_f(v[0]), util=_f(v[1]), power=_f(v[2]), sm=_f(v[3]), mem=_f(v[4]), hw=act(v[5]), swt=act(v[6]), hwt=act(v[7]), pcap=act(v[8]))
    except Exception: return None
def zone_max():
    m = float("nan")
    for p in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
        try: m = max(m, int(open(p).read()) / 1000.0) if m == m else int(open(p).read()) / 1000.0
        except Exception: pass
    return m
class Meter:
    def __init__(self, enabled=True, period=1.0): self.enabled = enabled and have_smi(); self.period = period; self.s = []; self.zmax = float('nan'); self._stop = threading.Event(); self.t = None
    def __enter__(self):
        self.t0 = time.time(); self.c0 = time.process_time(); self.z0 = zone_max(); self.g0 = read_gpu() if self.enabled else None
        if self.enabled:
            self.s = [(self.t0, self.g0)] if self.g0 else []
            self.t = threading.Thread(target=self._run, daemon=True); self.t.start()
        return self
    def _run(self):
        while not self._stop.wait(self.period):
            g = read_gpu()
            if g: self.s.append((time.time(), g))
            z = zone_max()
            if z == z: self.zmax = z if self.zmax != self.zmax else max(self.zmax, z)
    def __exit__(self, *a):
        self._stop.set()
        if self.t: self.t.join(timeout=5)
        g = read_gpu() if self.enabled else None
        if g: self.s.append((time.time(), g))
        self.wall = time.time() - self.t0; self.cpu = time.process_time() - self.c0; self.z1 = zone_max()
    def summary(self):
        d = dict(wall_s=round(self.wall, 3), cpu_s=round(self.cpu, 3), zone_max_start_C=self.z0, zone_max_C=max([x for x in (self.z0, self.z1, self.zmax) if x == x] or [float('nan')]))
        S = [x for _, x in self.s]
        if not S: return d
        ts = [t for t, _ in self.s]; P = [x["power"] for x in S]
        E = sum(0.5 * (P[i] + P[i + 1]) * (ts[i + 1] - ts[i]) for i in range(len(P) - 1)) / 3600.0 if len(P) > 1 else float("nan")
        U = [x["util"] for x in S]
        d.update(util_mean=round(sum(U) / len(U), 1), util_max=max(U), gpu_busy_s=round(self.wall * sum(U) / len(U) / 100.0, 3), power_mean_W=round(sum(P) / len(P), 2), power_max_W=max(P),
                 energy_Wh=round(E, 4) if E == E else "", sm_mhz_mean=round(sum(x["sm"] for x in S) / len(S), 0), sm_mhz_min=min(x["sm"] for x in S),
                 mem_used_mib_max=max(x["mem"] for x in S), temp_start_C=S[0]["temp"], temp_max_C=max(x["temp"] for x in S),
                 thermal_throttle_samples=sum(1 for x in S if x["hw"] or x["swt"] or x["hwt"]), power_cap_samples=sum(x["pcap"] for x in S), n_samples=len(S))
        return d
def append_row(path, row):
    new = not os.path.exists(path)
    full = {k: "" for k in FIELDS}; full.update(row); full["time_pt"] = now_pt()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new: w.writeheader()
        w.writerow(full); f.flush(); os.fsync(f.fileno())
def build_summary(csv_path, out_json, thermal_csv=None):
    if not os.path.exists(csv_path): return {}
    rows = list(csv.DictReader(open(csv_path)))
    ch = [r for r in rows if r["type"] == "chunk"]
    def num(r, k):
        try: return float(r[k])
        except Exception: return float("nan")
    ph = {}
    for r in ch:
        p = ph.setdefault(r["phase"] + "|" + r["device"], dict(chunks=0, wall_s=0.0, gpu_busy_s=0.0, energy_Wh=0.0, work_n=0.0, util=[], power=[], sm=[], tmax=0.0, throttle=0, work_unit=r["work_unit"]))
        p["chunks"] += 1; p["wall_s"] += num(r, "wall_s"); p["gpu_busy_s"] += num(r, "gpu_busy_s") if num(r, "gpu_busy_s") == num(r, "gpu_busy_s") else 0
        e = num(r, "energy_Wh"); p["energy_Wh"] += e if e == e else 0; p["work_n"] += num(r, "work_n") if num(r, "work_n") == num(r, "work_n") else 0
        for k, key in (("util", "util_mean"), ("power", "power_mean_W"), ("sm", "sm_mhz_mean")):
            x = num(r, key)
            if x == x: p[k].append(x)
        t = num(r, "temp_max_C"); p["tmax"] = max(p["tmax"], t) if t == t else p["tmax"]; p["throttle"] += int(num(r, "thermal_throttle_samples") or 0) if num(r, "thermal_throttle_samples") == num(r, "thermal_throttle_samples") else 0
    out = dict(updated_pt=now_pt(), phases={})
    for k, p in ph.items():
        m = lambda L: round(sum(L) / len(L), 2) if L else None
        out["phases"][k] = dict(chunks=p["chunks"], wall_s=round(p["wall_s"], 1), gpu_busy_s=round(p["gpu_busy_s"], 1), energy_Wh=round(p["energy_Wh"], 3), work_n=p["work_n"], work_unit=p["work_unit"],
                                rate_per_s=round(p["work_n"] / p["wall_s"], 2) if p["wall_s"] else None, util_mean=m(p["util"]), power_mean_W=m(p["power"]), sm_mhz_mean=m(p["sm"]), temp_max_C=p["tmax"], thermal_throttle_samples=p["throttle"])
    out["total"] = dict(wall_s=round(sum(v["wall_s"] for v in out["phases"].values()), 1), energy_Wh=round(sum(v["energy_Wh"] for v in out["phases"].values()), 3), chunks=sum(v["chunks"] for v in out["phases"].values()))
    out["thermal_pauses"] = sum(1 for r in rows if r["type"] == "thermal_pause"); out["user_pauses"] = sum(1 for r in rows if r["type"] == "user_pause")
    cmp = [r for r in ch if r["phase"] == "G0_bench"]
    out["cpu_vs_gpu"] = {r["chunk"] + "|" + r["device"]: dict(wall_s=r["wall_s"], rate_per_s=r["rate_per_s"], work_unit=r["work_unit"]) for r in cmp}
    if thermal_csv and os.path.exists(thermal_csv):
        try:
            t = list(csv.DictReader(open(thermal_csv))); out["thermal_log_tail"] = dict(rows=len(t), last=t[-1] if t else None, note="1-minute board log from ~/gb10_work/logs/thermal_log.sh (reused, not duplicated)")
        except Exception: pass
    tmp = out_json + ".tmp"; json.dump(out, open(tmp, "w"), indent=1); os.replace(tmp, out_json); return out
