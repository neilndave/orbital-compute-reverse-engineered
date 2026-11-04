#!/usr/bin/env bash
# RENDER 2 composition (both clips use ONE camera distance = same true scale; labels at y=64, below the caption band): Jun (left) and Aug (right) single-satellite unfold, same frame numbers, side by side.  usage: compose_render2.sh <JUN_FRAMES_DIR> <AUG_FRAMES_DIR> <out.mp4>
set -euo pipefail
J=${1:?}; A=${2:?}; O=${3:?}
ffmpeg -y -framerate 24 -start_number 340 -i "$J/f_%05d.png" -framerate 24 -start_number 340 -i "$A/f_%05d.png" \
  -filter_complex "[0:v]drawtext=text='June  J8_C1  (46 per Starship)':x=20:y=64:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.45:boxborderw=6[l];[1:v]drawtext=text='August  A4_C1  (30 per Starship)':x=20:y=64:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.45:boxborderw=6[r];[l][r]hstack=inputs=2" -c:v libx264 -crf 16 -pix_fmt yuv420p "$O"
