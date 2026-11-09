from pathlib import Path
import json,itertools,csv
import numpy as np
import os
D=Path(__file__).resolve().parent;ROOT=Path(os.environ['R11_ROOT'])
j=json.loads((ROOT/'native/r11_out/NATIVE_CHECKS.json').read_text());N=j['states']['nominal'];P=json.loads((D/'GLYCOL_REFERENCE227_INPUT.json').read_text())['cases'][0]['states']['reference227']
# Energy-conserving electrical heat partitions. 227kW reference scenario leaves23kW unconsumed; no fictitious consumer.
budgets={
 'nominal_175':dict(GPU_package=118.8,CPU=14.4,CPU_memory=6.,node_IO=12.,NVLink=12.,internal_DC_loss=10.,misc_control=1.8),
 'reference_peak_227':dict(GPU_package=165.6,CPU=18.,CPU_memory=6.,node_IO=10.,NVLink=12.,internal_DC_loss=10.,misc_control=5.4)}
# Package-power sensitivity changes allocation of non-GPU total, not total power; weights not vendor measurements.
base_other={k:v for k,v in budgets['nominal_175'].items() if k!='GPU_package'}
for pkg in (1.5,1.8):
 rest=175-72*pkg; factor=rest/sum(base_other.values())
 budgets[f'nominal_175_pkg{pkg}']=dict(GPU_package=72*pkg,**{k:v*factor for k,v in base_other.items()})
for b in budgets.values():assert min(b.values())>0
power=[];thermal=[];branches=[]
# Approximately digitized Fig5, NOT original rawdata. Never extrapolated beyond shownrange.
flow_map=np.array([.5,1.,1.5,2.,2.5]);Rinlet_map=np.array([.027,.0176,.0148,.0134,.0124]);dp_map=np.array([.10,1.10,2.4,4.15,6.3])*6.894757
CPVOL_PG25_W_K_per_Lmin=1020*3900/60000 # assumed characterization conversion, not paper property data
for tag,B in budgets.items():
 peak='peak' in tag; r=P if peak else N;total=sum(B.values());props=r['fluid_props'];mdot=r['mass_flow_kg_s'];V=mdot/props['rho']*60000;Tin=r['coolant_supply_K'];bulk=total*1000/(mdot*props['cp']);pump=r['pump_electric_W']/1000
 external_input=(total+2+pump)/.92
 power.append(dict(case=tag,component_kW=B,payload_total_kW=total,unspent_250kW_peak_cap_kW=250-total,external_pump_kW=pump,external_aux_kW=2,external_conversion_loss_kW=external_input-total-2-pump,generation_and_rejection_kW=external_input,note='Component partitions are assumed sensitivities, NOT sourced equipment power. Frozen inlet/pump at250design state used as conservative peak comparison for227, not a recomputed227bulk operating state.'))
 # Parallel heat-proportional flow sensitivities. Every watt and gram/s accounted once.
 for component,q in B.items():
  groups={'GPU_package':72,'CPU':36,'CPU_memory':36,'node_IO':18,'NVLink':9,'internal_DC_loss':1,'misc_control':1}[component]
  branches.append(dict(case=tag,group=component,count=groups,total_kW=q,per_group_kW=q/groups,total_L_min=V*q/total,per_group_L_min=V*q/total/groups,branch_dT_K=bulk,flow_model='Heat-proportional parallel allocation; actual Strata/node multi-component circuit topology unresolved'))
 qpkg=B['GPU_package']*1000/72;flow_pkg=V*B['GPU_package']/total/72
 if not .5<=flow_pkg<=2.5:raise ValueError('Literature map extrapolation')
 Rmap=float(np.interp(flow_pkg,flow_map,Rinlet_map));dp=float(np.interp(flow_pkg,flow_map,dp_map));Rmean_map=Rmap-1/(2*flow_pkg*CPVOL_PG25_W_K_per_Lmin)
 for fHBM,penalty,Rdie,Rhbm in itertools.product((.1,.2,.3),(1.,1.25,1.5),(.0072,.0144),(.01,.02,.04)):
  # fHBM of one package; two equal compute dies consume the remainder. No added second HBM electrical load.
  Qh=qpkg*fHBM;Qd=qpkg*(1-fHBM)/2;Rplate=Rmean_map*penalty
  base=Tin+bulk/2+qpkg*Rplate
  Td=base+Qd*Rdie;Th=base+Qh*Rhbm
  thermal.append(dict(case=tag,payload_total_kW=total,package_W=qpkg,HBM_fraction=fHBM,per_die_W=Qd,HBM_aggregate_W=Qh,package_energy_residual_W=qpkg-(2*Qd+Qh),package_branch_L_min=flow_pkg,branch_dT_K=bulk,Tin_K=Tin,literature_PG25_Rbase_to_inlet_K_W=Rmap,literature_PG25_dp_kPa=dp,literature_mean_R_after_reference_conversion_K_W=Rmean_map,property_map_factor_assumed=penalty,assumed_per_die_R_K_W=Rdie,assumed_HBM_aggregate_R_K_W=Rhbm,T_base_proxy_K=base,T_GPU_die_conditional_K=Td,T_HBM_conditional_K=Th,Rplate_mean_required_for_GPU366_K_W=(366-Tin-bulk/2-Qd*Rdie)/qpkg,R_HBM_max_for362_K_W=(362-base)/Qh,note='Not Rubin prediction: paper plate1kW/PG25/305K, approximate digitization; package paths, fluid correction and shared-coldplate spread unknown. Peak uses frozen250cap inlet as a conservative comparison, not actual227bulk solution.'))
# Nominal reference CPU/fabric path requirements only; R values unknown, not invented.
local_req=[]
for tag,B in budgets.items():
 r=P if 'peak' in tag else N;md=r['mass_flow_kg_s'];cp=r['fluid_props']['cp'];ref=r['coolant_supply_K']+sum(B.values())*1000/(2*md*cp)
 for name,n,target in [('CPU',36,366),('NVLink',9,366),('node_IO',18,366)]:
  perq=B[name]*1000/n
  local_req.append(dict(case=tag,component=name,per_group_W=perq,Tbulkmean_K=ref,diagnostic_target_K=target,Rtotal_to_mean_required_K_W=(target-ref)/perq,note='366K reference is an arithmetic comparison, NOT sourced CPU/fabric operatinglimit; actual plate/stack resistance unknown'))
for row in power:
 row['note']='Energy-conserving mathematical component allocation, not vendor load data. Nominal175 and reference227 each use their separately solved bulk state.250 remains a separate design-cap stress case, not fictitious reserve heat.'
for row in thermal:row['note']='Conditional analogue sensitivity, not a Rubin prediction. Fresh corrected native inlet/flow for175 or227; no fittedR orpartitions to preserve366/362.'
assert all(abs(sum(p['component_kW'].values())-p['payload_total_kW'])<1e-9 for p in power)
assert all(abs(x['package_energy_residual_W'])<1e-9 for x in thermal)
for tag in budgets:
 assert abs(sum(x['total_L_min'] for x in branches if x['case']==tag)-(N if 'peak' not in tag else P)['mass_flow_kg_s']/(N if 'peak' not in tag else P)['fluid_props']['rho']*60000)<1e-9
out=dict(diagnostic_only=True,adopted=False,power_budgets=power,thermal_sensitivities=thermal,branches=branches,path_resistance_requirements=local_req,source='ASME2022-97421Fig5 PG25 approximate digitization; nohotMPG40/Rubin map; primaryNVIDIAsystemspec45C inlet, no validated die/HBMsplit.',limitations='No property penalty, Rdie or HBM split is vendor qualified. Package heat includes HBM; CPU and network heat separately counted exactly once. No arbitraryR selection to hit366K.')
(ROOT/'out').mkdir(exist_ok=True);(ROOT/'out/DEVICE_THERMAL_RECHECK.json').write_text(json.dumps(out,indent=2)+'\n')
with (ROOT/'out/DEVICE_THERMAL_SENSITIVITIES.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(thermal[0]));w.writeheader();w.writerows(thermal)
central=[x for x in thermal if x['case']in ['nominal_175','reference_peak_227'] and x['HBM_fraction']==.2 and x['property_map_factor_assumed']==1 and x['assumed_per_die_R_K_W']==.0072 and x['assumed_HBM_aggregate_R_K_W']==.02]
print(json.dumps(central,indent=2))
