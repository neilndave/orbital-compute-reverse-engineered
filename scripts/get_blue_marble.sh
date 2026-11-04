#!/usr/bin/env bash
# Fallback: re-download the NASA Blue Marble Earth texture. Copies are already included in vendor/same_rack/results/omniverse/assets/.
# Source: NASA Visible Earth, "Blue Marble Next Generation w/ Topography and Bathymetry" (December 2004)
#   https://visibleearth.nasa.gov/images/73909/december-blue-marble-next-generation-w-topography-and-bathymetry
# Earth imagery: NASA Visible Earth / Blue Marble. Use of NASA imagery does not imply NASA endorsement.
# Writes the files the render scripts expect:
#   vendor/same_rack/results/omniverse/assets/bluemarble_8192.jpg (8192x4096) and bluemarble_2048.jpg
set -euo pipefail
URL="${BLUE_MARBLE_URL:-https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73909/world.topo.bathy.200412.3x21600x10800.jpg}"
DST="$(cd "$(dirname "$0")/.." && pwd)/vendor/same_rack/results/omniverse/assets"
if [ -s "$DST/bluemarble_8192.jpg" ] && [ -s "$DST/bluemarble_2048.jpg" ] && [ -z "${FORCE:-}" ]; then echo "Blue Marble textures already present in $DST (set FORCE=1 to re-download)"; exit 0; fi
mkdir -p "$DST"; TMP="$DST/bluemarble_src.jpg"
[ -s "$TMP" ] || curl -fL --retry 3 -o "$TMP" "$URL"
python3 - "$TMP" "$DST" <<'PY'
import sys; from PIL import Image
Image.MAX_IMAGE_PIXELS=None
im=Image.open(sys.argv[1]).convert("RGB")
for w in (8192,2048): im.resize((w,w//2),Image.LANCZOS).save(f"{sys.argv[2]}/bluemarble_{w}.jpg",quality=92)
PY
echo "Blue Marble textures written to $DST"
