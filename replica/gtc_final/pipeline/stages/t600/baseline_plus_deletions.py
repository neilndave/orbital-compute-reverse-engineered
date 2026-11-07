"""Read-only adopted/rendered-C1 desk screen; no baseline or render edits."""
from pathlib import Path
import json,sys,hashlib,copy,math
P=Path(__file__).resolve().parent;R=Path('/tmp/gtcfc_root/inputs/ai1_replica');sys.path.insert(0,str(R/'checks_t538'))
import model_t549 as M
out=[]
for i,tag in enumerate(['J8','A4']):
 ptpath=R/'gtc_params'/f'point_{tag}_C1.json';pt=json.load(open(ptpath));mo=M.Month(tag);frac=[.8,.7][i];N=[46,30][i]
 thermal=[]
 for load in [1.,frac]:
  k=dict(T_chip_K=370.,T_hbm_max_K=370.,R_plate_KW=.01422,q_plate_kW=1.7,derate=load,hbm_dT_K=18*load,dT_loop_K=20.,cref_frac=.5,fin=1,fin_area_rel=1.,fin_mass_rel=1.,pmad_heat_to_rad=1.,pmad_eff=.92,q_other_kW=2.,mc_offset_K=.44,pump_spares=2,reserve_floor=.05,wing_scale=1.,hp_lift_K=0.)
  z=mo.ev(k,A_override=pt['areas']['A_rad_face_m2'])
  thermal.append(dict(load_fraction=load,IT_kW=pt['result']['P_IT_peak_kW']*load,Q_reject_kW=z['Q_rej_kW'],GPU_K=z['T_chip_ach_K'],HBM_K=z['T_hbm_ach_K'],coolant_supply_K=z['T_supply_ach_K'],coolant_reference_K=z['T_supply_ach_K']+10,maximum_total_R_K_per_kW_for_370=(370-z['T_supply_ach_K']-10)/(1.7*load),model_status='INHERITED model_t549,F3 water-like thermal table and render-yoke views. NOT full-rack validation;20Klooprise inherited. IncludesPMAD/2kWaux/pumpheat. No newgeometry.'))
 L=copy.deepcopy(pt['mass_lines_kg']);original=sum(L.values());no_margin=sum(v for k,v in L.items() if k!='margin')
 # Replace only old MMOD/spare/completecoolant budgets with explicit scoped pools; do not call deleted functionality designed.
 # Routing/pumps/rack liquid remain in inherited coolant line to avoid free deletion or double counting.
 keep={k:v for k,v in L.items() if k not in ['margin','mmod_bumper','spare_compute']}
 # 70/120 mechanism pool for unknown radiator deployment; do not also carry E mechanisms.
 pools=dict(deployment_mechanisms=[70.,120.][i],MMOD_spare_panel_allocation=[80.,140.][i],freeze_restart_including_battery=[60.,90.][i],life_and_compute_provision=[50.,80.][i]);keep.update(pools)
 hardware=sum(keep.values());launch=N*hardware*1.05+2100
 out.append(dict(case=['June','August'][i],point_id=pt['id'],point_path=str(ptpath),point_sha256=hashlib.sha256(ptpath.read_bytes()).hexdigest(),counts=N,compute_MW=N*pt['result']['P_IT_peak_kW']/1000,geometry_unchanged=True,nominal_radiator_area_m2=pt['areas']['A_rad_face_m2'],physical_radiator_panel_count=pt['geometry_derived']['radiator']['n_panels'],physical_panel_planform_m2=pt['geometry_derived']['radiator']['n_panels']*1.0701,solar_area_m2=pt['areas']['A_arr_m2'],original_line_sum_kg=original,original_result_mass_kg=pt['result']['mass_kg'],original_science_hardware_without_margin_kg=no_margin,original_includes_margin_launch_kg=N*pt['result']['mass_kg']+2000,new_scoped_ledger_kg=keep,new_scoped_hardware_and_propellant_kg=hardware,reserve_fraction=.05,launch_total_kg=launch,margin_100t_kg=100000-launch,mass_fit=launch<=100000,thermal_screens=thermal,warning='Mass/geometry allocation candidate only. Inherited coolant includes pumps,header/rackfluid/piping; no newwetpool added. ADCS includes old propellant;5%reserve conservatively appliedtoall massinclprop. Thermal/packingfailurescannotbe erasedbydeletingMMOD/life requirements.'))
(P/'BASELINE_PLUS_DELETIONS_SCREEN.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
