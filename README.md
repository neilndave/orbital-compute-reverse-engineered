# Orbital Compute, Reverse-Engineered

**Status: GTC poster r20, "Cooling and Launching Orbital Data Centers: Concept to Architecture in 12 Days".** The poster and everything needed to rebuild it are in [`replica/gtc_poster_r20/`](replica/gtc_poster_r20/README.md).
Its design numbers come from the locked r11 August design in [`replica/gtc_august_lock/`](replica/gtc_august_lock/README.md).
Where older documents in `docs/` or `replica/` differ, those two folders win.

## The study
Published targets for an orbital data center satellite (250 kW peak, 175 kW, 75 kW per ton; source below) and an assumed 100 t launch imply
30 satellites per launch. Working only from public information, an engineer and an AI agent sized one satellite carrying one
NVIDIA Vera Rubin NVL72 (72 GPUs + 36 CPUs) and checked the chosen architecture with NVIDIA tools on one GB10 desktop:
- radiator design search (1.81M designs) and 1.05M what-if runs in **NVIDIA Warp**, run as CUDA kernels on the GB10 Grace Blackwell GPU and timed against its CPU cores;
- a **PhysicsNeMo** learned model of radiator fin efficiency, checked against Warp solves;
- solar-wing and radiator unfold in **NVIDIA Newton**, with a Warp re-solve;
- illustrative renders in **Omniverse Isaac Sim RTX**; CalculiX for the rack frame and stowed panels.

It is a simulation study and a basis for detailed design, not flight qualification. Every limitation is listed in the poster folder README.

## What's in the repo
| Path | Contents |
|---|---|
| `replica/gtc_poster_r20/` | GTC poster r20 (PDF), gates and layout audits, and the full `repro/` tree (generator, audit, inputs, numbers) |
| `replica/gtc_august_lock/` | Locked r11 August design: canonical record, number trace and the r11 repro (the r11 poster was removed; r20 is the only poster) |
| `replica/gtc_final/`, `replica/gb10_*`, other `replica/` scripts | Earlier configurations and the design history (superseded where they differ) |
| `docs/` | Calibration notes and the engineering log from the earlier phases (historical) |
| `vendor/same_rack/` | Modules and render-pipeline scripts reused from a sibling project (provenance in `FILES.txt`) |
| `scripts/get_blue_marble.sh` | Re-downloads the NASA Blue Marble texture used by the renders |
| `FILES.txt` | Register of every tracked file |

## Reproduce
See `replica/gtc_poster_r20/repro/REPLICATE.md`: Tier 1 runs on any Linux box (CPU only); Tier 2 re-runs the GPU work on an NVIDIA GB10.

## Source and disclaimer
Targets: https://www.spacex.com/spacexai/starmind. Independent study from public information; not affiliated with or endorsed by SpaceX.
Earth imagery: NASA Visible Earth / Blue Marble; use of NASA imagery does not imply NASA endorsement. See `CREDITS.md`.

## Licence
Apache-2.0. See `LICENSE`.
