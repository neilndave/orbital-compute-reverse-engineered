#!/usr/bin/env bash
# Build a throw-away repo-shaped overlay tree so the UNMODIFIED repo poster scripts (fleet_kin_T45.py etc.) read the replica layout/pack.
# usage: make_overlay.sh <Jun|Aug> <REPO_ROOT> <OUT_DIR>      (REPO_ROOT is only read; nothing in it is changed)
set -euo pipefail
B=${1:?Jun|Aug}; REPO=${2:?repo root}; OUT=${3:?out dir}; HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$OUT/experiments/poster" "$OUT/results/fleet" "$OUT/results/phase2_T45" "$OUT/src"
cp "$REPO"/experiments/poster/*.py "$OUT/experiments/poster/"            # copies, not symlinks: the scripts resolve ROOT from their own real path
cp "$REPO"/experiments/poster/*.sh "$OUT/experiments/poster/"
mkdir -p "$OUT/results/omniverse"; cp -r "$REPO"/results/omniverse/. "$OUT/results/omniverse/"     # render assets (earth, hull, textures); the render script resolves ROOT from its own path
cp -r "$REPO"/results/phase2_T45/. "$OUT/results/phase2_T45/"
mkdir -p "$OUT/experiments/newton_array" "$OUT/results/newton_array"; cp "$REPO"/experiments/newton_array/*.py "$OUT/experiments/newton_array/"   # run_array.py writes results relative to itself -> overlay, repo stays read-only
mkdir -p "$OUT/experiments/newton_deploy" "$OUT/results/newton_deploy"; cp "$REPO"/experiments/newton_deploy/*.py "$OUT/experiments/newton_deploy/"   # [t441] run_array imports run_hinge
mkdir -p "$OUT/results/full3d" "$OUT/results/audit"; cp "$REPO"/results/full3d/*.json "$OUT/results/full3d/"; cp -r "$REPO"/results/audit/. "$OUT/results/audit/" 2>/dev/null || true   # [t441] run_array reads full3d/audit
for f in "$REPO"/results/fleet/*.json "$REPO"/results/fleet/*.npz; do cp "$f" "$OUT/results/fleet/"; done
cp "$HERE/scene/$B/fleet_layout_replica_$B.json" "$OUT/results/fleet/fleet_layout_T45.json"
cp "$HERE/scene/$B/fleet_pack_replica_$B.json"   "$OUT/results/fleet/fleet_pack_T45.json"
[ -d "$REPO/src" ] && cp -r "$REPO/src/." "$OUT/src/" || true
python3 "$HERE/adapt_scene.py" "$OUT" "$B"   # two-box body (equip bus + comp_pod), deployed geometry, clip scaling
python3 "$HERE/patch_fleet_kin.py" "$OUT"     # replica-aware fleet_kin + clearance checker (overlay copies only)
python3 "$HERE/patch_stage_plan.py" "$OUT"    # count-generic stage planner (overlay copy only)
python3 "$HERE/patch_release_dirs.py" "$OUT"   # outward release for 2-3 satellites per layer (overlay copy only)
cp "$HERE/scripts/fleet_replica_env.sh" "$OUT/experiments/poster/"
echo "overlay ready: $OUT  (layout+pack = replica $B, ESTIMATE)"
