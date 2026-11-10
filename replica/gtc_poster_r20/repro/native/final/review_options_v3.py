"""Deterministic geometry-expanded trade screen; not a claim that any option is qualified.
Thermal roots, calibrated coolant scaling, explicit linear support allocations, freeze hardware,
array/view coupling and inherited drag propagation. Full freeze transients only for selected config.
"""
import os
import os,sys,json,math,hashlib,copy
from pathlib import Path
R=Path(os.environ.get('GTCFC_ROOT',os.environ['GTCFC_ROOT']+''));sys.path.insert(0,str(R/'stages/spin1'))
import thermal_spin1 as T
from geometry_v3 import layout
from array_v3 import exact
import mmod_spin1 as MM
import mmod_grid_spin1 as MG
J=lambda p:json.load(open(R/p))
B=J('stages/baseline/GTC_SCOPED_BASELINE_EXACT.json');A=J('inputs/V3A_CONFIG.json');X=J('final/GTC_FINAL_CANDIDATE.json');G=J('inputs/ARRAY_GEOMETRY_V3.json');NB=J('inputs/ai1_replica/checks_t538/t596/final_config_NB2F2_t596.json');FM=J('stages/spin1/freeze/FREEZE_MASS_SPIN1.json');SP=J('stages/spin1/SPIN1_EXACT.json')
def rho(t):
 if t<253:return rho(253)+(rho(253)-rho(263))/10*(253-t)
 if t>373.15:return rho(373.15)+(rho(373.15)-rho(363.15))/10*(t-373.15)
 return T.CPr.PropsSI('D','T',t,'P',3e5,'INCOMP::MPG[0.4]')
def option(i,n,hybrid=False,Fpenalty=0):
 nm=['June','August'][i];tag=['J8','A4'][i];b=B['fleets'][i];mo=T.M.Month(tag);n0=mo.npan0;A0=mo.A0;Fe0=mo.Fe
 mo.npan0=n;mo.A0=mo.plan*n;mo.ncol0=math.ceil(n/10);gg=layout(G[nm],n);a0=b['solar_area_m2'];vf0=float(exact(G[nm],a0/28).mean())
 oldtab=T.FIN_TAB;oldfac=T.FV.AREA_FACTOR
 if hybrid:T.FIN_TAB='F3_L40_t0p5';T.FV.AREA_FACTOR=.9913
 try:
  for z in range(30):
   pk=T.operating(mo,1,'MPG40');area=pk['total_solar_power_and_rejected_heat_W']/319.7;vf=float(exact(gg,area/28).mean());fe=Fe0-(vf-vf0)-Fpenalty
   if abs(fe-mo.Fe)<1e-13:break
   mo.Fe=fe
  nom=T.operating(mo,[.8,.7][i],'MPG40');cool,cd=T.coolant_line(mo,'MPG40')
 finally:T.FIN_TAB=oldtab;T.FV.AREA_FACTOR=oldfac
 L={v['item']:v['kg'] for v in b['ledger']};LL=copy.deepcopy(L);ratio=area/a0;nr=n/n0
 for k in ['array','harness','power_electronics']:LL[k]=L[k]*ratio
 for k in ['radiator','structure_mech','deployment_mechanisms']:LL[k]=L[k]*nr
 if hybrid:LL['radiator']/=T.FV.FIN_MASS_REL
 LL['coolant_loop']=cool
 inv=nom['inventory'];m=sum(inv[k] for k in ['fluid_rack','fluid_trunk','hdr_fluid','panel_fluid']);acc=NB['accumulator'][tag];dV=m*(1/rho(pk['coolant_radiator_inlet_K'])-1/rho(240))*1000;ak=acc['accumulator_kg']/acc['dV_cold240_to_hot352_L']*dV
 nb=NB['BAT_breakdown'][tag];per=((nb['heater_strips_fin_root']+nb['heater_harness'])*1.5+nb['swivel_patch_heaters'])/NB['panels'][tag]+NB['ADD_breakdown_kg_per_panel']['insert_cord']+NB['ADD_breakdown_kg_per_panel']['fitting_swivel_compliance_plugs']
 hw=per*n+ak+nb['switching']+nb['row80_safe_mode'];LL['freeze_restart_including_battery']=max(L['freeze_restart_including_battery'],hw)
 LL['MMOD_spare_panel_allocation']=max(L['MMOD_spare_panel_allocation'],SP['fleets'][i]['item3_mmod']['trunk_SPF_recommended']['total_kg'])
 ram=mo.Aram0+(area-a0)*2/math.pi*mo.beta_stat+(mo.A0-A0);dry=sum(LL.values())-sum(L.values());LL['propellant_delta_inherited_c13_prop']=T.M.C13.prop(mo.core0+dry,ram)-T.M.C13.prop(mo.core0,mo.Aram0)
 mass=sum(LL.values());launch=b['count']*mass+2000
 return dict(case=nm,panels=n,fin='historical bonded K13D comparison' if hybrid else 'Al 6061-T6 26mm/0.225mm',radiator_effective_area_m2=mo.A0,GPU_nominal_K=nom['GPU_K'],HBM_nominal_K=nom['HBM_K'],inlet_peak_K=pk['coolant_radiator_inlet_K'],coolant_supply_nominal_K=nom['coolant_supply_K'],peak_demand_W=pk['total_solar_power_and_rejected_heat_W'],solar_area_m2=area,sc_mass_kg=mass,launch_t=launch/1000,reserve_t=(100000-launch)/1000,freeze_hardware_kg=hw,heater_kW=n*6*2.9446*40/1000,ledger_kg=LL,view_factor=mo.Fe,meets_393_K=pk['coolant_radiator_inlet_K']<=393,mass_fit=launch<=100000,packing='NOT evaluated for this option unless explicitly linked to separate constructive check',transient='Full transient only for selected config; scalar hardware estimate here',limits='Linear support allocation, retained hydraulic head, old mean bus blockage; not structural/hydraulic qualification')
out=dict(scope=__doc__,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),provenance='Inputs and equations in this script; every option is generated, never edited output',thermal_options={},header_options={},adoptions_pending_confirmation=['August GPU-selected fin/panel geometry, explicit radiator film and circular tube freeze inventory; proposal not approved baseline'],no_cuopt_stage=True)
for i,nm in enumerate(['June','August']):
 counts=([77,86,87,90,95,96,100,110] if i==0 else [128,143,144,145,150,160]);rows=[option(i,n) for n in counts];rows.append(option(i,[95,145][i],True));rows.append(option(i,[95,145][i],False,.01));out['thermal_options'][nm]=rows
 n=X['fleets'][i]['radiator_panels']['value'];cc=dict(npan=n,ncol=math.ceil(n/10),trunk_bore_m=[.0241656,.0311977][i]);s,r=MM.taper(.020,10,.010);dmean=sum(d+.0016 for d in s+r)/len(s+r);headers=[]
 for route,W in [('ledger',MM.PW),('short_edge',2.9446)]:
  tb=MG.hdr_tubes(dict(cc,routing=route))
  for flux in [1.,3.]:
   grid=[]
   for tw in [.8,1.2,1.6,2,2.5,3,4,6,8]:
    for S in [0,5,10,15,20,30,40,60,80,100]:
     z=MG.evalc(tb,tw,S,flux);h=dmean/2+(tw-.8)/1000+(S+z['t_b_mm'])/1000
     z.update(blockage_total_frac=MG.blk(h,W),blockage_incremental_frac=MG.blk(h,W)-MG.blk(dmean/2,W),max_envelope_depth_m=.020+2*tw/1000+2*(S+z['t_b_mm'])/1000)
     grid.append(z)
   for target in [1.,.1,-math.log(.95)]:
    valid=[z for z in grid if z['N_5yr']<=target];best=min(valid,key=lambda z:z['total_kg']) if valid else None
    headers.append(dict(routing=route,debris_flux_multiplier=flux,target_N_5yr=target,minimum=best,scope='Header-only BLE screen; circular wrap and unchanged taper bore; no mass credit for shorter pipe. Short-edge reroute needs pressure/ports/root hoses/stow design; N<=1 is NOT high reliability.'))
 out['header_options'][nm]=headers
out['legacy_thermal_option_warning']='Historical old-fin/no-radiator-film options ONLY, not final August predictions. Final choice and constraints come from the NVIDIA sweep and full selected pipeline.'
out['selected_canonical']=[dict(case=f['case'],panels=f['radiator_panels']['value'],mass_kg=f['sc_mass_kg']['value'],GPU_K=f['GPU_nominal_K']['value'],inlet_K=f['coolant_radiator_inlet_peak_K']['value']) for f in X['fleets']]
p=R/'final/REVIEW_OPTIONS_V3.json';p.write_text(json.dumps(out,indent=2,default=lambda z:z.item())+'\n');print('Wrote',p)
