from pathlib import Path
import sys,os,json,math
from scipy.optimize import brentq
D=Path(__file__).resolve().parent;R=Path(os.environ['GTCFC_ROOT']);tag='r11'
os.environ.update(GTCFC_ROOT=str(R),AI1_ROOT=str(R/'inputs/ai1_replica'),PYTHONDONTWRITEBYTECODE='1')
sys.dont_write_bytecode=True;sys.path[:0]=[str(R/'stages/spin1'),str(R/'inputs/repo/src')]
import thermal_spin1 as T
from geometry_v3 import apply
m=T.M.Month('A4');calib_mo_cool0=m.cool0;calib_alloc=m.L0['coolant_loop'];apply(m,'August')
pw=json.loads((R/'stages/spin1/POWER_SPIN1.json').read_text())['cases']['August']['adopted_array'];m.Fe=pw['effective_view_new']
mech=json.loads((D/'REFERENCE_MECHANICAL_LOCK.json').read_text());seam=mech['operational']['module_seam'];gross=pw['area_m2'];fraction=1-seam['gross_planform_loss_fraction'];planar=gross*fraction;rating=seam['local_active_surface_W_m2_required'];solar=planar*rating
states={}
for name,load in [('nominal',.7),('peak',1.)]:
 r=T.operating(m,load,'MPG40');fp=T.mpg40(r['coolant_rack_mean_K']);_,pump,_,inv=T.cool2f(r['IT_kW'],m.A0,m.npan0,m.ncol0,20.,2,fp)
 r.update(check_pump_residual_W=pump-r['pump_electric_W'],properties_query_mean_K=r['coolant_rack_mean_K'],properties_actual_query_K=min(r['coolant_rack_mean_K'],373.15),properties_clamped=r['coolant_rack_mean_K']>373.15,fluid_volume_flow_L_min=r['mass_flow_kg_s']/r['fluid_props']['rho']*60000,hydraulic_computed_volume_L_min=r['inventory']['Vdot_L_s']*60,solar_margin_W=solar-r['total_solar_power_and_rejected_heat_W'],additional_cell_fill_to_cover_actual_demand=r['total_solar_power_and_rejected_heat_W']/solar)
 states[name]=r
maxP=brentq(lambda p:solar-T.operating(m,p/250.,'MPG40')['total_solar_power_and_rejected_heat_W'],200.,260.,xtol=1e-10)
limited=T.operating(m,maxP/250.,'MPG40')
mass,detail=T.coolant_line(m,'MPG40')
fp372=T.mpg40(372.)
x=dict(scope='Isolated selfconsistent native solver at fixed array/view/radiator geometry. Only explicitly passed coolant properties differ. No new adopted baseline.',states=states,solar=dict(gross_planform_m2=gross,seam_planform_loss_fraction=1-fraction,seam_area_m2=gross-planar,remaining_planar_active_surface_m2=planar,locked_remaining_surface_rating_W_m2=rating,rounded_headline_rating_W_m2=324.55,additional_cell_fill_assumption=1.,output_W_at_full_precision_locked_rating=solar,output_W_at_rounded324p55=planar*324.55,scope='Remaining PLANAR surface equivalent module rating, NOT an independently qualified bare-cell rating; internalcellfill is implicit/unspecified. Do not apply324.55to grossarea. A separate geometriccellfillfactor below1would reduceoutput unless already foldedintorating.',maximum_feasible_payload_BOL_kW=maxP,limited_peak_state=limited,required_extra_remaining_surface_rating_to_serve250_W_m2=states['peak']['total_solar_power_and_rejected_heat_W']/planar),calibration=dict(inherited_L0_coolant_allocation_kg=calib_alloc,denominator_water_reference_raw_cool0_kg=calib_mo_cool0,multiplicative_mass_factor=calib_alloc/calib_mo_cool0,calibrated_corrected_line_kg=mass,detail=detail,props_at372=fp372,note='Inheritedwaterreferencecalibrationheldfixed; no backsolve/recalibration. Rawcoolantsizing evaluatedat372Kperexistingpolicy,notnominalorpeaktemperature.'),geometry=dict(area_m2=m.A0,panels=m.npan0,columns=m.ncol0,fin=m.v3_fin,view_factor=m.Fe))
(R/'r11_out/NATIVE_CHECKS.json').write_text(json.dumps(x,indent=2)+'\n');print(tag,'nom',states['nominal']['pump_electric_W'],'pk',states['peak']['pump_electric_W'],'maxPayload',maxP,'mass',mass)
