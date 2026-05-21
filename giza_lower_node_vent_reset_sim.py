"""Giza lower-node vent/reset pressure screen.

This simulation does not prove historical use. It does not prove the feed path
existed. It tests whether the lower chamber could be pressure-safe only if
vent/reset capacity exists. Sealed pressure fails; vent/reset is the candidate
rescue.

The model is a lumped pressure/flow screen, not CFD. It treats a ground-level
water head as the source pressure, incoming water as displacing an equal volume
of air, and candidate vent paths as simple orifices.
"""

from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Literal


Status = Literal["sealed_fail", "weak_vent", "controlled_reset", "overviolent"]

PA_PER_PSI = 6894.757293168
KPA_PER_PA = 0.001
SECONDS_PER_MINUTE = 60.0


@dataclass(frozen=True)
class VentResetInputs:
    depth_values_m: tuple[float, ...] = (30.0, 35.0)
    chamber_volume_m3: float = 462.0
    event_volumes_m3: tuple[float, ...] = (1.0, 5.0, 10.0, 25.0, 50.0)
    vent_areas_m2: tuple[float, ...] = (
        0.0,
        0.0005,
        0.001,
        0.005,
        0.01,
        0.05,
        0.1,
    )
    discharge_coefficient: float = 0.62
    air_density_kg_m3: float = 1.2
    water_density_kg_m3: float = 1000.0
    gravity_m_s2: float = 9.81
    practical_reset_time_s: float = 300.0
    overviolent_flow_m3_s: float = 10.0
    overviolent_velocity_m_s: float = 300.0

    def __post_init__(self) -> None:
        if self.chamber_volume_m3 <= 0:
            raise ValueError("chamber_volume_m3 must be positive")
        if self.discharge_coefficient <= 0:
            raise ValueError("discharge_coefficient must be positive")
        if self.air_density_kg_m3 <= 0 or self.water_density_kg_m3 <= 0:
            raise ValueError("densities must be positive")
        if self.gravity_m_s2 <= 0:
            raise ValueError("gravity_m_s2 must be positive")
        if self.practical_reset_time_s <= 0:
            raise ValueError("practical_reset_time_s must be positive")
        if self.overviolent_flow_m3_s <= 0 or self.overviolent_velocity_m_s <= 0:
            raise ValueError("overviolent thresholds must be positive")
        if any(depth <= 0 for depth in self.depth_values_m):
            raise ValueError("depth values must be positive")
        if any(volume <= 0 for volume in self.event_volumes_m3):
            raise ValueError("event volumes must be positive")
        if any(area < 0 for area in self.vent_areas_m2):
            raise ValueError("vent areas must be non-negative")


@dataclass(frozen=True)
class PressureRow:
    depth_m: float
    pressure_pa: float
    pressure_kpa: float
    pressure_psi: float


@dataclass(frozen=True)
class VentResetRow:
    depth_m: float
    event_volume_m3: float
    vent_area_m2: float
    pressure_pa: float
    pressure_kpa: float
    pressure_psi: float
    vent_flow_m3_s: float
    vent_velocity_m_s: float
    reset_time_s: float
    reset_time_min: float
    status: Status


def pressure_from_depth_pa(
    depth_m: float,
    rho_water_kg_m3: float = 1000.0,
    gravity_m_s2: float = 9.81,
) -> float:
    """Return hydrostatic pressure from head depth in pascals."""
    if depth_m <= 0:
        raise ValueError("depth_m must be positive")
    if rho_water_kg_m3 <= 0 or gravity_m_s2 <= 0:
        raise ValueError("density and gravity must be positive")
    return rho_water_kg_m3 * gravity_m_s2 * depth_m


def pa_to_psi(pressure_pa: float) -> float:
    return pressure_pa / PA_PER_PSI


def pressure_row(depth_m: float, inputs: VentResetInputs = VentResetInputs()) -> PressureRow:
    pressure_pa = pressure_from_depth_pa(
        depth_m,
        inputs.water_density_kg_m3,
        inputs.gravity_m_s2,
    )
    return PressureRow(
        depth_m=depth_m,
        pressure_pa=pressure_pa,
        pressure_kpa=pressure_pa * KPA_PER_PA,
        pressure_psi=pa_to_psi(pressure_pa),
    )


def orifice_air_flow_m3_s(
    delta_p_pa: float,
    vent_area_m2: float,
    discharge_coefficient: float = 0.62,
    air_density_kg_m3: float = 1.2,
) -> float:
    """Return lumped air outflow through an orifice in cubic meters per second."""
    if delta_p_pa < 0:
        raise ValueError("delta_p_pa must be non-negative")
    if vent_area_m2 < 0:
        raise ValueError("vent_area_m2 must be non-negative")
    if discharge_coefficient <= 0 or air_density_kg_m3 <= 0:
        raise ValueError("discharge coefficient and air density must be positive")
    if delta_p_pa == 0 or vent_area_m2 == 0:
        return 0.0
    return discharge_coefficient * vent_area_m2 * math.sqrt(2.0 * delta_p_pa / air_density_kg_m3)


def vent_velocity_m_s(flow_m3_s: float, vent_area_m2: float) -> float:
    if vent_area_m2 <= 0:
        return 0.0
    return flow_m3_s / vent_area_m2


def classify_reset_status(
    vent_area_m2: float,
    vent_flow_m3_s: float,
    velocity_m_s: float,
    reset_time_s: float,
    inputs: VentResetInputs = VentResetInputs(),
) -> Status:
    if vent_area_m2 <= 0:
        return "sealed_fail"
    if (
        vent_flow_m3_s >= inputs.overviolent_flow_m3_s
        or (velocity_m_s >= inputs.overviolent_velocity_m_s and vent_area_m2 >= 0.05)
    ):
        return "overviolent"
    if not math.isfinite(reset_time_s) or reset_time_s > inputs.practical_reset_time_s:
        return "weak_vent"
    return "controlled_reset"


def evaluate_vent_reset(
    depth_m: float,
    event_volume_m3: float,
    vent_area_m2: float,
    inputs: VentResetInputs = VentResetInputs(),
) -> VentResetRow:
    if event_volume_m3 <= 0:
        raise ValueError("event_volume_m3 must be positive")
    if vent_area_m2 < 0:
        raise ValueError("vent_area_m2 must be non-negative")
    pressure = pressure_row(depth_m, inputs)
    flow = orifice_air_flow_m3_s(
        pressure.pressure_pa,
        vent_area_m2,
        inputs.discharge_coefficient,
        inputs.air_density_kg_m3,
    )
    velocity = vent_velocity_m_s(flow, vent_area_m2)
    reset_time_s = math.inf if flow <= 0 else event_volume_m3 / flow
    status = classify_reset_status(vent_area_m2, flow, velocity, reset_time_s, inputs)
    return VentResetRow(
        depth_m=depth_m,
        event_volume_m3=event_volume_m3,
        vent_area_m2=vent_area_m2,
        pressure_pa=pressure.pressure_pa,
        pressure_kpa=pressure.pressure_kpa,
        pressure_psi=pressure.pressure_psi,
        vent_flow_m3_s=flow,
        vent_velocity_m_s=velocity,
        reset_time_s=reset_time_s,
        reset_time_min=reset_time_s / SECONDS_PER_MINUTE if math.isfinite(reset_time_s) else math.inf,
        status=status,
    )


def build_pressure_table(inputs: VentResetInputs = VentResetInputs()) -> tuple[PressureRow, ...]:
    return tuple(pressure_row(depth, inputs) for depth in inputs.depth_values_m)


def build_vent_reset_table(inputs: VentResetInputs = VentResetInputs()) -> tuple[VentResetRow, ...]:
    rows: list[VentResetRow] = []
    for depth in inputs.depth_values_m:
        for event_volume in inputs.event_volumes_m3:
            for vent_area in inputs.vent_areas_m2:
                rows.append(evaluate_vent_reset(depth, event_volume, vent_area, inputs))
    return tuple(rows)


def fmt_float(value: float, digits: int = 3) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.{digits}f}"


def print_pressure_table(rows: Iterable[PressureRow]) -> None:
    print("\nDepth-pressure table")
    print(f"{'depth_m':>8} {'pressure_kPa':>14} {'pressure_psi':>14}")
    for row in rows:
        print(f"{row.depth_m:8.1f} {row.pressure_kpa:14.1f} {row.pressure_psi:14.2f}")


def print_vent_reset_table(rows: Iterable[VentResetRow]) -> None:
    print("\nVent/reset table")
    print(
        f"{'depth_m':>7} {'event_m3':>9} {'vent_m2':>9} {'psi':>8} "
        f"{'flow_m3_s':>11} {'time_s':>10} {'time_min':>10} {'status':>18}"
    )
    for row in rows:
        print(
            f"{row.depth_m:7.1f} "
            f"{row.event_volume_m3:9.1f} "
            f"{row.vent_area_m2:9.4f} "
            f"{row.pressure_psi:8.2f} "
            f"{row.vent_flow_m3_s:11.3f} "
            f"{fmt_float(row.reset_time_s, 2):>10} "
            f"{fmt_float(row.reset_time_min, 2):>10} "
            f"{row.status:>18}"
        )


def export_vent_reset_csv(
    rows: Iterable[VentResetRow],
    path: Path | str = "vent_reset_summary.csv",
) -> Path:
    csv_path = Path(path)
    fieldnames = [
        "depth_m",
        "event_volume_m3",
        "vent_area_m2",
        "pressure_pa",
        "pressure_kpa",
        "pressure_psi",
        "vent_flow_m3_s",
        "vent_velocity_m_s",
        "reset_time_s",
        "reset_time_min",
        "status",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            data = asdict(row)
            if math.isinf(data["reset_time_s"]):
                data["reset_time_s"] = "inf"
            if math.isinf(data["reset_time_min"]):
                data["reset_time_min"] = "inf"
            writer.writerow(data)
    return csv_path


def print_gate_summary(rows: Iterable[VentResetRow]) -> None:
    row_tuple = tuple(rows)
    statuses = {row.status for row in row_tuple}
    controlled = [row for row in row_tuple if row.status == "controlled_reset"]
    overviolent = [row for row in row_tuple if row.status == "overviolent"]
    weak = [row for row in row_tuple if row.status == "weak_vent"]

    print("\nGate summary")
    print("- Depth-to-pressure gate: passes screen for the target 43-50 psi band at 30-35 m.")
    print("- Sealed chamber pressure safety: fails; no vent path means displaced air has no reset path.")
    if controlled:
        print("- Vented reset gate: controlled_reset cases exist under candidate vent areas/event volumes.")
    else:
        print("- Vented reset gate: no controlled_reset case found under this parameter set.")
    if weak:
        print("- Weak vent cases remain where reset time is too long for the practical threshold.")
    if overviolent:
        print("- Overviolent cases appear where air flow is large enough to be destructive or unstable.")
    print("- Reset remains conditional on actual vent geometry, continuity, blockage, sealing, and erosion limits.")
    print(f"- Statuses observed: {', '.join(sorted(statuses))}")


def print_boundary() -> None:
    print("\nBoundary")
    print("This simulation does not prove historical use.")
    print("It does not prove the feed path existed.")
    print("It tests whether the lower chamber could be pressure-safe only if vent/reset capacity exists.")
    print("Sealed pressure fails; vent/reset is the candidate rescue.")


def run(inputs: VentResetInputs = VentResetInputs()) -> None:
    pressure_rows = build_pressure_table(inputs)
    vent_rows = build_vent_reset_table(inputs)
    print("Giza Lower-Node Vent/Reset Pressure Screen")
    print_boundary()
    print_pressure_table(pressure_rows)
    print_vent_reset_table(vent_rows)
    print_gate_summary(vent_rows)
    csv_path = export_vent_reset_csv(vent_rows)
    print(f"\nCSV export: {csv_path.resolve()}")


if __name__ == "__main__":
    run()
