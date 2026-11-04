# Replica render environment (Jun/Aug). Source from inside the overlay: source experiments/poster/fleet_replica_env.sh
# = repo v3 timeline + hinge-stub trim + release camera + t360 hold camera.  NOT set on purpose: FLEET_PACK / FLEET_LAYOUT / FLEET_LSCALE (A6L-specific; the overlay carries the replica pack+layout), FLEET_HIDE13.
_D="$(dirname "${BASH_SOURCE[0]}")"
source "$_D/fleet_v3_env_T45.sh"; unset FLEET_HIDE13
source "$_D/fleet_cam_t360_env_T45.sh"
# width-fold duration: Newton wfold timing if the file exists (apply_wfold_timing.py writes it), else the 14 s PLACEHOLDER
export FLEET_TAU_W="${FLEET_TAU_W:-14.0}"
[ -n "${WFOLD_ENV:-}" ] && [ -f "$WFOLD_ENV" ] && source "$WFOLD_ENV"
echo "replica env: FLEET_TAU_W=$FLEET_TAU_W (14.0 = PLACEHOLDER until Newton wfold results are applied)"
