"""Which F4 design a downstream check reads: the 70 C what-if (legacy, untagged files) or the 45 C baseline (files tagged _T45).

Select with the environment variable RTS_TAG:  unset or "" = 70 C what-if (results/full3d/optimized_design.json, stageC.json);
RTS_TAG=_T45 = 45 C baseline (results/full3d/optimized_design_T45.json, stageC_T45.json).  Outputs of a downstream check use `tagged(path)` so a
45 C run writes <name>_T45.<ext> and never overwrites the 70 C file (DECISIONS row 57; P14 re-run of every 70 C check at the 45 C baseline)."""
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
TAG = os.environ.get("RTS_TAG", "")
if TAG not in ("", "_T45"):
    raise ValueError("RTS_TAG must be '' (70 C what-if) or '_T45' (45 C baseline), got %r" % TAG)
IS_BASELINE = TAG == "_T45"


def full3d(name):
    """results/full3d/<name><TAG>.json as a Path (name without extension)."""
    return ROOT / "results" / "full3d" / f"{name}{TAG}.json"


def design():
    """The optimised design json (optimized_design or optimized_design_T45)."""
    return json.load(open(full3d("optimized_design")))


def stage_c():
    return json.load(open(full3d("stageC")))


def tagged(path):
    """Insert the tag before the extension: tagged('results/x/a.json') -> results/x/a_T45.json under RTS_TAG=_T45, unchanged otherwise."""
    p = pathlib.Path(path)
    return p.with_name(p.stem + TAG + p.suffix) if TAG else p


def summary():
    """Design numbers every downstream script needs: supply K, IT kW, as-built panel count, panel width / length, panel mass."""
    d = design()
    ab = d["as_built"]
    return dict(T_sup_K=d["T_sup_K"], P_IT_kW=ab["P_IT_kW"], n_built=ab["n_built"], width_m=d["width_m"], length_m=d["length_m"],
                m_panel_kg=ab["m_panel_kg"], m_panel_metal_kg=d["metrics"]["m_panel_metal_kg"], m_panel_tube_kg=d["metrics"]["m_panel_tube_kg"],
                n_across=int(d["cfg"]["across"]), along=int(ab["along"]), array_kg=d["full"]["parts"]["array_kg"], tag=TAG)

def n_added():
    """Panels added on top of the as-built count to hold the worst case WITH the strip bumper (DECISIONS row 52 at 70 C = +4).
    Under RTS_TAG=_T45 the value is the one re-derived from the 45 C Warp rows (P14); override with env RTS_NADD for a what-if."""
    import os
    if os.environ.get("RTS_NADD") not in (None, ""):
        return int(os.environ["RTS_NADD"])
    return 4 if not IS_BASELINE else N_ADD_T45


N_ADD_T45 = 2          # P14 item 1: results/orbit_sweep/orbit_sweep_T45.json, Z-93 alpha 0.36 no-bumper extra_area_pct 0.6808 % x 264 = 1.80 -> +2 (same rule as DECISIONS row 52: 1.875 % x 176 = 3.3 -> +4 at 70 C)
