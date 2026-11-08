"""Generator for THERMAL_INPUTS_SPIN1.json (spin1 wrote this file by hand-run code): recharge PMAD heat from POWER_SPIN1 (30-min battery) and the
header-protected view multiplier 1 - incremental blockage of the ledger-routing N<=1 header screen (MMOD_GRID_SPIN1)."""
import json
P = json.load(open("POWER_SPIN1.json")); G = json.load(open("MMOD_GRID_SPIN1.json"))
out = {nm: dict(recharge_heat_W=P["cases"][nm]["battery_table"]["30min"]["main_radiator_extra_heat_W_during_recharge"],
                header_protect_F_scale=1.0 - G["cases"][nm]["ledger"]["min_mass_N<=1.0"]["blockage_incremental_frac"]) for nm in ("June", "August")}
json.dump(out, open("THERMAL_INPUTS_SPIN1.json", "w"), indent=1); print(out)
