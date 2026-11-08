# August orbital-compute GPU study — locked application

Public canonical SHA256 `a64dc61e2347373c0e1f63fea683aca6dee7bc4a25d6b26c014aef76611a550f`. Source verification canonical SHA256 `f02f82201c45c9b1c98b1052f8adc795f47c441e642059bd450b288b5de88846`. These are DIFFERENT hashes: this tree is an explicit August-only projection, not the private construction history. The author retains responsibility. Work ongoing; no qualified flight-system claim.

## What can be reproduced

- `tools/SWEEP_INPUTS.json` is the frozen reduced-model configuration. `gpu_core.py`/`run_tools.py` reproduce discrete sizing, stress Monte Carlo and differentiable optimization using the supplied held-out-validated surrogate.
- `make_fin_dataset.py`, `train_surrogate.py` and `fin_al_benchmark.py` reproduce native labels, surrogate training and selected finite-volume fin tables (optional CUDA/container environment). Setup/training and warm timing scopes are separate; CPU backend single-threaded.
- `model/native/run_native_parity.py` independently re-solves the final adopted thermal roots, energy/mass rollup and exact array view on CUDA from frozen native operating inputs.
- `model/fea/run_panel_fea.py` regenerates the circular-tube supported local-panel mesh and invokes an externally installed CalculiX; refined solves can take hours. No raw stress/output bulk or solver binary is included.
- `reproduce.py` checks every frozen-file hash, independent arithmetic and optional CPU/GPU study parity in a temporary copy. This verifies the published point/tools; the private construction/history pipeline is intentionally not represented as an included public replay.

## Model and limitations

30×250kW =7.5MW installed peak;175kW nominal(sunlit), not an achieved annual average.100t budget includes2t dispenser. 31.25kg safe-mode pack; compute pauses in eclipse.140-panel Al6061-T6 radiator. Coating emissivity0.92 is the design spec(BOL).23-mm seams consume1.495% gross area;319.7W/m² gross implies324.55W/m² active surface, an unqualified cell-fill assumption. No unqualified mass/optical credit.

Component-envelope stow and representative rigid deployment/local strength are screening results. Connected stow, hardware, actual launch loads, flexible structures, pressure/life, header MMOD, EOL, full-peak chips and annual-average requirements remain OPEN. Freeze reference FAIL is owner-waived with full actual hardware mass charged. No general energy or end-to-end GPU speedup claim.

## Run

Install Python, NumPy, SciPy, Matplotlib, CoolProp and Warp matching the measured versions where possible. Optional training requires the specified PhysicsNeMo container. `python reproduce.py` validates frozen artifacts and arithmetic; `python reproduce.py --cpu-studies` additionally replays the three Warp study stages. `--cuda-studies` requires CUDA. Run the native CUDA thermal verifier separately from its folder.

`GTC_POSTER_DRAFT.pdf` is the author-attributed final-design draft with the finished 4K Isaac Sim RTX Earth-background hero. LICENSE applies to original work only; CREDITS covers external dependencies. No logo/endorsement is implied.

## Workflow and process provenance

The poster presents one engineer plus a closed-product AI agent orchestrating open Apache-2.0 analysis, GPU studies and native checks, with human approval. The agent and Isaac Sim renderer are proprietary. `checks/PROCESS_METRICS.json` and its separate SHA256 sidecar document the approximate calendar span, reduced-model grid count, bounded uncertainty scenarios and two release-audit gates; none is a measured labor saving or productivity multiplier. The approved author attribution and repository link appear only in the poster PDF.
