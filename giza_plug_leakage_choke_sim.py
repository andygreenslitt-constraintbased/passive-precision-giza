"""Giza plug-interface leakage/choke screen.

This is an engineering screen only. It does not prove historical use, does not
claim the feed path existed, and does not claim the plugs were valves. It tests
whether small gaps around or between granite plugs could form an effective
choke area in the controlled-reset band found by prior lower-node screens.
"""

from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Literal


ChokeClass = Literal["sealed_too_tight", "controlled_choke", "over_open"]
ResetStatus = Literal["weak_vent", "controlled_reset", "overviolent", "sealed_fail"]
LeakageModel = Literal["perimeter_gap", "corner_gap", "joint_gap_between_plugs"]

PA_PER_PSI = 6894.757293168


@dataclass(frozen=True)
class PlugLeakageInputs:
    pressure_psi_values: tuple[float, ...] = (42.7, 49.8)
    plug_count: int = 3
    passage_width_m: float = 1.05
    passage_height_m: float = 1.20
    plug_lengths_m: tuple[float, ...] = (1.57, 1.67, 1.00)
    gap_heights_m: tuple[float, ...] = (0.0005, 0.001, 0.002, 0.005, 0.01, 0.02)
    leakage_models: tuple[LeakageModel, ...] = (
        "perimeter_gap",
        "corner_gap",
        "joint_gap_between_plugs",
    )
    efficiencies: tuple[float, ...] = (0.05, 0.10, 0.25, 0.50, 1.0)
    event_volumes_m3: tuple[float, ...] = (1.0, 5.0, 10.0, 25.0, 50.0)
    corner_count: int = 4
    corner_gap_width_m: float = 0.05
    min_controlled_area_m2: float = 0.005
    max_controlled_area_m2: float = 0.05
    discharge_coefficient: float = 0.62
    air_density_kg_m3: float = 1.2
    weak_reset_time_s: float = 300.0
    controlled_min_time_s: float = 5.0
    overviolent_flow_m3_s: float = 10.0

    def __post_init__(self) -> None:
        if any(pressure <= 0 for pressure in self.pressure_psi_values):
            raise ValueError("pressure values must be positive")
        if self.plug_count <= 0:
            raise ValueError("plug_count must be positive")
        if self.passage_width_m <= 0 or self.passage_height_m <= 0:
            raise ValueError("passage dimensions must be positive")
        if any(length <= 0 for length in self.plug_lengths_m):
            raise ValueError("plug lengths must be positive")
        if any(gap < 0 for gap in self.gap_heights_m):
            raise ValueError("gap heights must be non-negative")
        if any(eff < 0 for eff in self.efficiencies):
            raise ValueError("efficiencies must be non-negative")
        if any(volume <= 0 for volume in self.event_volumes_m3):
            raise ValueError("event volumes must be positive")
        if self.corner_count <= 0 or self.corner_gap_width_m <= 0:
            raise ValueError("corner geometry must be positive")
        if self.min_controlled_area_m2 <= 0 or self.max_controlled_area_m2 <= self.min_controlled_area_m2:
            raise ValueError("controlled area band must be positive and ordered")
        if self.discharge_coefficient <= 0 or self.air_density_kg_m3 <= 0:
            raise ValueError("flow constants must be positive")
        if self.weak_reset_time_s <= 0 or self.controlled_min_time_s <= 0:
            raise ValueError("time thresholds must be positive")
        if self.overviolent_flow_m3_s <= 0:
            raise ValueError("overviolent flow threshold must be positive")


@dataclass(frozen=True)
class GapAreaRow:
    leakage_model: LeakageModel
    gap_height_m: float
    efficiency: float
    effective_leak_area_m2: float
    choke_classification: ChokeClass


@dataclass(frozen=True)
class ResetRow:
    leakage_model: LeakageModel
    gap_height_m: float
    efficiency: float
    effective_leak_area_m2: float
    choke_classification: ChokeClass
    pressure_psi: float
    event_volume_m3: float
    flow_m3_s: float
    reset_time_s: float
    reset_time_min: float
    reset_status: ResetStatus


def passage_perimeter_m(width_m: float, height_m: float) -> float:
    if width_m <= 0 or height_m <= 0:
        raise ValueError("passage dimensions must be positive")
    return 2.0 * (width_m + height_m)


def pressure_psi_to_pa(pressure_psi: float) -> float:
    if pressure_psi <= 0:
        raise ValueError("pressure_psi must be positive")
    return pressure_psi * PA_PER_PSI


def effective_leak_area_m2(
    model: LeakageModel,
    gap_height_m: float,
    efficiency: float,
    inputs: PlugLeakageInputs = PlugLeakageInputs(),
) -> float:
    if gap_height_m < 0:
        raise ValueError("gap_height_m must be non-negative")
    if efficiency < 0:
        raise ValueError("efficiency must be non-negative")
    if model == "perimeter_gap":
        raw_area = passage_perimeter_m(inputs.passage_width_m, inputs.passage_height_m) * gap_height_m
    elif model == "corner_gap":
        raw_area = inputs.corner_count * inputs.corner_gap_width_m * gap_height_m
    elif model == "joint_gap_between_plugs":
        raw_area = inputs.passage_width_m * gap_height_m
    else:
        raise ValueError(f"unknown leakage model: {model}")
    return raw_area * efficiency


def classify_choke_area(
    area_m2: float,
    inputs: PlugLeakageInputs = PlugLeakageInputs(),
) -> ChokeClass:
    if area_m2 < inputs.min_controlled_area_m2:
        return "sealed_too_tight"
    if area_m2 <= inputs.max_controlled_area_m2:
        return "controlled_choke"
    return "over_open"


def orifice_air_flow_m3_s(
    pressure_psi: float,
    area_m2: float,
    inputs: PlugLeakageInputs = PlugLeakageInputs(),
) -> float:
    if area_m2 <= 0:
        return 0.0
    pressure_pa = pressure_psi_to_pa(pressure_psi)
    return inputs.discharge_coefficient * area_m2 * math.sqrt(2.0 * pressure_pa / inputs.air_density_kg_m3)


def classify_reset(
    area_m2: float,
    flow_m3_s: float,
    reset_time_s: float,
    inputs: PlugLeakageInputs = PlugLeakageInputs(),
) -> ResetStatus:
    if area_m2 <= 0 or flow_m3_s <= 0:
        return "sealed_fail"
    if reset_time_s < inputs.controlled_min_time_s or flow_m3_s >= inputs.overviolent_flow_m3_s:
        return "overviolent"
    if reset_time_s > inputs.weak_reset_time_s:
        return "weak_vent"
    return "controlled_reset"


def evaluate_gap_area(
    model: LeakageModel,
    gap_height_m: float,
    efficiency: float,
    inputs: PlugLeakageInputs = PlugLeakageInputs(),
) -> GapAreaRow:
    area = effective_leak_area_m2(model, gap_height_m, efficiency, inputs)
    return GapAreaRow(
        leakage_model=model,
        gap_height_m=gap_height_m,
        efficiency=efficiency,
        effective_leak_area_m2=area,
        choke_classification=classify_choke_area(area, inputs),
    )


def evaluate_reset(
    model: LeakageModel,
    gap_height_m: float,
    efficiency: float,
    pressure_psi: float,
    event_volume_m3: float,
    inputs: PlugLeakageInputs = PlugLeakageInputs(),
) -> ResetRow:
    if event_volume_m3 <= 0:
        raise ValueError("event_volume_m3 must be positive")
    gap_row = evaluate_gap_area(model, gap_height_m, efficiency, inputs)
    flow = orifice_air_flow_m3_s(pressure_psi, gap_row.effective_leak_area_m2, inputs)
    reset_time_s = event_volume_m3 / flow if flow > 0 else math.inf
    return ResetRow(
        leakage_model=model,
        gap_height_m=gap_height_m,
        efficiency=efficiency,
        effective_leak_area_m2=gap_row.effective_leak_area_m2,
        choke_classification=gap_row.choke_classification,
        pressure_psi=pressure_psi,
        event_volume_m3=event_volume_m3,
        flow_m3_s=flow,
        reset_time_s=reset_time_s,
        reset_time_min=reset_time_s / 60.0 if math.isfinite(reset_time_s) else math.inf,
        reset_status=classify_reset(gap_row.effective_leak_area_m2, flow, reset_time_s, inputs),
    )


def build_gap_area_rows(inputs: PlugLeakageInputs = PlugLeakageInputs()) -> tuple[GapAreaRow, ...]:
    rows: list[GapAreaRow] = []
    for model in inputs.leakage_models:
        for gap_height in inputs.gap_heights_m:
            for efficiency in inputs.efficiencies:
                rows.append(evaluate_gap_area(model, gap_height, efficiency, inputs))
    return tuple(rows)


def build_reset_rows(inputs: PlugLeakageInputs = PlugLeakageInputs()) -> tuple[ResetRow, ...]:
    rows: list[ResetRow] = []
    for model in inputs.leakage_models:
        for gap_height in inputs.gap_heights_m:
            for efficiency in inputs.efficiencies:
                for pressure_psi in inputs.pressure_psi_values:
                    for event_volume in inputs.event_volumes_m3:
                        rows.append(evaluate_reset(model, gap_height, efficiency, pressure_psi, event_volume, inputs))
    return tuple(rows)


def export_csv(rows: Iterable[ResetRow], path: Path | str = "giza_plug_leakage_choke_summary.csv") -> Path:
    csv_path = Path(path)
    fieldnames = [
        "leakage_model",
        "gap_height_m",
        "efficiency",
        "effective_leak_area_m2",
        "choke_classification",
        "pressure_psi",
        "event_volume_m3",
        "flow_m3_s",
        "reset_time_s",
        "reset_time_min",
        "reset_status",
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


def fmt(value: float, digits: int = 4) -> str:
    if math.isinf(value):
        return "inf"
    return f"{value:.{digits}f}"


def print_boundary() -> None:
    print("Boundary")
    print("This is an engineering screen only.")
    print("It does not prove historical use.")
    print("It does not claim the plugs were valves.")
    print("It only tests whether plug-interface leakage could screen as a controlled choke or isolation boundary.")


def print_gap_area_table(rows: Iterable[GapAreaRow]) -> None:
    print("\nGap/effective-area table")
    print(f"{'model':>25} {'gap_mm':>9} {'eff':>7} {'area_m2':>12} {'classification':>20}")
    for row in rows:
        print(
            f"{row.leakage_model:>25} "
            f"{row.gap_height_m * 1000.0:9.2f} "
            f"{row.efficiency:7.2f} "
            f"{row.effective_leak_area_m2:12.5f} "
            f"{row.choke_classification:>20}"
        )


def print_reset_table(rows: Iterable[ResetRow]) -> None:
    print("\nPressure/event reset table")
    print(
        f"{'model':>25} {'gap_mm':>8} {'eff':>5} {'area_m2':>9} {'psi':>7} "
        f"{'event_m3':>9} {'flow':>10} {'time_s':>10} {'status':>18}"
    )
    for row in rows:
        print(
            f"{row.leakage_model:>25} "
            f"{row.gap_height_m * 1000.0:8.2f} "
            f"{row.efficiency:5.2f} "
            f"{row.effective_leak_area_m2:9.5f} "
            f"{row.pressure_psi:7.1f} "
            f"{row.event_volume_m3:9.1f} "
            f"{row.flow_m3_s:10.3f} "
            f"{fmt(row.reset_time_s, 2):>10} "
            f"{row.reset_status:>18}"
        )


def print_controlled_gap_summary(rows: Iterable[GapAreaRow]) -> None:
    print("\nControlled choke gap ranges")
    row_tuple = tuple(rows)
    for model in sorted({row.leakage_model for row in row_tuple}):
        model_rows = [row for row in row_tuple if row.leakage_model == model and row.choke_classification == "controlled_choke"]
        if not model_rows:
            print(f"- {model}: no controlled_choke gaps in tested sweep.")
            continue
        min_gap = min(row.gap_height_m for row in model_rows) * 1000.0
        max_gap = max(row.gap_height_m for row in model_rows) * 1000.0
        min_eff = min(row.efficiency for row in model_rows)
        max_eff = max(row.efficiency for row in model_rows)
        print(
            f"- {model}: controlled_choke appears from {min_gap:.2f}-{max_gap:.2f} mm "
            f"across efficiency {min_eff:.2f}-{max_eff:.2f}."
        )


def print_interpretation(area_rows: Iterable[GapAreaRow]) -> None:
    rows = tuple(area_rows)
    controlled = [row for row in rows if row.choke_classification == "controlled_choke"]
    perimeter_controlled = [row for row in controlled if row.leakage_model == "perimeter_gap"]
    huge_only = controlled and min(row.gap_height_m for row in controlled) > 0.01
    over_open = [row for row in rows if row.choke_classification == "over_open"]

    print("\nInterpretation")
    if controlled and not huge_only:
        print("- Millimeter-scale gaps can produce the 0.005-0.05 m2 effective choke band in this screen.")
        print("- Plug-interface leakage is a plausible choke mechanism candidate under stated assumptions.")
    elif huge_only:
        print("- Only large visible gaps reach the controlled band; plug leakage is weak under these assumptions.")
    else:
        print("- No tested plug-interface gaps reach the controlled choke band.")
    if over_open:
        print("- Some tested tolerances become over_open; additional packing/sealing would be required.")
    if perimeter_controlled:
        print("- Perimeter leakage is the strongest of the tested plug-interface area mechanisms.")
    print("- Do not claim the plugs were valves; claim only a screened choke/isolation-boundary possibility.")


def run(inputs: PlugLeakageInputs = PlugLeakageInputs()) -> None:
    area_rows = build_gap_area_rows(inputs)
    reset_rows = build_reset_rows(inputs)
    print("Giza Plug-Interface Leakage/Choke Screen\n")
    print_boundary()
    print(f"\nPassage perimeter: {passage_perimeter_m(inputs.passage_width_m, inputs.passage_height_m):.3f} m")
    print(f"Plug count: {inputs.plug_count}; plug lengths: {inputs.plug_lengths_m}")
    print_gap_area_table(area_rows)
    print_reset_table(reset_rows)
    print_controlled_gap_summary(area_rows)
    print_interpretation(area_rows)
    csv_path = export_csv(reset_rows)
    print(f"\nCSV export: {csv_path.resolve()}")


if __name__ == "__main__":
    run()
