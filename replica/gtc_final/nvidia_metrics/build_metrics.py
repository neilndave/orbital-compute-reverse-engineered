"""Assemble NVIDIA_METRICS.json for the GTC FINAL v2 baseline from the raw harness outputs in this folder (no new numbers are invented here;
every derived value records its formula).  Raw inputs: BENCH_GB10.json (+ BENCH_GB10_SCIPY.json), BENCH_BOX_CPU.json (+ BENCH_BOX_SCIPY.json),
VALIDATE_GB10.json, VALIDATE_BOX_CPU.json, E2E_GB10/e2e.log, E2E_BOX/e2e.log, ../GB10_FINAL_PARITY_RESULT.json, ../GTC_FINAL_CANDIDATE.json,
HISTORICAL.json (earlier GB10 runs on geometry-identical configs, with source paths)."""
import json, os, re, hashlib, statistics
H = os.path.dirname(os.path.abspath(__file__)); J = lambda p: json.load(open(os.path.join(H, p)))
sha = lambda p: hashlib.sha256(open(os.path.join(H, p), "rb").read()).hexdigest()
G = J("BENCH_GB10.json"); B = J("BENCH_BOX_CPU.json"); GS = J("BENCH_GB10_SCIPY.json"); BS = J("BENCH_BOX_SCIPY.json")
VG = J("VALIDATE_GB10.json"); VB = J("VALIDATE_BOX_CPU.json"); HI = J("HISTORICAL.json"); P = J("../GB10_FINAL_PARITY_RESULT.json"); C = J("../GTC_FINAL_CANDIDATE.json")
def e2e(path):
    d = dict(pipeline_wall_s=[], table={}, parity_wall_s=[]); txt = open(os.path.join(H, path)).read()
    for m in re.finditer(r"E1 run \d rc (\d+) wall_s ([\d.]+) files (\d+) sha256 (\w+)", txt): d["pipeline_wall_s"].append(float(m.group(2))); d["pipeline_sha256"] = m.group(4); d["pipeline_rc"] = int(m.group(1))
    for m in re.finditer(r"E3 run \d wall_s ([\d.]+)", txt): d["parity_wall_s"].append(float(m.group(1)))
    for m in re.finditer(r"E2 (\w+) wall_s ([\d.]+) device (\S+) solver_wall_s ([\d.]+) max_abs_d_eta_vs_vendored (\S+)", txt):
        d["table"][m.group(1)] = dict(process_wall_s=float(m.group(2)), device=m.group(3), solver_wall_s=float(m.group(4)), max_abs_d_eta_vs_vendored=float(m.group(5)), solves=585, grid="320x8")
    d["pipeline_median_s"] = statistics.median(d["pipeline_wall_s"]) if d["pipeline_wall_s"] else None
    d["parity_median_s"] = statistics.median(d["parity_wall_s"]) if d["parity_wall_s"] else None
    d["host_line"] = txt.split("\n")[0]; return d
EG = e2e("E2E_GB10/e2e.log"); EB = e2e("E2E_BOX/e2e.log")
def merge_fin(gpu_run, cpu_run, gs, bs):
    rows = []
    sG = {r["cells"]: r["scipy_direct_cpu"] for r in gs["B1_fin"]}; sB = {r["cells"]: r["scipy_direct_cpu"] for r in bs["B1_fin"]}; bc = {r["cells"]: r for r in cpu_run["B1_fin"]}
    for r in gpu_run["B1_fin"]:
        c = r["cells"]; row = dict(nx=r["nx"], ny=r["ny"], cells=c, gb10_gpu_warp=r.get("warp_cuda"), grace_cpu_warp=r.get("warp_cpu"), grace_cpu_scipy_direct=sG.get(c),
                                   box_cpu_warp=bc.get(c, {}).get("warp_cpu"), box_cpu_scipy_direct=sB.get(c))
        g = row["gb10_gpu_warp"]["median_s"]
        row["speedup_gpu_vs_grace_warp"] = row["grace_cpu_warp"]["median_s"] / g if row["grace_cpu_warp"] else None
        row["speedup_gpu_vs_box_warp"] = row["box_cpu_warp"]["median_s"] / g if row["box_cpu_warp"] else None
        row["speedup_gpu_vs_grace_scipy"] = row["grace_cpu_scipy_direct"]["median_s"] / g if row["grace_cpu_scipy_direct"] else None
        row["Q_rel_diff_gpu_vs_grace_warp"] = abs(row["gb10_gpu_warp"]["Q_W"] - row["grace_cpu_warp"]["Q_W"]) / row["grace_cpu_warp"]["Q_W"] if row["grace_cpu_warp"] else None
        row["Q_rel_diff_gpu_vs_scipy"] = abs(row["gb10_gpu_warp"]["Q_W"] - row["grace_cpu_scipy_direct"]["Q_W"]) / row["grace_cpu_scipy_direct"]["Q_W"] if row["grace_cpu_scipy_direct"] else None
        p = row["gb10_gpu_warp"].get("gpu_mean_W"); row["gpu_J_per_solve"] = p * g if p else None
        rows.append(row)
    return rows
FIN = merge_fin(G, B, GS, BS)
MC = []; bmc = {r["N"]: r for r in B["B2_mc"]}
for r in G["B2_mc"]:
    N = r["N"]; g = r["warp_cuda"]; row = dict(N=N, gb10_gpu_warp=g, grace_cpu_warp=r.get("warp_cpu"), grace_cpu_numpy=r["numpy_cpu"], box_cpu_warp=bmc.get(N, {}).get("warp_cpu"), box_cpu_numpy=bmc.get(N, {}).get("numpy_cpu"),
                                         GPU_K_mean=r["GPU_K_mean_numpy"], GPU_K_p99=r["GPU_K_p99_numpy"])
    for k in ("grace_cpu_warp", "grace_cpu_numpy", "box_cpu_warp", "box_cpu_numpy"):
        row["speedup_gpu_vs_" + k] = row[k]["median_s"] / g["median_s"] if row.get(k) else None
    row["gpu_J_per_Mdraw"] = (g["gpu_mean_W"] - (G["meta"]["gpu_idle_W"] or 0)) * g["median_s"] / (N / 1e6) if g.get("gpu_mean_W") and g.get("n_power_samples", 0) >= 5 else None
    row["gpu_J_per_Mdraw_basis"] = "(mean nvidia-smi power.draw during timed repeats - idle) x median wall / (N/1e6); only when >=5 samples (100 ms) were captured"
    MC.append(row)
big = MC[-1]; m6 = [r for r in MC if r["N"] == 10**6][0]
cross = next((r["N"] for r in MC if r["speedup_gpu_vs_grace_cpu_numpy"] and r["speedup_gpu_vs_grace_cpu_numpy"] > 1), None)
fcross = next((r["cells"] for r in FIN if r["speedup_gpu_vs_grace_warp"] and r["speedup_gpu_vs_grace_warp"] > 1), None)
prod = [r for r in FIN if r["cells"] == 2560][0]; top = FIN[-1]
V = VG["V1_grid_convergence"]; vprod = [r for r in V["warp"] if r["nx"] == 320][0]
cold = VG["V4_cold_warm"]["devices"]
hl = dict(
  mc_N_max=big["N"], mc_gpu_draws_per_s=big["gb10_gpu_warp"]["draws_per_s"], mc_gpu_s_at_Nmax=big["gb10_gpu_warp"]["median_s"], mc_numpy_grace_s_at_Nmax=big["grace_cpu_numpy"]["median_s"],
  mc_speedup_vs_numpy_grace_at_Nmax=big["speedup_gpu_vs_grace_cpu_numpy"], mc_speedup_vs_warp_grace_1e6=m6["speedup_gpu_vs_grace_cpu_warp"], mc_speedup_vs_numpy_box_1e6=m6["speedup_gpu_vs_box_cpu_numpy"],
  mc_speedup_vs_numpy_grace_1e6=m6["speedup_gpu_vs_grace_cpu_numpy"], mc_speedup_vs_warp_box_1e6=m6["speedup_gpu_vs_box_cpu_warp"],
  mc_max_abs_diff_gpu_vs_numpy=max(r["gb10_gpu_warp"]["max_abs_diff_vs_numpy"] for r in MC), mc_crossover_N_vs_numpy_grace=cross,
  mc_gpu_J_per_Mdraw_at_Nmax=big["gpu_J_per_Mdraw"],
  fin_prod_cells=2560, fin_prod_gpu_s=prod["gb10_gpu_warp"]["median_s"], fin_prod_grace_warp_s=prod["grace_cpu_warp"]["median_s"], fin_prod_grace_scipy_s=prod["grace_cpu_scipy_direct"]["median_s"],
  fin_prod_speedup_vs_grace_warp=prod["speedup_gpu_vs_grace_warp"], fin_top_cells=top["cells"], fin_top_speedup_vs_grace_warp=top["speedup_gpu_vs_grace_warp"],
  fin_top_speedup_vs_grace_scipy=top["speedup_gpu_vs_grace_scipy"], fin_crossover_cells_vs_grace_warp=fcross,
  fin_max_Q_rel_diff_gpu_vs_cpu=max(r["Q_rel_diff_gpu_vs_grace_warp"] for r in FIN if r["Q_rel_diff_gpu_vs_grace_warp"] is not None),
  val_order=V["observed_order"], val_prod_err_vs_BVP=vprod["err_vs_BVP_rel"], val_richardson_err_vs_BVP=V["richardson_err_vs_BVP_rel"],
  val_energy_residual_max=max(r["energy_residual_rel"] for r in V["warp"]), val_fin_efficiency=VG["V2_reference_1D_BVP"]["fin_efficiency"],
  val_Qp_W_per_m=VG["V2_reference_1D_BVP"]["Qp_W_per_m"], val_scipy_finest_err_vs_BVP=V["scipy_direct"][-1]["err_vs_BVP_rel"], val_scipy_finest_nx=V["scipy_direct"][-1]["nx"],
  cold_gpu_s=cold["cuda:0"]["cold_first_solve_s_incl_kernel_compile"], warm_gpu_s=cold["cuda:0"]["warm_median_s"], cold_cpu_s=cold["cpu"]["cold_first_solve_s_incl_kernel_compile"], warm_cpu_s=cold["cpu"]["warm_median_s"],
  e2e_pipeline_gb10_s=EG["pipeline_median_s"], e2e_pipeline_box_s=EB["pipeline_median_s"], e2e_pipeline_sha_match=EG.get("pipeline_sha256") == EB.get("pipeline_sha256"),
  e2e_table_gpu_s=EG["table"]["gpu"]["solver_wall_s"], e2e_table_grace_cpu_s=EG["table"]["cpu"]["solver_wall_s"], e2e_table_box_cpu_s=EB["table"]["cpu"]["solver_wall_s"],
  e2e_table_max_d_eta=max(v["max_abs_d_eta_vs_vendored"] for v in list(EG["table"].values()) + list(EB["table"].values())), e2e_parity_gb10_s=EG["parity_median_s"],
  parity_max_abs=P["max_abs_difference"], parity_rows=len(P["rows"]) if isinstance(P.get("rows"), list) else None)
hl["fin_table_speedup_gpu_vs_grace"] = hl["e2e_table_grace_cpu_s"] / hl["e2e_table_gpu_s"]
cost = HI["cost_assumptions"]; hrs = sum(HI["gb10_gpu_hours"][k]["hours"] for k in HI["gb10_gpu_hours"])
kwh = sum(HI["gb10_gpu_hours"][k]["hours"] * HI["gb10_gpu_hours"][k]["mean_W"] for k in HI["gb10_gpu_hours"]) / 1000.0
costd = dict(gb10_gpu_hours=hrs, gpu_energy_kWh=kwh, local_electricity_usd=kwh * cost["tariff_usd_per_kWh"], local_amortised_usd=hrs * cost["gb10_price_usd"] / (cost["amortisation_years"] * 8766.0),
             cloud_on_demand_usd=hrs * cost["cloud_usd_per_h"], assumptions=cost, label="ESTIMATE; rental-equivalent hours, not a performance-matched comparison (L40S fp64 rate differs from GB10)")
out = dict(label="NVIDIA metrics, GTC FINAL v2 baseline (AI1_GTC_FINAL_V2_AL)", configuration_id=C["configuration_id"], configuration_sha256=hashlib.sha256(open(os.path.join(H, "../GTC_FINAL_CANDIDATE.json"), "rb").read()).hexdigest(),
           hardware=dict(gb10=G["meta"], box=B["meta"]), headline=hl, fin_solve_scaling=FIN, thermal_mc_scaling=MC, validation=dict(gb10=VG, box=VB),
           end_to_end=dict(gb10=EG, box=EB), final_parity=dict(max_abs_difference=P["max_abs_difference"], passed=P["passed"], device=P["device_name"], warp=P["warp_version"], configuration_sha256=P["configuration_sha256"]),
           tools=HI["tools"], compute_cost=costd, method_notes=HI["method_notes"],
           raw_files={f: sha(f) for f in ["BENCH_GB10.json", "BENCH_GB10_SCIPY.json", "BENCH_BOX_CPU.json", "BENCH_BOX_SCIPY.json", "VALIDATE_GB10.json", "VALIDATE_BOX_CPU.json", "E2E_GB10/e2e.log", "E2E_BOX/e2e.log", "HISTORICAL.json",
                                                "bench_v2.py", "bench_v2_run1.py", "validate_v2.py", "e2e_v2.sh", "mc_kernels.py", "warp_fin_ref.py"] if os.path.exists(os.path.join(H, f))})
json.dump(out, open(os.path.join(H, "NVIDIA_METRICS.json"), "w"), indent=1); print(json.dumps(hl, indent=1)); print(json.dumps({k: v for k, v in costd.items() if k != "assumptions"}))
