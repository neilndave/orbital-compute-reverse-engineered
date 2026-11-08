# GTC final candidate configuration (AI1_GTC_FINAL_CANDIDATE_v1)

This folder is the single configuration behind the GTC poster numbers: the scoped baseline plus three additions
(30-minute peak-power battery; MPG40 glycol coolant with fin-root heaters so the loop can stop in eclipse and restart; Whipple shields on the four central coolant trunks).
Radiator-header debris protection and panel spares remain OPEN. Status: concept estimate, not vendor-qualified.

- `results/GTC_FINAL_CANDIDATE.json`: every poster number, each with its source file, JSON path, stage, script, hashes and tool.
- `results/POSTER_DRAFTS.md`: poster numbers table and takeaway generated from that file.
- `results/NVIDIA_TOOLS_INVENTORY.md`: which NVIDIA tool produced what (and claims that are not backed).
- `results/ASSUMPTION_REGISTER.md`: each input labelled sourced / engineering assumption / open item.
- `results/RENDER_CHECK.json`: Omniverse renders R1/R2 against this configuration (what is and is not drawn).

## Reproduce

```
cp -a pipeline /tmp/gtcfc_root      # scripts use this canonical root
cd /tmp/gtcfc_root && PY=python3 ./run_pipeline.sh   # numpy, scipy, CoolProp 8.0.0
cd final && python3 gb10_final_parity.py              # optional: NVIDIA Warp 1.18 fp64 on a CUDA GPU
```

The run ends with `RESULTS_CANONICAL.json`; its sha256 must be `e151e4e1f5b6a588be95560a1251de018a868ba60588ae807f51e17d05030870`
(floats to 10 significant digits). The same hash was obtained from clean checkouts on an x86_64 CPU box and on the GB10 (aarch64), and the GB10 Warp fp64 parity check passed with a 9.16e-11 maximum difference.

`pipeline/INPUT_MANIFEST.json` lists every vendored input with its hash. Three inputs were edited for publication without changing any number: `eclipse_daily.json` trimmed to the 550/600 km entries, a local citation path, and personal names in label strings.
