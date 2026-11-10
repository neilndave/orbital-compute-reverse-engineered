# GTC poster r20: orbital data center satellite, AI agent + GPU simulation

`GTC_POSTER_R20.pdf` is the GTC poster (43 × 24 in, one page, PUBLIC build). It is the r20 revision of the August design
study in `../gtc_august_lock/` (locked r11 canonical numbers; no design numbers changed after r11).

PDF sha256: `85c3f9f70ae72b38d3ee6692ea79dcf19f8d23788f50e7e0af44250475b4459b`

## What is on the poster
- **Title:** "Cooling and Launching Orbital Data Centers: Concept to Architecture in 12 Days".
- **Problem / Why it matters:** published per-satellite targets (250 kW peak / 175 kW average, 75 kW per ton) and a 100 t launch imply 30 satellites; 12 coworking days from concept to a chosen mechanical and thermal architecture (boxed).
- **Design architecture:** one Vera Rubin NVL72 (72 GPUs + 36 CPUs) per satellite, 3,026 kg, 140 radiator panels, 862 m² array, 30 per 100 t launch; 600 km dawn-dusk sun-synchronous orbit; steady-state thermal results only.
- **Panel 1, Warp:** 1.81M-design radiator search (3,048 meet every hard limit; lightest with 1 K extra margin chosen) and 1.05M what-if runs over 14 assumed input ranges; the hard limits and the four searched variables are listed under the chart.
- **Panel 2, GB10:** same fp64 Warp code on the GB10 Grace Blackwell GPU (Warp kernels on CUDA), one CPU core and all 20 CPU cores (32.9× and 2.35× on the search; levels off at 32–33× from about 260,000 designs).
- **Panel 3, PhysicsNeMo / Warp:** learned fin-efficiency model checked on 128 held-out fins (max |Δη| = 9.3e-5); the chosen design's fins were re-solved with Warp; a Warp autodiff optimizer comes within 0.65% of the search's lightest radiator (local check).
- **Panel 4, Newton / Warp:** unfold sequence of one solar wing and one radiator column (36 representative hinges, all lock); Warp re-solves all 21 solar-array hinges within 0.0061°.

## Contents
| Path | What it holds |
|---|---|
| `GTC_POSTER_R20.pdf` | The poster (PUBLIC build). The only PDF in this folder. |
| `CHANGES.md` | What changed from r11 to r20. |
| `checks/GATES_R20.json` | Gate predicates from the delivered build: 196/196 passed. |
| `checks/LAYOUT_R20_AUDIT.json`, `checks/LAYOUT_R20_MPL_AUDIT.json` | Physical-PDF and matplotlib layout audits (margins, minimum 24 pt text, 300 dpi images, overlaps, NVIDIA content share). |
| `checks/POSTER_PDF_PUBLIC_TRACE.json` | All printed text and the hashes of the generator, numbers and chart inputs. |
| `checks/POSTER_NUMBERS_R11.json` | Every printed number with its source file, key path and raw value. |
| `figs/POSTER_R20_PREVIEW.png` | 100 dpi preview. |
| `repro/` | Everything needed to regenerate the numbers, the poster and the gates. See `repro/REPLICATE.md`. |

## Rebuild the poster
From `repro/` (see `repro/REPLICATE.md` for environments):
```bash
export R11_ROOT=$PWD POSTER_LAYOUT=A POSTER_AUTHOR='<approved author>' POSTER_ASSISTANT='<approved assistant>' REPO_URL='https://github.com/<owner>/<repo>'
python poster/make_poster_r20.py --public --release poster_inputs/RELEASE_R11_K712_4K_CROP_fixed_r20right.png --repo-url "$REPO_URL"
QR_PY=<python with opencv> python poster/audit_r20.py work/box_r11   # work/box_r11 comes from run_all.sh step 4
```
With the approved identity strings and repo URL the PUBLIC PDF is byte-identical to `GTC_POSTER_R20.pdf` (checked on a clean copy).
The audit in this copy runs 193 predicates; the three that compare against earlier unpublished revisions (r17, r19, r20 v1) run only when those PDFs are supplied with `POSTER_REF_DIR`.

## Limitations
This is a simulation study from public information, not flight qualification.
- Peak 250 kW holds at beginning of life only (249.9 kW available).
- Thermal results are steady state. Rubin GPU/HBM temperatures are estimates with an assumed cold-plate resistance; at the 250 kW peak they exceed the 370 K target and 378 K HBM limit, and detailed engineering is needed.
- What-if ranges are engineering assumptions, not measured probabilities.
- Deployment is a rigid-body Newton simulation with assumed hinge parameters (one wing and one radiator column), not a hardware test.
- The release animation is kinematic with assumed parameters; the satellite render is illustrative and contrast enhanced.

Independent study from public information; not affiliated with or endorsed by SpaceX.
LICENSE (Apache-2.0) applies to original work only; see `CREDITS.md` for third-party terms.
