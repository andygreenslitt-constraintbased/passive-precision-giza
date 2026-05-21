"""Giza lower-node vent choke calibration screen.

This is an engineering screening model only. It does not prove the feed path
existed, does not prove historical hydraulic use, and does not claim water
moved every block. It tests whether observed large passages require smaller
effective choke control to make a lower-node pressure/reset system manageable.
"""

from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Literal


Status = Literal["sealed_fail", "weak_vent", "controlled_reset", "overviolent"]

PA_PER_PSI = 6894.757293168


@dataclass(frozen=True)
class ChokeCalibrationInputs:
    depth_values_m: tuple[float, ...] = (30.0, 35.0)
    event_volumes_m3: tuple[float, ...] = (1.0, 5.0, 10.0, 25.0, 50.0)
    tested_choke_areas_m2: tuple[float, ...] = (
        0.0,
        0.0005,
        0.001,
        0.0025,
        0.005,
        0.01,
        0.02,
        0.05,
        0.1,
        0.25,
        0.5,
        0.79,
        1.26,
    )
    descending_passage_area_m2: float = 1.26
    subterranean_horizontal_passage_area_m2: float = 0.79
    discharge_coefficient: float = 0.62
    air_density_kg_m3: float = 1.2
    water_density_kg_m3: float = 1000.0
    gravity_m_s2: float = 9.81
    weak_reset_time_s: float = 300.0
    controlled_min_time_s: float = 5.0
    overviolent_velocity_m_s: float = 300.0
    overviolent_flow_m3_s: float = 10.0

    def __post_init__(self) -> None:
        if any(depth <= 0 for depth in self.depth_values_m):
            raise ValueError("depth values must be positive")
        if any(volume <= 0 for volume in self.event_volumes_m3):
            raise ValueError("event volumes must be positive")
        if any(area < 0 for area in self.tested_choke_areas_m2):
            raise ValueError("choke areas must be non-negative")
        if self.descending_passage_area_m2 <= 0 or self.subterranean_horizontal_passage_area_m2 <= 0:
            raise ValueError("observed passage areas must be positive")
        if self.discharge_coefficient <= 0:
            raise ValueError("discharge coefficient must be positive")
        if self.air_density_kg_m3 <= 0 or self.water_density_kg_m3 <= 0:
            raise ValueError("densities must be positive")
        if self.gravity_m_s2 <= 0:
            raise ValueError("gravity must be positive")
        if self.weak_reset_time_s <= 0 or self.controlled_min_time_s <= 0:
            raise ValueError("time thresholds must be positive")
        if self.overviolent_velocity_m_s <= 0 or self.overviolent_flow_m3_s <= 0:
            raise ValueError("overviolent thresholds must be positive")


@dataclass(frozen=True)
class ChokeRow:
    depth_m: float
    pressure_psi: float
    pressure_kpa: float
    event_volume_m3: float
    choke_area_m2: float
    flow_m3_s: float
    velocity_m_s: float
    reset_time_s: float
    reset_time_min: float
    status: Status


@dataclass(frozen=True)
class OperatingBand:
    depth_m: float
    event_volume_m3: float
    minimum_choke_area_avoids_weak_m2: float | None
    maximum_choke_area_before_overviolent_m2: float | None
    controlled_min_area_m2: float | None
    controlled_max_area_m2: float | None
    controlled_count: int
    gross_079_status: Status
    gross_126_status: Status


def pressure_from_depth_pa(
    depth_m: float,
    rho_water_kg_m3: float = 1000.0,
    gravity_m_s2: float = 9.81,
) -> float:
    if depth_m <= 0:
        raise ValueError("depth_m must be positive")
    if rho_water_kg_m3 <= 0 or gravity_m_s2 <= 0:
        raise ValueError("density and gravity must be positive")
    return rho_water_kg_m3 * gravity_m_s2 * depth_m


def pa_to_psi(pressure_pa: float) -> float:
    return pressure_pa / PA_PER_PSI


def orifice_air_flow_m3_s(
    delta_p_pa: float,
    choke_area_m2: float,
    discharge_coefficient: float = 0.62,
    air_density_kg_m3: float = 1.2,
) -> float:
    if delta_p_pa < 0:
        raise ValueError("delta_p_pa must be non-negative")
    if choke_area_m2 < 0:
        raise ValueError("choke_area_m2 must be non-negative")
    if discharge_coefficient <= 0 or air_density_kg_m3 <= 0:
        raise ValueError("discharge coefficient and air density must be positive")
    if delta_p_pa == 0 or choke_area_m2 == 0:
        return 0.0
    return discharge_coefficient * choke_area_m2 * math.sqrt(2.0 * delta_p_pa / air_density_kg_m3)


def classify_choke(
    choke_area_m2: float,
    flow_m3_s: float,
    velocity_m_s: float,
    reset_time_s: float,
    inputs: ChokeCalibrationInputs = ChokeCalibrationInputs(),
) -> Status:
    if choke_area_m2 <= 0:
        return "sealed_fail"
    # The simple incompressible orifice equation yields sonic-scale jet velocity
    # for all positive apertures at 43-50 psi. In this screening model, the
    # destructive overviolent class is assigned when that velocity is paired
    # with damaging bulk discharge, while the raw velocity is still reported.
    if (
        (reset_time_s < inputs.controlled_min_time_s and flow_m3_s >= inputs.overviolent_flow_m3_s)
        or (velocity_m_s >= inputs.overviolent_velocity_m_s and flow_m3_s >= inputs.overviolent_flow_m3_s)
        or flow_m3_s >= inputs.overviolent_flow_m3_s
    ):
        return "overviolent"
    if reset_time_s > inputs.weak_reset_time_s:
        return "weak_vent"
    return "controlled_reset"


def evaluate_choke(
    depth_m: float,
    event_volume_m3: float,
    choke_area_m2: float,
    inputs: ChokeCalibrationInputs = ChokeCalibrationInputs(),
) -> ChokeRow:
    if event_volume_m3 <= 0:
        raise ValueError("event_volume_m3 must be positive")
    if choke_area_m2 < 0:
        raise ValueError("choke_area_m2 must be non-negative")
    pressure_pa = pressure_from_depth_pa(depth_m, inputs.water_density_kg_m3, inputs.gravity_m_s2)
    flow = orifice_air_flow_m3_s(
        pressure_pa,
        choke_area_m2,
        inputs.discharge_coefficient,
        inputs.air_density_kg_m3,
    )
    velocity = flow / choke_area_m2 if choke_area_m2 > 0 else 0.0
    reset_time_s = event_volume_m3 / flow if flow > 0 else math.inf
    status = classify_choke(choke_area_m2, flow, velocity, reset_time_s, inputs)
    return ChokeRow(
        depth_m=depth_m,
        pressure_psi=pa_to_psi(pressure_pa),
        pressure_kpa=pressure_pa / 1000.0,
        event_volume_m3=event_volume_m3,
        choke_area_m2=choke_area_m2,
        flow_m3_s=flow,
        velocity_m_s=velocity,
        reset_time_s=reset_time_s,
        reset_time_min=reset_time_s / 60.0 if math.isfinite(reset_time_s) else math.inf,
        status=status,
    )


def build_rows(inputs: ChokeCalibrationInputs = ChokeCalibrationInputs()) -> tuple[ChokeRow, ...]:
    rows: list[ChokeRow] = []
    for depth in inputs.depth_values_m:
        for event_volume in inputs.event_volumes_m3:
            for area in inputs.tested_choke_areas_m2:
                rows.append(evaluate_choke(depth, event_volume, area, inputs))
    return tuple(rows)


def find_row(rows: Iterable[ChokeRow], depth_m: float, event_volume_m3: float, choke_area_m2: float) -> ChokeRow:
    for row in rows:
        if (
            math.isclose(row.depth_m, depth_m)
            and math.isclose(row.event_volume_m3, event_volume_m3)
            and math.isclose(row.choke_area_m2, choke_area_m2)
        ):
            return row
    raise LookupError("matching choke row not found")


def compute_operating_bands(
    rows: Iterable[ChokeRow],
    inputs: ChokeCalibrationInputs = ChokeCalibrationInputs(),
) -> tuple[OperatingBand, ...]:
    row_tuple = tuple(rows)
    bands: list[OperatingBand] = []
    for depth in inputs.depth_values_m:
        for event_volume in inputs.event_volumes_m3:
            group = [
                row
                for row in row_tuple
                if math.isclose(row.depth_m, depth) and math.isclose(row.event_volume_m3, event_volume)
            ]
            non_weak = [
                row
                for row in group
                if row.choke_area_m2 > 0 and row.status in ("controlled_reset", "overviolent")
            ]
            non_overviolent = [
                row
                for row in group
                if row.choke_area_m2 > 0 and row.status in ("weak_vent", "controlled_reset")
            ]
            controlled = [row for row in group if row.status == "controlled_reset"]
            gross_079 = find_row(group, depth, event_volume, inputs.subterranean_horizontal_passage_area_m2)
            gross_126 = find_row(group, depth, event_volume, inputs.descending_passage_area_m2)
            bands.append(
                OperatingBand(
                    depth_m=depth,
                    event_volume_m3=event_volume,
                    minimum_choke_area_avoids_weak_m2=min(
                        (row.choke_area_m2 for row in non_weak),
                        default=None,
                    ),
                    maximum_choke_area_before_overviolent_m2=max(
                        (row.choke_area_m2 for row in non_overviolent),
                        default=None,
                    ),
                    controlled_min_area_m2=min((row.choke_area_m2 for row in controlled), default=None),
                    controlled_max_area_m2=max((row.choke_area_m2 for row in controlled), default=None),
                    controlled_count=len(controlled),
                    gross_079_status=gross_079.status,
                    gross_126_status=gross_126.status,
                )
            )
    return tuple(bands)


def export_csv(rows: Iterable[ChokeRow], path: Path | str = "giza_vent_choke_calibration.csv") -> Path:
    csv_path = Path(path)
    fieldnames = [
        "depth_m",
        "pressure_psi",
        "pressure_kpa",
        "event_volume_m3",
        "choke_area_m2",
        "flow_m3_s",
        "velocity_m_s",
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


def fmt(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "-"
    if math.isinf(value):
        return "inf"
    return f"{value:.{digits}f}"


def print_boundary() -> None:
    print("Boundary")
    print("This does not prove the feed path existed.")
    print("This does not prove historical hydraulic use.")
    print("This does not claim water moved every block.")
    print(
        "It tests whether observed large passages require smaller effective choke control "
        "to make the lower-node pressure system manageable."
    )


def print_depth_pressure_table(inputs: ChokeCalibrationInputs) -> None:
    print("\nDepth-pressure table")
    print(f"{'depth_m':>8} {'pressure_kPa':>14} {'pressure_psi':>14}")
    for depth in inputs.depth_values_m:
        pressure_pa = pressure_from_depth_pa(depth, inputs.water_density_kg_m3, inputs.gravity_m_s2)
        print(f"{depth:8.1f} {pressure_pa / 1000.0:14.1f} {pa_to_psi(pressure_pa):14.2f}")


def print_choke_table(rows: Iterable[ChokeRow]) -> None:
    print("\nChoke calibration table")
    print(
        f"{'depth_m':>7} {'psi':>8} {'event_m3':>9} {'area_m2':>9} "
        f"{'flow_m3_s':>11} {'vel_m_s':>10} {'time_s':>10} {'time_min':>10} {'status':>18}"
    )
    for row in rows:
        print(
            f"{row.depth_m:7.1f} "
            f"{row.pressure_psi:8.2f} "
            f"{row.event_volume_m3:9.1f} "
            f"{row.choke_area_m2:9.4f} "
            f"{row.flow_m3_s:11.3f} "
            f"{row.velocity_m_s:10.1f} "
            f"{fmt(row.reset_time_s, 2):>10} "
            f"{fmt(row.reset_time_min, 2):>10} "
            f"{row.status:>18}"
        )


def print_operating_bands(bands: Iterable[OperatingBand]) -> None:
    print("\nControlled operating bands")
    print(
        f"{'depth_m':>7} {'event_m3':>9} {'min_not_weak':>13} {'max_not_violent':>16} "
        f"{'controlled_band_m2':>22} {'n':>3} {'0.79_status':>14} {'1.26_status':>14}"
    )
    for band in bands:
        if band.controlled_min_area_m2 is None:
            controlled_band = "-"
        else:
            controlled_band = f"{band.controlled_min_area_m2:.4f}-{band.controlled_max_area_m2:.4f}"
        print(
            f"{band.depth_m:7.1f} "
            f"{band.event_volume_m3:9.1f} "
            f"{fmt(band.minimum_choke_area_avoids_weak_m2, 4):>13} "
            f"{fmt(band.maximum_choke_area_before_overviolent_m2, 4):>16} "
            f"{controlled_band:>22} "
            f"{band.controlled_count:3d} "
            f"{band.gross_079_status:>14} "
            f"{band.gross_126_status:>14}"
        )


def print_interpretation(rows: Iterable[ChokeRow], bands: Iterable[OperatingBand]) -> None:
    row_tuple = tuple(rows)
    band_tuple = tuple(bands)
    gross_rows = [row for row in row_tuple if math.isclose(row.choke_area_m2, 0.79) or math.isclose(row.choke_area_m2, 1.26)]
    gross_overviolent = any(row.status == "overviolent" for row in gross_rows)
    midrange_controlled = any(
        row.status == "controlled_reset" and 0.005 <= row.choke_area_m2 <= 0.05
        for row in row_tuple
    )
    controlled_exists = any(band.controlled_count > 0 for band in band_tuple)

    print("\nInterpretation")
    if gross_overviolent:
        print("- Observed gross passage areas 0.79 and/or 1.26 m2 are overviolent in this screen.")
        print("- Gross passage area is too large to be treated as the effective vent aperture.")
    else:
        print("- Observed gross passage areas do not become overviolent under this parameter set.")

    if midrange_controlled:
        print("- Smaller effective areas in the 0.005-0.05 m2 range can produce controlled reset cases.")
        print("- The system would require a choke, gate, partial obstruction, or equivalent effective aperture.")
    elif not controlled_exists:
        print("- No controlled band exists; the vent/reset gate fails under current assumptions.")
    else:
        print("- Controlled cases exist, but not in the nominal 0.005-0.05 m2 midrange.")

    print("- Effective choke geometry, blockage, erosion, acoustic shock, and sealing remain empirical.")


def run(inputs: ChokeCalibrationInputs = ChokeCalibrationInputs()) -> None:
    rows = build_rows(inputs)
    bands = compute_operating_bands(rows, inputs)
    print("Giza Vent Choke Calibration Screen\n")
    print_boundary()
    print_depth_pressure_table(inputs)
    print_choke_table(rows)
    print_operating_bands(bands)
    print_interpretation(rows, bands)
    csv_path = export_csv(rows)
    print(f"\nCSV export: {csv_path.resolve()}")


if __name__ == "__main__":
    run()
