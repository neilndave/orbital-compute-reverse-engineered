# August orbital-compute GPU study, locked r11

Canonical SHA256: `a3bd7328425085fa29ceb053c437740ccad7150112a57fbf6c34c5d15010374b` (`RESULTS_CANONICAL.json`).

This is the r11 canonical. It replaces the earlier August lock (`f02f8220…`). It is the August design and nothing else, with three corrections:

1. **Compute payload.** The payload is exactly one Vera Rubin NVL72 (72 GPUs + 36 CPUs). Earlier wording said 79 GPUs. The 640.38 kg allocation and the 600 × 1200 × 937 mm box are stated assumptions.
2. **Coolant properties.** The radiator and eclipse models now pass the MPG40 coolant properties correctly (`repro/native/tools/r11/PROPERTY_PASSING.patch`).
3. **Peak-power acceptance.** Acceptance is 249.9 kW. The 250 kW peak target is unchanged, so this is a rounding tolerance, not a design change. Peak available at beginning of life is 249.91 kW.

## What stayed the same

The same 1,806,336-design search selects the same design point, index 1037888:
- 140 panels, 7 tubes per panel;
- 0.2587 mm fin;
- 861.75 m² array.

The search now finds 3,048 hard-feasible and 2,347 design-margin-feasible designs. The satellite mass is 3,026 kg.

`checks/NUMBER_TRACE_R10_VS_R11.md` lists every poster number before and after the change.

## Contents

| Path | What it holds |
|---|---|
| `GTC_POSTER_DRAFT.pdf` | Poster, 43 × 24 in, r11 public PDF. This is the only PDF in the package. |
| `RESULTS_CANONICAL.json` | Canonical candidate record: hashes, decisions, native results and poster numbers. |
| `checks/GATES_R11.json` | 51/51 gate predicates passed. |
| `checks/LAYOUT_R11_AUDIT.json` | Physical-PDF layout audit. |
| `checks/POSTER_NUMBERS_R11.json` | Each printed number with its source file, key path and source hash. |
| `checks/NUMBER_TRACE_R10_VS_R11.*` | Number trace, r10 vs r11. |
| `checks/NATIVE_CHECKS_R11.json` | Native model checks. |
| `checks/DEVICE_THERMAL_RECHECK.json` | Device thermal sensitivity. |
| `checks/EFFORT_METRICS_11D.json` | Effort metrics (historical record). |
| `figs/` | Poster preview and Isaac Sim RTX hero render. |
| `repro/` | Everything needed to regenerate the numbers, poster and hashes. See `repro/REPLICATE.md`. |

## Replicating

Follow `repro/REPLICATE.md`:
- **Tier 1:** `./run_all.sh` on any Linux box, CPU only, about 3 minutes.
- **Tier 2:** NVIDIA GB10 CUDA runs.
- **Tier 3:** reused evidence: PhysicsNeMo, Newton, CalculiX frame and panel.

Expected hashes are listed there. A clean-copy rerun reproduced the candidate hash and the poster byte-for-byte.

## Limitations

This is a research screening model, not a flight-qualified design.
- Peak 250 kW holds at beginning of life only.
- Rubin GPU/HBM temperatures are an estimate around a ≈370 K nominal target. Junctions are not qualified.
- Rigid-body deployment and screening FEA are not hardware tests.
- The effort span is a historical record, not a productivity claim.

LICENSE applies to original work only. CREDITS.md covers external dependencies. No endorsement is implied. The author attribution and the repository link appear only in the poster PDF.
