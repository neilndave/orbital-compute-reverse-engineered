"""Same Rack, Two Skies: differentiable GPU co-design of radiators and heat pumps for AI racks.

Modules
-------
warp_fin     2-D conduction + radiation fin/panel solver in NVIDIA Warp (float64) with an adjoint gradient
exact_fin    analytic nonlinear radiating-fin reference used to validate the solver
viewfactor   Monte-Carlo diffuse view factors in Warp, checked against closed-form cases
hpcycle      vapor-compression heat-pump cycle (CoolProp)
sysmodel     0-D system mass/area model (radiator + PV + heat-pump hardware) and break-even
env_leo      LEO environmental heat load (quadrature over the Earth sphere)
config       YAML input files with per-input provenance tags
plotstyle    one consistent matplotlib figure style
"""
__version__ = "0.1.0"
