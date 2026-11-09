"""Portable wall-clock stage runner; timings never enter canonical model results."""
import sys,time,subprocess
t0=time.perf_counter()
r=subprocess.run(sys.argv[3:])
with open(sys.argv[1],"a") as f:f.write(f"{sys.argv[2]}\t{time.perf_counter()-t0:.6f}\n")
raise SystemExit(r.returncode)
