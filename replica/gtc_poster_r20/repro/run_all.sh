#!/bin/bash
# r20 (final GTC poster): make_poster_r20.py + audit_r20.py; release still = poster_inputs/RELEASE_R11_K712_4K_CROP_fixed_r20right.png (tools/crop_release_r20.py); YOUTUBE_URL overrides the built-in playlist URL
# Panel 4 plots all 36 modeled hinges; one source + disclaimer footnote line. Layout A = release frame + labelled hero
# (the only layout in this copy; the old layout-B header cut-out image was removed). The audit decodes both QR codes with OpenCV: QR_PY = a python with opencv-python-headless (default python3).
# r11 end-to-end replication on any Linux x86_64/aarch64 box (CPU only). GB10 CUDA results are committed in gb10_out/
# (re-run them with sweep/run_gb10_r11.sh on a GB10); this script re-derives everything else and checks box-vs-GB10 identity.
# Env: PY_NATIVE (python with native_requirements.txt), PY_POSTER (python with poster_requirements.txt),
#      POSTER_AUTHOR / POSTER_ASSISTANT / REPO_URL (approved identity strings, PDF only).
set -euo pipefail
export R11_ROOT=$(cd "$(dirname "$0")" && pwd); cd "$R11_ROOT"
PYN=${PY_NATIVE:-python3}; PYP=${PY_POSTER:-python3}; REPO_URL=${REPO_URL:-https://github.com/OWNER/REPOSITORY}; export REPO_URL
: "${POSTER_AUTHOR:?set POSTER_AUTHOR}" "${POSTER_ASSISTANT:?set POSTER_ASSISTANT}"; export POSTER_AUTHOR POSTER_ASSISTANT
echo "[1/8] native corrected-MPG40 chain";            PY=$PYN native/run_r11_native.sh
echo "[2/8] sweep inputs from native outputs";       (cd sweep && GTCFC_ROOT=$R11_ROOT/native PYTHONDONTWRITEBYTECODE=1 $PYN make_sweep_inputs.py)
echo "[3/8] box CPU frozen-control sweep";           PY=$PYN sweep/run_sweep_case.sh sweep/FROZEN_CONTROL_SWEEP_INPUTS.json work/box_frozen_control cpu BOX_CPU sweep
echo "[4/8] box CPU r11 sweep + scenarios";          PY=$PYN sweep/run_sweep_case.sh sweep/SWEEP_INPUTS.json work/box_r11 cpu BOX_CPU sweep mc
echo "[5/8] device thermal sensitivity";             $PYN evidence/device/device_thermal_recheck.py > /dev/null
echo "[6/8] poster numbers + r10/r11 trace + speed numbers"; $PYN numbers/derive_numbers.py gb10_out && $PYN numbers/make_number_trace.py && $PYN speed/derive_speed.py >/dev/null
echo "[7/8] poster PDFs (r20, layout ${POSTER_LAYOUT:-A})";  REL=${RELEASE_PNG:-poster_inputs/RELEASE_R11_K712_4K_CROP_fixed_r20right.png}; YT=(${YOUTUBE_URL:+--youtube-url "$YOUTUBE_URL"}); $PYP poster/make_poster_r20.py --release "$REL" --repo-url "$REPO_URL" "${YT[@]}" && $PYP poster/make_poster_r20.py --public --release "$REL" --repo-url "$REPO_URL" "${YT[@]}"
echo "[8/8] physical-PDF audit + gates (r20)";       $PYP poster/audit_r20.py work/box_r11
$PYN tools/check_r11_lock.py   # design numbers = locked r11 record (out/R11_CANDIDATE.json, a3bd7328...); the hash itself reproduces in ../../gtc_august_lock/repro
