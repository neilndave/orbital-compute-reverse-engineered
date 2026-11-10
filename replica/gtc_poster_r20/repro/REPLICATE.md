# Replicating the r20 GTC poster (numbers from the locked r11 canonical, approved Nov 8 2026)

Scope: the August design with exactly one Vera Rubin NVL72 (72 GPUs + 36 CPUs), the MPG40 coolant-property fix, and a
249.9 kW peak-power acceptance threshold (a rounding tolerance on the unchanged 250 kW target). Nothing else changed:
same exterior geometry, same 861.75 m² array, same 140-panel radiator, same selected search index (1037888).

Every number printed on the poster is in `out/POSTER_NUMBERS_R11.json` with its source file, key path and raw value.
`out/NUMBER_TRACE_R10_VS_R11.{md,csv,json}` lists every r10 number next to its r11 value.

## Environments
| Tier | Where | Python / packages |
|---|---|---|
| Native model, sweep inputs, box CPU sweep/scenarios, numbers | any Linux box | Python 3.13, `native_requirements.txt` (CoolProp 8.0.0, Warp 1.19.0, numpy 2.5.4, scipy 1.18.1) |
| Poster PDF + audit | any Linux box, DejaVu Sans fonts installed | `poster_requirements.txt` (matplotlib 3.11.2, qrcode 8.2, PyMuPDF 2.1) and poppler-utils (`pdftotext`) |
| GPU search, scenarios, warp.Tape, timing | NVIDIA GB10 (CUDA) + one Cortex-X925 core | `gb10_requirements.txt` (Python 3.12.3, Warp 1.18.0, numpy 2.5.4, scipy 1.18.1) |

## Tier 1: one command, CPU only (about 3 minutes)
```bash
export PY_NATIVE=/path/to/native/python PY_POSTER=/path/to/poster/python
export POSTER_AUTHOR='<approved author>' POSTER_ASSISTANT='<approved assistant>' REPO_URL='https://github.com/<owner>/<repo>'
./run_all.sh
```
`run_all.sh` runs, in order:
1. `native/run_r11_native.sh`: the corrected-MPG40 native chain (thermal → freeze scenarios → six August MPG40 eclipse
   transients → water keep-warm → freeze mass → assemble → final ledger → fixed-array power check `tools/r11/power_check.py`).
   The property fix itself is `native/tools/r11/PROPERTY_PASSING.patch` (already applied to the vendored sources).
2. `sweep/make_sweep_inputs.py`: regenerates `sweep/SWEEP_INPUTS.json` **only** from step-1 outputs (pumps from
   `native/r11_out/NATIVE_CHECKS.json`, header/rack/trunk inventories from `THERMAL_SPIN1.json`). This is the single source:
   the earlier 0.05% header-coefficient drift and the 16.4 W nominal-pump offset are gone.
3. Frozen-control sweep on box CPU with the r11 kernel (pre-fix August inputs, strict 250.000 kW): must give 3095 / 2398 / index 1037888.
4. r11 sweep (1,806,336 designs) and 1,048,576-scenario run on box CPU.
5. `evidence/device/device_thermal_recheck.py`: the Rubin GPU/HBM conditional sensitivity (371 / 373 K central case).
6. `numbers/derive_numbers.py gb10_out` then `numbers/make_number_trace.py`.
7. `poster/make_poster_r20.py --release poster_inputs/RELEASE_R11_K712_4K_CROP_fixed_r20right.png` (DRAFT and PUBLIC PDFs into `out/poster_r20/`). r20 is the final GTC poster: four 40 pt panel titles (no headlines) with the finding under each chart; Problem + boxed "Why it matters" (12 coworking days from `evidence/effort/EFFORT_UPDATE_R17.json`); steady-state thermal text only (rack coolant in/out, Rubin GPU/HBM estimates from the steady check in `evidence/transient/TRANSIENT_PEAK.json`); Panel 2 adds the all-core CPU bars from `speed/SPEED_ALLCORE_R11.json`; Panel 4 plots all 36 representative hinges (21 wing + 5 width + 10 radiator) with numbered phase bands and a key; one source + disclaimer footnote. The release still is the r18 rotation-fixed frame cropped from the right only (`tools/crop_release_r20.py`, pixel-identical left 3,480 columns). Hero: `--hero` / HERO_PNG (default `poster_inputs/HERO_R13.png`).
8. `poster/audit_r20.py work/box_r11`: physical-PDF layout audit + gate predicates (193 in this copy; 196 when the earlier-revision reference PDFs are supplied with `POSTER_REF_DIR`, which adds the three r17/r19/r20-v1 comparison gates), including decoding both QR codes from the rendered PDFs with `poster/qr_decode.py` (needs `opencv-python-headless`; set QR_PY to a python that has it), then `tools/check_r11_lock.py` (every re-derived design field and every r11 number matches the locked record `out/R11_CANDIDATE.json`).

### Expected results
| Output | Expected |
|---|---|
| `sweep/SWEEP_INPUTS.json` sha256 | `94e1b3ae978b83fe5fc0b3d87bf8ccbe9b277d4d44fdd523403ec328db7cc12b` |
| `sweep/gpu_core.py` sha256 | `cb07f775bcc65c2a82972119225fbe82e3c3319804f8ede45c30def3b5b8bb13` |
| Frozen control (box CPU) | hard 3095, design 2398, index 1037888, 3020.886551 kg |
| r11 sweep (box CPU = GB10 CPU = GB10 CUDA) | hard 3048, design 2347, index 1037888 (140 panels, 7 tubes, 0.2587 mm fin, 861.753 m² array), screen mass 3024.601123 kg |
| r11 scenarios | P(inlet ≤ 393 K) = 0.4166250228881836 (41.66%) |
| Native satellite mass / reserve | 3026.214467 kg / 7.213566 t; peak available 249.913752 kW (BOL) |
| `out/POSTER_NUMBERS_R11.json` sha256 | `c7b01951725b2bc4678bbe0d04e40c12de019688858ac22427a42c1c604cfff2` |
| `out/R11_CANDIDATE.json` (locked r11 record, committed) | sha256 `a3bd7328425085fa29ceb053c437740ccad7150112a57fbf6c34c5d15010374b`; `tools/check_r11_lock.py` prints `r11 lock OK`. The hash itself is reproduced by `../../gtc_august_lock/repro/run_all.sh` (this register has more entries for the r20 poster) |
| `out/poster_r20/GATES_R20.json` | passed, 193/193 predicates in this copy (196/196 with `POSTER_REF_DIR`) |
| Poster PDF sha256 (r20 PUBLIC) | `85c3f9f70ae72b38d3ee6692ea79dcf19f8d23788f50e7e0af44250475b4459b`, only with the approved identity strings and repo URL (they change the PDF bytes) |

Native outputs are numerically identical (absolute 1e-9 + relative 1e-12) to the independent t773 corrected-MPG40 recheck (`tools/numcompare.py`).

## Tier 2: GB10 CUDA (about 10 minutes, mostly first-time kernel compilation)
```bash
PY=/path/to/gb10/python OUT=$PWD/gb10_out CPU_CORE=5 sweep/run_gb10_r11.sh
```
This runs the frozen-control sweep on CUDA, then the r11 sweep, scenarios and warp.Tape on CUDA, the same sweep and scenarios on
one X925 core (`taskset`), and three controlled benchmark repetitions (`run_benchmark.py`, median reported). Committed results are
in `gb10_out/`. The poster's timing numbers are medians of `gb10_out/r11/BENCH_{GPU,CPU}_{1,2,3}.json` (0.2136 s / 7.0201 s → 32.9×).
Timing values vary run to run by about 1%; counts, selection and scenario fractions are exact.

## Tier 3: reused-scope evidence (rerun on GB10 in the t773 recheck; scripts and inputs committed, not re-run by `run_all.sh`)
| Poster number | Evidence | Command |
|---|---|---|
| PhysicsNeMo 9.3e-5, 384/128 | `evidence/fin/FIN_RECHECK_SUMMARY.json` | unpack `fin_inputs.tgz`, `WORK=<dir> PY=<python> evidence/fin/run_fin.sh` (PhysicsNeMo 26.08 container) |
| 36 hinges lock (31 here + 5 width hinges in `poster_inputs/wfold_newton_tw120_dt0.01.json`), 0.0061° | `evidence/newton/NEWTON_RECHECK_SUMMARY.json` | unpack `newton_inputs.tgz`, `evidence/newton/run_newton.sh` (Newton 1.7.0, Warp 1.18.0) |
| ≈46 kg frame (45.70 kg), 35 Hz | `evidence/frame/FRAME_CONTROL_REPRODUCTION.json` | `CCX=<CalculiX 2.21 ccx> python evidence/frame/frame_control.py` (decks in `evidence/frame/decks/`) |
| 128–153 Hz, ≈139 Hz | `evidence/panel/PANEL_RECHECK_SUMMARY.json` | unpack `panel_inputs.tgz`, `evidence/panel/run_panel.sh` (finest L3 139.05 Hz reused) |
| 12 coworking days | `evidence/effort/EFFORT_UPDATE_R17.json` | record of the study calendar, not re-measurable (`HISTORICAL_TIME_RECHECK.json` is the earlier record) |

## What changed versus the August/r10 inputs, and why
1. `native/`: absolute paths replaced by `$GTCFC_ROOT`; recorded source-hash keys made root-relative. No numerical effect (verified).
2. `sweep/make_sweep_inputs.py`: pumps read from the native power check instead of hard-coded frozen constants; `peak_power_acceptance_W = 249900`.
3. `sweep/gpu_core.py`: the array grid is anchored at the fixed August array (`packing_verified_max_array_m2`) and peak
   payload power is an explicit acceptance test, `array × 319.7 W/m² × 0.92 − 2 kW − pump ≥ 249.9 kW` (the existing 1e-6 m² packing
   tolerance is carried over in watts). With the frozen inputs and a 250.000 kW threshold this reproduces the frozen search exactly.
4. `sweep/run_sweep_case.sh`: writes `SELECTED.json` from the sweep when a box run needs it for the scenario stage. The GB10 runs already had it.
5. Hygiene: user paths removed from logs and evidence; identity strings come from environment variables and appear only in the PDF.
