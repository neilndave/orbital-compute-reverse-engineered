"""Final-candidate orbit facts for the baseline orbit (600 km circular dawn-dusk SSO, LTAN 06:00) from the inherited eclipse model outputs
(eclipse_model.py: skyfield + JPL DE421 Sun, J2 SSO, conical shadow).  Replaces the 550-km t590 values (21.66 / 17.41 min, 1514 /yr) that spin1
had inherited from the t596 freeze work."""
import csv, json, math
R0 = "/tmp/gtcfc_root/inputs/ai1_replica/eclipse"
row = [r for r in csv.DictReader(open(R0 + "/eclipse_grid.csv")) if int(float(r["h_km"])) == 600 and abs(float(r["ltan_h"]) - 6.0) < 1e-6][0]
daily = json.load(open(R0 + "/eclipse_daily.json"))["600_6.0"]; ecl_days = [d for d in daily if d["shadow_min_day"] > 0]
n_ecl = int(float(row["n_ecl_orbits_shadow"])); shadow_h = sum(d["shadow_min_day"] for d in daily) / 60.0
out = dict(h_km=600, ltan_h=6.0, inc_deg=float(row["inc_deg"]), T_orb_min=float(row["T_orb_min"]), orbits_per_year=float(row["n_orbits_year"]),
           season=f'{row["season_start"]} - {row["season_end"]}', season_days=int(float(row["season_days"])), max_shadow_min=float(row["max_shadow_min"]),
           eclipsed_orbits_per_year=n_ecl, shadow_hours_per_year=shadow_h, mean_shadow_min_when_eclipsed=shadow_h * 60.0 / n_ecl,
           beta_abs_range_on_eclipse_days_deg=[min(d["beta_min_abs"] for d in ecl_days), max(d["beta_max_abs"] for d in ecl_days)],
           beta_star_deg=math.degrees(math.asin(6378.137 / (6378.137 + 600.0))), sunlit_frac_equiv=float(row["sunlit_frac_equiv"]),
           superseded_550km_t590=dict(max_min=21.66, mean_min=17.41, eclipsed_orbits_per_year=1514, note="t590 count was at 550 km; kept only as a conservative sensitivity"))
json.dump(out, open("ECLIPSE_600KM.json", "w"), indent=1); print(json.dumps(out))
