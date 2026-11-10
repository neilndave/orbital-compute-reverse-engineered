# Credits and third-party terms

Original study scripts and data: Copyright 2026 the author, Apache-2.0 (`LICENSE`). This license does not relicense external software, NASA assets or linked documents. No solver, container or Omniverse binaries or proprietary assets are redistributed. No NVIDIA or SpaceX endorsement.

- NVIDIA Warp 1.18.0 (GB10 CUDA and CPU runs; 1.19.0 for CPU-only reproduction), NVIDIA Newton 1.7.0 and NVIDIA PhysicsNeMo 2.2.0: Apache-2.0 projects; https://github.com/NVIDIA/warp ; https://github.com/newton-physics/newton ; https://github.com/NVIDIA/physicsnemo .
- NGC PhysicsNeMo/PyTorch container: NVIDIA container and upstream component terms; https://catalog.ngc.nvidia.com/orgs/nvidia/teams/physicsnemo/containers/physicsnemo . Not redistributed; own trained weights and labels supplied.
- NVIDIA Omniverse Kit/RTX and Isaac Sim: NVIDIA license terms apply; https://docs.omniverse.nvidia.com and https://docs.isaacsim.omniverse.nvidia.com . No runtime binaries or assets redistributed. The poster includes an illustrative Isaac Sim RTX render (contrast enhanced; parameters in `repro/poster_inputs/HERO_R13_ENHANCE_PARAMS.json`).
- CalculiX 2.21: external GPLv2 solver (upstream license controls; no solver binary or source redistributed): https://www.calculix.de and https://www.dhondt.de .
- CoolProp 8.0.0: MIT; https://coolprop.org/ . High-temperature property clamp limitations remain explicit in the native records.
- Matplotlib, NumPy, SciPy, qrcode, PyMuPDF, OpenCV (QR decode check) and poppler-utils: their own open-source licenses.
- NASA Blue Marble: NASA Earth Observatory / Reto Stöckli; https://visibleearth.nasa.gov/images/73909 . Earth visual in the renders; NASA imagery-use terms apply; no endorsement.
- Published targets: https://www.spacex.com/spacexai/starmind (reference only; not SpaceX hardware or affiliation).
- AI-assisted analysis, code, checks and drafting; the author set the requirements, made the design decisions and retains responsibility for assumptions and claims.
