"""Writes ../NVIDIA_TOOLS_INVENTORY.{json,md} for the v2 (all-aluminium) baseline from NVIDIA_METRICS.json; replaces the inherited K13D wording."""
import json, os
H = os.path.dirname(os.path.abspath(__file__)); NM = json.load(open(os.path.join(H, "NVIDIA_METRICS.json"))); hl = NM["headline"]; T = NM["tools"]
fmt = lambda v, s: format(v, s)
SG = json.load(open(os.path.join(H, "SURROGATE_V2.json")))
tools = [
 dict(tool="NVIDIA Warp 1.18.0 fp64 (GB10 cuda:0)", run="v2 fin table AL6061_L26_t0p225 (Al 6061-T6, 26 mm / 0.225 mm, integral/brazed, no bondline): 585 Newton+PCG solves, nx 320 x ny 8",
      status="COMPLETED", final_numbers_depend=True, produced="every coolant supply/inlet, GPU and HBM temperature in GTC_FINAL_CANDIDATE.json (v2); radiator rises; mass flow (area factor 1.0)",
      metrics=f"table wall GPU {hl['e2e_table_gpu_s']:.0f} s vs Grace CPU {hl['e2e_table_grace_cpu_s']:.0f} s (same Warp code); max |d eta| vs vendored {hl['e2e_table_max_d_eta']:.1e}; production-grid error vs independent 1-D BVP {hl['val_prod_err_vs_BVP']:.1e}, observed order {hl['val_order']:.2f}, energy residual <= {hl['val_energy_residual_max']:.0e}",
      evidence=["pipeline/inputs/ai1_replica/gb10_final_al/table_AL6061_L26_t0p225.json", "nvidia_metrics/VALIDATE_GB10.json", "nvidia_metrics/E2E_GB10/e2e.log"]),
 dict(tool="NVIDIA Warp 1.18.0 fp64 (GB10 cuda:0)", run="v2 final parity (gb10_final_parity.py, 10 rows: final T2/T1, baseline T0 nominal/peak, T4 sensitivity x 2 months)", status=f"COMPLETED, PASS (max abs diff {hl['parity_max_abs']:.2e})",
      final_numbers_depend="verification", produced="independent GPU re-solve of fin-table interpolation, thermal root, energy balance and mass ledger of the v2 config", evidence=["GB10_FINAL_PARITY_RESULT.json"]),
 dict(tool="NVIDIA Warp 1.18.0 fp64 (GB10 cuda:0)", run="v2 thermal-root Monte Carlo benchmark (parity kernel on 1e3-1e7 perturbed draws)", status="COMPLETED (benchmark)", final_numbers_depend=False,
      produced="GPU-vs-CPU throughput; not a design number", metrics=f"{hl['mc_gpu_draws_per_s']/1e6:.0f} M draws/s at {hl['mc_N_max']:.0e}; {hl['mc_speedup_vs_numpy_grace_at_Nmax']:.0f}x NumPy on Grace; {hl['mc_speedup_vs_warp_grace_1e6']:.0f}x the same Warp code on Grace (1e6); max |diff| {hl['mc_max_abs_diff_gpu_vs_numpy']:.1e}",
      evidence=["nvidia_metrics/BENCH_GB10.json", "nvidia_metrics/NVIDIA_METRICS.json"]),
 dict(tool="NVIDIA Warp CUDA (GB10)", run="Al fin screen (fin_al_v2.py, screen_al_fine.json): Al/K13D cell areal ratio", status="COMPLETED", final_numbers_depend=True, produced="radiator mass line 141.89/236.45 kg (x 1.16037 of the K13D wet line)",
      evidence=["pipeline/inputs/ai1_replica/gb10_final_al/screen_al_fine.json"]),
 dict(tool="NVIDIA Warp FEA (CG beam/frame) + warp.fem", run="t479/t494 carbon frame (GB10)", status="COMPLETED (inherited; frame unchanged in v2)", final_numbers_depend="inherited mass line only",
      produced=T["warp_fea_frame"]["what"], evidence=[T["warp_fea_frame"]["source"]]),
 dict(tool="NVIDIA Newton 1.7.0 (+ Warp articulated reference)", run="fold-latch deployment dynamics, 4 cases (geometry identical in v2)", status="COMPLETED (bounded subsystems)", final_numbers_depend=False,
      produced=f"peak hinge torque {T['newton_deployment']['peak_hinge_torque_max_Nm']} N.m (A4_C1); Newton vs Warp within {T['newton_deployment']['newton_vs_warp_max_rel_diff_pct']} %; deployment hardware stays an allocation",
      metrics=f"Newton {T['newton_deployment']['newton_wall_s_per_case_min']}-{T['newton_deployment']['newton_wall_s_per_case_max']} s per case vs ~{T['newton_deployment']['warp_reference_wall_s_per_case']} s Warp reference", evidence=[T["newton_deployment"]["source"]]),
 dict(tool="NVIDIA Omniverse / Isaac Sim 6.0 RTX (GB10)", run="R1 (Aug 30-sat release + unfold, 960 fr) and R2 (Jun/Aug, 2 x 476 fr)", status="COMPLETED (visualisation; radiator geometry unchanged by the Al switch)", final_numbers_depend=False,
      produced="poster figures/videos", metrics=f"R1 {T['omniverse_rtx_R1']['s_per_frame']} s/frame at {T['omniverse_rtx_R1']['mean_gpu_W']} W mean GPU; R2 {T['omniverse_rtx_R2']['s_per_frame']} s/frame", evidence=[T["omniverse_rtx_R1"]["source"], T["omniverse_rtx_R2"]["source"]]),
 dict(tool="NVIDIA PhysicsNeMo (GB10 container)", run="t538 surrogate over an unadopted design space", status="EXPLORATORY", final_numbers_depend=False, produced="nothing in v2", metrics=f"{T['physicsnemo']['wall_s']} s on GB10", evidence=[T["physicsnemo"]["source"]]),
 dict(tool="NVIDIA PhysicsNeMo 2.2.0 (GB10 container)", run="v2 local Al 6061 fin-efficiency surrogate (FullyConnected 4x64, supervised; not a PINN)", status="COMPLETED (supporting poster panel; no baseline number depends on it)", final_numbers_depend=False,
      produced=f"held-out heat error max {SG['metrics']['test']['q_cell_W_m2']['max_relative_pct']:.4f} %; fixed-rise GPU-temp closure max {SG['thermal']['all']['max_abs']:.4f} K; {SG['metrics']['timing']['cuda']['100000']['speedup']:.1f}x vs batched Warp fp64 at 100k; 100k-design screen {SG['screening']['June']['production_interface_median_s']*1000:.0f} ms; degree-4 polynomial control also accurate (no neural-necessity claim)",
      metrics=f"training {SG['metrics']['training_s']:.1f} s on GB10", evidence=["nvidia_metrics/SURROGATE_V2.json", "gtc_surrogate_v2/REPORT.md"]),
 dict(tool="CPU (not NVIDIA): numpy/scipy/CoolProp", run="full v2 pipeline s00-s15 (box x86_64 and GB10 aarch64)", status=f"COMPLETED, canonical hash match: {hl['e2e_pipeline_sha_match']}", final_numbers_depend=True,
      produced="all mass, power/battery, MMOD, freeze/restart transient, eclipse and downtime numbers", metrics=f"wall {hl['e2e_pipeline_gb10_s']:.0f} s GB10 / {hl['e2e_pipeline_box_s']:.0f} s box (median of 3)", evidence=["RESULTS_CANONICAL.sha256", "nvidia_metrics/E2E_GB10/e2e.log", "nvidia_metrics/E2E_BOX/e2e.log"])]
json.dump(dict(configuration_id=NM["configuration_id"], tools=tools, superseded="K13D70 bonded-fin wording (F3_L40_t0p5 table, 0.9913 area factor, bondline) applies only to prior_candidate_k13d/"), open(os.path.join(H, "..", "NVIDIA_TOOLS_INVENTORY.json"), "w"), indent=1)
md = ["# NVIDIA tool inventory (GTC FINAL v2, all-aluminium radiator)", "", f"Configuration `{NM['configuration_id']}`. Metrics: `nvidia_metrics/NVIDIA_METRICS.json`.", "", "| Tool | Run | Status | Feeds final numbers? | Produced | Measured | Evidence |", "|---|---|---|---|---|---|---|"]
for t in tools: md.append("| " + " | ".join([t["tool"], t["run"], t["status"], str(t["final_numbers_depend"]), t["produced"], t.get("metrics", ""), "<br>".join(f"`{e}`" for e in t["evidence"])]) + " |")
md += ["", "K13D70 bonded-fin wording (F3_L40_t0p5 table, 0.9913 area factor, bondline) now applies only to the prior candidate in `prior_candidate_k13d/`."]
open(os.path.join(H, "..", "NVIDIA_TOOLS_INVENTORY.md"), "w").write("\n".join(md) + "\n"); print("inventory ok")
