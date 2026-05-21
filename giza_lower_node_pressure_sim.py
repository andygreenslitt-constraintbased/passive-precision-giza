"""
Giza lower-node hydraulic/contact calibration screen.

Engineering boundary:
- This does not prove historical use.
- This does not prove the feed path existed.
- This does not claim water lifted every block.
- This does not revive long-range mechanical transfer.
- It only tests whether the observed depth-pressure scale is physically useful
  under a ground-level feed assumption.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PA_PER_PSI = 6894.76
NEWTON_PER_TONNE_FORCE = 9806.65


@dataclass(frozen=True)
class HydrostaticInputs:
    depth_m: float = 30.0
    depth_range_m: tuple[float, float] = (30.0, 35.0)
    rho_water_kg_m3: float = 1000.0
    g: float = 9.81
    chamber_volume_m3: float = 462.0
    descending_passage_area_m2: float = 1.26
    discharge_coefficient: float = 0.62


@dataclass(frozen=True)
class PressureResult:
    depth_m: float
    pressure_pa: float
    pressure_psi: float
    pressure_kpa: float
    force_per_m2_n: float
    tonnes_force_per_m2: float


@dataclass(frozen=True)
class VentFlowResult:
    pressure_psi: float
    vent_area_m2: float
    flow_m3_s: float
    reset_times_s: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class ContactInputs:
    block_mass_kg: float = 2500.0
    mu_dry: float = 0.6
    mu_wet: float = 0.3
    worker_pull_n: float = 300.0


@dataclass(frozen=True)
class ContactResult:
    pressure_psi: float
    pressure_pa: float
    coupled_area_m2: float
    coupling_efficiency: float
    normal_force_n: float
    hydraulic_unload_n: float
    unload_percent_of_weight: float
    effective_normal_n: float
    friction_force_dry_n: float
    friction_force_assisted_n: float
    force_savings_n: float
    percent_reduction: float
    workers_before: float
    workers_after: float
    separation_flag: bool
    useful_flag: bool
    strong_flag: bool
    status: str


def pressure_from_depth(depth_m: float, rho_water_kg_m3: float = 1000.0, g: float = 9.81) -> PressureResult:
    pressure_pa = rho_water_kg_m3 * g * depth_m
    pressure_psi = pressure_pa / PA_PER_PSI
    return PressureResult(
        depth_m=depth_m,
        pressure_pa=pressure_pa,
        pressure_psi=pressure_psi,
        pressure_kpa=pressure_pa / 1000.0,
        force_per_m2_n=pressure_pa,
        tonnes_force_per_m2=pressure_pa / NEWTON_PER_TONNE_FORCE,
    )


def psi_to_pa(pressure_psi: float) -> float:
    return pressure_psi * PA_PER_PSI


def orifice_flow_m3_s(
    pressure_pa: float,
    area_m2: float,
    rho_water_kg_m3: float = 1000.0,
    discharge_coefficient: float = 0.62,
) -> float:
    if pressure_pa <= 0 or area_m2 <= 0:
        return 0.0
    return discharge_coefficient * area_m2 * math.sqrt(2.0 * pressure_pa / rho_water_kg_m3)


def vent_flow_table(
    pressure_psi_values: Iterable[float],
    vent_areas_m2: Iterable[float],
    event_volumes_m3: Iterable[float] = (1.0, 5.0, 10.0),
    rho_water_kg_m3: float = 1000.0,
    discharge_coefficient: float = 0.62,
) -> list[VentFlowResult]:
    rows: list[VentFlowResult] = []
    for pressure_psi in pressure_psi_values:
        pressure_pa = psi_to_pa(pressure_psi)
        for area in vent_areas_m2:
            flow = orifice_flow_m3_s(pressure_pa, area, rho_water_kg_m3, discharge_coefficient)
            reset_times = tuple((volume, volume / flow if flow > 0 else math.inf) for volume in event_volumes_m3)
            rows.append(VentFlowResult(pressure_psi, area, flow, reset_times))
    return rows


def contact_result(
    pressure_psi: float,
    coupled_area_m2: float,
    coupling_efficiency: float,
    inputs: ContactInputs = ContactInputs(),
    g: float = 9.81,
) -> ContactResult:
    pressure_pa = psi_to_pa(pressure_psi)
    normal_force = inputs.block_mass_kg * g
    hydraulic_unload = pressure_pa * coupled_area_m2 * coupling_efficiency
    effective_normal = max(normal_force - hydraulic_unload, 0.0)
    friction_dry = inputs.mu_dry * normal_force
    friction_assisted = inputs.mu_wet * effective_normal
    savings = friction_dry - friction_assisted
    percent_reduction = 100.0 * savings / friction_dry if friction_dry > 0 else 0.0
    workers_before = friction_dry / inputs.worker_pull_n
    workers_after = friction_assisted / inputs.worker_pull_n
    separation = hydraulic_unload >= normal_force
    useful = percent_reduction >= 10.0 and not separation
    strong = percent_reduction >= 30.0 and not separation
    status = "separation" if separation else "strong" if strong else "useful" if useful else "weak"
    return ContactResult(
        pressure_psi=pressure_psi,
        pressure_pa=pressure_pa,
        coupled_area_m2=coupled_area_m2,
        coupling_efficiency=coupling_efficiency,
        normal_force_n=normal_force,
        hydraulic_unload_n=hydraulic_unload,
        unload_percent_of_weight=100.0 * hydraulic_unload / normal_force if normal_force > 0 else 0.0,
        effective_normal_n=effective_normal,
        friction_force_dry_n=friction_dry,
        friction_force_assisted_n=friction_assisted,
        force_savings_n=savings,
        percent_reduction=percent_reduction,
        workers_before=workers_before,
        workers_after=workers_after,
        separation_flag=separation,
        useful_flag=useful,
        strong_flag=strong,
        status=status,
    )


def contact_sweep(
    pressure_psi_values: Iterable[float],
    coupled_areas_m2: Iterable[float] = (0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1),
    coupling_efficiencies: Iterable[float] = (0.05, 0.10, 0.25, 0.50, 1.0),
    inputs: ContactInputs = ContactInputs(),
) -> list[ContactResult]:
    return [
        contact_result(pressure, area, efficiency, inputs)
        for pressure in pressure_psi_values
        for area in coupled_areas_m2
        for efficiency in coupling_efficiencies
    ]


def print_pressure_summary(results: list[PressureResult]) -> None:
    print("MODEL 1: HYDROSTATIC HEAD")
    print("Pressure from ground-level feed into lower node depth.")
    print(f"{'depth m':>8} {'psi':>10} {'kPa':>10} {'tonnes-force/m2':>18}")
    print("-" * 52)
    for row in results:
        print(f"{row.depth_m:8.1f} {row.pressure_psi:10.2f} {row.pressure_kpa:10.1f} {row.tonnes_force_per_m2:18.2f}")
    print()


def print_vent_summary(rows: list[VentFlowResult]) -> None:
    print("MODEL 2: LOWER CHAMBER PRESSURE / VENT / RESET SCREEN")
    print("Simplified lumped pressure node with orifice bleed/reset. This is not CFD.")
    print("Sealed chamber screen: unsafe if pressure cannot vent/reset and approaches full head pressure.")
    print(f"{'psi':>8} {'vent area m2':>14} {'flow m3/s':>12} {'1m3 reset s':>12} {'5m3 reset s':>12} {'10m3 reset s':>13}")
    print("-" * 80)
    for row in rows:
        reset = dict(row.reset_times_s)
        print(
            f"{row.pressure_psi:8.1f} {row.vent_area_m2:14.3f} {row.flow_m3_s:12.3f} "
            f"{reset.get(1.0, math.inf):12.1f} {reset.get(5.0, math.inf):12.1f} {reset.get(10.0, math.inf):13.1f}"
        )
    print()


def print_contact_summary(rows: list[ContactResult]) -> None:
    print("MODEL 3: CONTACT / FRICTION USEFULNESS SCREEN")
    print("Hydraulic unload is local interface assistance only; it is not a claim that water lifted blocks.")
    print(
        f"{'psi':>6} {'area m2':>8} {'eff':>6} {'unload %wt':>11} "
        f"{'assisted N':>12} {'reduction %':>12} {'workers before':>15} {'workers after':>14} {'status':>11}"
    )
    print("-" * 110)
    for row in rows:
        print(
            f"{row.pressure_psi:6.1f} {row.coupled_area_m2:8.3f} {row.coupling_efficiency:6.2f} "
            f"{row.unload_percent_of_weight:11.1f} {row.friction_force_assisted_n:12.0f} "
            f"{row.percent_reduction:12.1f} {row.workers_before:15.1f} {row.workers_after:14.1f} {row.status:>11}"
        )
    print()


def print_gate_summary(pressure_rows: list[PressureResult], contact_rows: list[ContactResult]) -> None:
    psi_values = [row.pressure_psi for row in pressure_rows]
    depth_gate = min(psi_values) >= 42.0 and max(psi_values) <= 51.0
    useful_rows = [row for row in contact_rows if row.useful_flag]
    strong_rows = [row for row in contact_rows if row.strong_flag]
    separation_rows = [row for row in contact_rows if row.separation_flag]
    modest_rows = [
        row
        for row in contact_rows
        if row.useful_flag and row.coupled_area_m2 <= 0.05 and row.coupling_efficiency <= 0.50
    ]
    usefulness_gate = bool(modest_rows)
    print("MODEL 4: GATE SUMMARY")
    print(f"- depth-to-pressure gate: {'passes screen' if depth_gate else 'fails screen'}")
    print(f"  30-35 m head produces {min(psi_values):.1f}-{max(psi_values):.1f} psi.")
    print(
        f"- hydraulic usefulness gate: {'passes screen' if usefulness_gate else 'conditional / not closed'} "
        f"({len(useful_rows)} useful rows, {len(strong_rows)} strong rows in full sweep)."
    )
    if modest_rows:
        first = modest_rows[0]
        print(
            "  First modest useful row: "
            f"{first.pressure_psi:.1f} psi, area={first.coupled_area_m2:.3f} m2, "
            f"eff={first.coupling_efficiency:.2f}, reduction={first.percent_reduction:.1f}%."
        )
    if separation_rows:
        first_sep = separation_rows[0]
        print(
            "- separation risk appears when P*A*eff >= block weight; "
            f"first sweep separation row is {first_sep.pressure_psi:.1f} psi, "
            f"area={first_sep.coupled_area_m2:.3f} m2, eff={first_sep.coupling_efficiency:.2f}."
        )
    else:
        print("- separation risk: no separation rows in this sweep, but threshold is P*A*eff >= block weight.")
    print("- vent/reset gate: conditional on actual vent geometry, sealing, blockage state, and reset path.")
    print()
    print("BOUNDARY NOTE")
    print("This is a pressure/flow/contact calibration screen only. It does not prove historical use,")
    print("does not prove a feed path existed, does not claim water lifted every block, and does not")
    print("revive long-range mechanical transfer.")


def export_pressure_csv(path: Path, rows: list[PressureResult]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("depth_m", "pressure_psi", "pressure_kpa", "tonnes_force_per_m2"),
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "depth_m": row.depth_m,
                    "pressure_psi": row.pressure_psi,
                    "pressure_kpa": row.pressure_kpa,
                    "tonnes_force_per_m2": row.tonnes_force_per_m2,
                }
            )


def export_contact_csv(path: Path, rows: list[ContactResult]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "pressure_psi",
                "coupled_area_m2",
                "coupling_efficiency",
                "unload_percent_of_weight",
                "friction_force_assisted_n",
                "percent_reduction",
                "workers_before",
                "workers_after",
                "status",
            ),
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: getattr(row, field) for field in writer.fieldnames})


def run(export_csv: bool = True) -> None:
    inputs = HydrostaticInputs()
    pressure_rows = [pressure_from_depth(depth, inputs.rho_water_kg_m3, inputs.g) for depth in inputs.depth_range_m]
    pressure_band = (43.0, 50.0)
    vent_rows = vent_flow_table(
        pressure_psi_values=pressure_band,
        vent_areas_m2=(0.001, 0.005, 0.01, 0.05, 0.1),
        event_volumes_m3=(1.0, 5.0, 10.0),
        discharge_coefficient=inputs.discharge_coefficient,
    )
    contact_rows = contact_sweep(pressure_band)

    print("GIZA LOWER-NODE HYDRAULIC / CONTACT CALIBRATION SCREEN")
    print("=" * 72)
    print("Engineering screen only; not historical proof.")
    print()
    print_pressure_summary(pressure_rows)
    print_vent_summary(vent_rows)
    print_contact_summary(contact_rows)
    print_gate_summary(pressure_rows, contact_rows)

    if export_csv:
        base = Path(__file__).resolve().parent
        export_pressure_csv(base / "pressure_head_summary.csv", pressure_rows)
        export_contact_csv(base / "contact_sweep_summary.csv", contact_rows)
        print()
        print("CSV exports:")
        print(f"- {base / 'pressure_head_summary.csv'}")
        print(f"- {base / 'contact_sweep_summary.csv'}")


if __name__ == "__main__":
    run()
