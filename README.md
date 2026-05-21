# Passive Precision — Giza Engineering Simulation

Engineering feasibility analysis for a hydraulic-assisted construction model of Khufu's pyramid.

> **Claim boundary:** Engineering closure under stated inputs does not mean historical use has been archaeologically proven.

## What This Is

A set of constraint-gate screens that test whether a proposed hydraulic construction sequence for the Great Pyramid is **physically consistent** under stated engineering assumptions.

The model does not prove anything happened. It checks whether the proposed mechanism can **pass every engineering gate** — hydrostatic pressure, air management, plug geometry, reset timing, vent choke calibration, construction sequence ordering, and residue spatial prediction.

## Gates

| Gate | Subsystem | Tests |
|------|-----------|-------|
| Hydrostatic pressure at depth | Hydraulics | Pressure vs depth |
| Lower water node | Hydraulics | Node activation + pressure |
| Air management | Hydraulics | Compressible vent flow |
| Reset time | Hydraulics | Event volume / vent flow |
| Vent choke calibration | Hydraulics | Controlled band 0.005 – 0.05 m2 |
| Plug leakage + choke geometry | Plugs | Perimeter gap area classification |
| Construction sequence | Sequencing | 11-event lifecycle ordering |
| Residue spatial prediction | Prediction | Mineral signal contrast ratios |

**Controlled reset band:** 0.005 – 0.05 m2 effective choke area. Below: air lock risk. Above: uncontrolled discharge.

## Simulation Modules

| File | Purpose |
|------|---------|
| `giza_reduced_gate_ledger.py` | Master gate ledger — all 18 gates |
| `giza_lower_node_pressure_sim.py` | Hydraulic unload screen |
| `giza_lower_node_vent_reset_sim.py` | Vent reset cycle |
| `giza_vent_choke_calibration.py` | Choke area sweep across depths and volumes |
| `giza_plug_leakage_choke_sim.py` | Plug-fit geometry + choke classification |
| `giza_sequence_boss_gate.py` | Construction lifecycle sequence validator |
| `giza_residue_prediction_gate.py` | Spatial residue prediction + contrast ratios |
| `giza_sequence_sim.py` | Sequence simulation |

## Key Results

- Schedule ratio: **1.15** (repaired baseline, conditional pass)
- Lower/upper residue contrast: **>1.5** (supports pattern screen)
- Plug upstream/downstream contrast: **>1.1**
- Plug interface/passage contrast: **>1.1**
- Canonical lifecycle sequence: **0 conflicts**
- All four known fault types detected by sequence gate

## Quick Start

```python
from giza_sequence_boss_gate import evaluate_sequence
result = evaluate_sequence("canonical")
print(result.status)        # conditional_pass
print(result.conflicts)     # []

from giza_vent_choke_calibration import build_rows
rows = build_rows()
controlled = [r for r in rows if r.status == "controlled_reset"]
print(len(controlled), "controlled reset configurations")
```

## Running The Full Stack

```python
from giza_reduced_gate_ledger import run_full_ledger
results = run_full_ledger()
for gate in results:
    print(gate["name"], gate["status"])
```

## Claim Boundaries

### Allowed Engineering Claims
- Validation-ready full-build engineering closure under stated inputs
- Water-applied lower system functions as air-management / reset / isolation infrastructure
- Ordinary mechanics move mass
- Phased upper workcells resolve the upper-zone integration conflict
- Residue chemistry is a testable prediction layer

### Blocked Claims
- Historical proof
- Hydraulic lifting proven
- Long-range vibration/hydraulic transfer proven
- Grand Gallery waveguide proof
- Salt/alum/sulfate proof without controls

## Dependencies

Standard library only for the simulation files. No external packages required.

---
Engineering screen only. Not archaeological proof.
