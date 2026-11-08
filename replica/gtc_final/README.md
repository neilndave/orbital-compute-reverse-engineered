# GTC final configuration v2 (AI1_GTC_FINAL_V2_AL)

This folder is the single configuration behind the GTC poster numbers: the scoped baseline plus three additions
(30-minute peak-power battery; MPG40 glycol coolant with fin-root heaters so the loop can stop in eclipse and restart; Whipple shields on the four central coolant trunks).
v2 changes the radiator fin from bonded K13D70 CFRP (30 mm / 0.20 mm) to Al 6061-T6 integral/brazed fins (26 mm half-length, 0.225 mm, 60 mm tube pitch, no bondline), same 77/128 panel footprint and coating.
It supersedes AI1_GTC_FINAL_CANDIDATE_v1. Radiator-header debris protection, panel spares, the 6061 braze process and the higher tube debris exposure remain OPEN.
Status: simulation-based concept estimate, not flight hardware, not qualified.

- `results/GTC_FINAL_CANDIDATE.json`: every poster number, each with its source file, JSON path, stage, script, hashes and tool.
- `results/POSTER_DRAFTS.md`: poster numbers table and takeaway generated from that file.
- `results/NVIDIA_TOOLS_INVENTORY.md`: which NVIDIA tool produced what (and claims that are not backed).
- `results/ASSUMPTION_REGISTER.md`: each input labelled sourced / engineering assumption / open item.
- `results/RENDER_CHECK.json`: Omniverse renders against this configuration (geometry unchanged by v2; what is and is not drawn).
- `nvidia_metrics/`: the GPU-vs-CPU benchmark harness and its raw results (`NVIDIA_METRICS.json` is the roll-up).

## Reproduce

```
cp -a pipeline /tmp/gtcv2_root      # scripts use this canonical root
cd /tmp/gtcv2_root && PY=python3 ./run_pipeline.sh   # numpy, scipy, CoolProp 8.0.0
cd final && python3 gb10_final_parity.py              # optional: NVIDIA Warp 1.18 fp64 on a CUDA GPU
```

The run ends with `RESULTS_CANONICAL.json`; its sha256 must be `1cfbdb7793ec72e5509f7cf3a1de071465930565aa0013b3316ef49db072c13e`
(floats to 10 significant digits). The same hash was obtained from clean runs on an x86_64 CPU box and on the GB10 (aarch64), and the GB10 Warp fp64 parity check passed with a 1.44e-10 maximum difference (10 rows).

## GPU measurements (nvidia_metrics/NVIDIA_METRICS.json)

All fp64. CPU baselines are single-core (same Warp code on the CPU backend, NumPy, and SciPy direct). Medians of repeated warm runs; spreads are in the raw files.

| Measurement | Result |
|---|---|
| Thermal-root Monte Carlo, 10 million draws | 21.0 M draws/s on the GB10 GPU; 370x one Grace core (NumPy); 60x one Grace core (same Warp code, 1 M draws); max difference 1.1e-13 K |
| Single fin solve (Newton + PCG) | GPU slower than one Grace core below 10,240 cells (0.86x at the 2,560-cell production grid); 20x faster at 163,840 cells; SciPy direct solve is faster than both |
| Validation | second-order grid convergence (order 2.0000) against an independent 1-D reference; production-grid error 5.5e-7; Richardson 7.3e-13; energy-balance residual 5.2e-13 |
| End to end | pipeline 23.0 s on the GB10 vs 60.5 s on the x86 box, identical results hash; 585-solve fin table 101.9 s GPU vs 88.0 s Grace CPU |
| Energy | 0.69 J per million Monte Carlo draws (GPU board power above idle, nvidia-smi 100 ms samples) |

`pipeline/INPUT_MANIFEST.json` lists every vendored input with its hash. Three inputs were edited for publication without changing any number: `eclipse_daily.json` trimmed to the 550/600 km entries, a local citation path, and personal names in label strings.

June freeze-hardware compliance budget is 66 kg (approved t627u), with 65.7 kg actual hardware. This is an allocation-only change; mass and reserve are unchanged. Original GB10 timing/parity evidence predates this bookkeeping change.
