"""Giza lower-node residue prediction gate.

This is an engineering/archaeological prediction screen only. It does not treat
residues as proof. It creates spatial predictions and falsifiers: residue
chemistry only matters if it respects system geometry and contamination
controls.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Literal


ZoneClass = Literal["strong_expected", "moderate_expected", "weak_expected"]
SupportStatus = Literal["supports_screen", "weak_support", "fails_pattern"]

RESIDUE_CLASSES = (
    "carbonate",
    "sulfate",
    "chloride/salt",
    "gypsum",
    "alum/metal-sulfate",
    "clay/silt sediment",
)


@dataclass(frozen=True)
class ZoneInput:
    zone: str
    wet_exposure_score: float
    flow_velocity_score: float
    evaporation_score: float
    choke_boundary_score: float
    contamination_risk_score: float
    modern_access_risk_score: float

    def __post_init__(self) -> None:
        values = (
            self.wet_exposure_score,
            self.flow_velocity_score,
            self.evaporation_score,
            self.choke_boundary_score,
            self.contamination_risk_score,
            self.modern_access_risk_score,
        )
        if any(value < 0.0 or value > 1.0 for value in values):
            raise ValueError("zone scores must be between 0 and 1")


@dataclass(frozen=True)
class ZonePrediction:
    zone: str
    wet_exposure_score: float
    flow_velocity_score: float
    evaporation_score: float
    choke_boundary_score: float
    contamination_risk_score: float
    modern_access_risk_score: float
    low_flow_deposition_score: float
    sediment_capture_score: float
    residue_signal: float
    adjusted_signal: float
    classification: ZoneClass
    expected_residue_classes: tuple[str, ...]


@dataclass(frozen=True)
class BoundaryContrasts:
    lower_vs_upper_ratio: float
    plug_upstream_vs_downstream_ratio: float
    plug_interface_vs_general_passage_ratio: float


@dataclass(frozen=True)
class ResidueGateOutputs:
    predictions: tuple[ZonePrediction, ...]
    hotspots: tuple[ZonePrediction, ...]
    contrasts: BoundaryContrasts
    support_status: SupportStatus
    falsifier_summary: tuple[str, ...]
    validation_needed: tuple[str, ...]


def default_zone_inputs() -> tuple[ZoneInput, ...]:
    return (
        ZoneInput("lower_chamber", 1.0, 0.3, 0.7, 0.2, 0.4, 0.5),
        ZoneInput("descending_passage_lower", 0.8, 0.6, 0.5, 0.1, 0.4, 0.6),
        ZoneInput("subterranean_horizontal_passage", 0.9, 0.5, 0.6, 0.2, 0.3, 0.4),
        ZoneInput("well_shaft_lower", 0.7, 0.7, 0.6, 0.4, 0.4, 0.6),
        ZoneInput("plug_upstream_face", 0.9, 0.4, 0.8, 1.0, 0.2, 0.3),
        ZoneInput("plug_interfaces", 0.8, 0.8, 0.9, 1.0, 0.2, 0.3),
        ZoneInput("plug_downstream_face", 0.3, 0.2, 0.5, 0.6, 0.3, 0.5),
        ZoneInput("ascending_passage_above_plugs", 0.2, 0.2, 0.4, 0.1, 0.5, 0.7),
        ZoneInput("grand_gallery_lower", 0.15, 0.2, 0.4, 0.1, 0.5, 0.7),
        ZoneInput("king_chamber_zone", 0.05, 0.1, 0.3, 0.0, 0.4, 0.8),
    )


def residue_signal(zone: ZoneInput) -> float:
    low_flow_deposition = 1.0 - zone.flow_velocity_score
    sediment_capture = zone.wet_exposure_score * low_flow_deposition
    return (
        0.35 * zone.wet_exposure_score
        + 0.20 * zone.evaporation_score
        + 0.20 * zone.choke_boundary_score
        + 0.15 * low_flow_deposition
        + 0.10 * sediment_capture
    )


def adjusted_signal(zone: ZoneInput) -> float:
    raw = residue_signal(zone)
    return raw * (1.0 - 0.5 * zone.contamination_risk_score) * (1.0 - 0.5 * zone.modern_access_risk_score)


def classify_signal(signal: float) -> ZoneClass:
    if signal >= 0.65:
        return "strong_expected"
    if signal >= 0.35:
        return "moderate_expected"
    return "weak_expected"


def expected_residue_classes(zone: ZoneInput) -> tuple[str, ...]:
    classes: list[str] = []
    if zone.wet_exposure_score >= 0.5:
        classes.extend(["carbonate", "sulfate", "gypsum"])
    if zone.evaporation_score >= 0.5:
        classes.append("chloride/salt")
    if zone.choke_boundary_score >= 0.5:
        classes.append("alum/metal-sulfate")
    if zone.wet_exposure_score >= 0.5 and zone.flow_velocity_score <= 0.6:
        classes.append("clay/silt sediment")
    if not classes:
        classes.append("low/background residue")
    return tuple(dict.fromkeys(classes))


def predict_zone(zone: ZoneInput) -> ZonePrediction:
    low_flow = 1.0 - zone.flow_velocity_score
    sediment_capture = zone.wet_exposure_score * low_flow
    raw = residue_signal(zone)
    adjusted = adjusted_signal(zone)
    return ZonePrediction(
        zone=zone.zone,
        wet_exposure_score=zone.wet_exposure_score,
        flow_velocity_score=zone.flow_velocity_score,
        evaporation_score=zone.evaporation_score,
        choke_boundary_score=zone.choke_boundary_score,
        contamination_risk_score=zone.contamination_risk_score,
        modern_access_risk_score=zone.modern_access_risk_score,
        low_flow_deposition_score=low_flow,
        sediment_capture_score=sediment_capture,
        residue_signal=raw,
        adjusted_signal=adjusted,
        classification=classify_signal(adjusted),
        expected_residue_classes=expected_residue_classes(zone),
    )


def safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return float("inf") if numerator > 0 else 1.0
    return numerator / denominator


def mean_signal(predictions: Iterable[ZonePrediction], zones: set[str]) -> float:
    selected = [prediction.adjusted_signal for prediction in predictions if prediction.zone in zones]
    if not selected:
        return 0.0
    return sum(selected) / len(selected)


def get_prediction(predictions: Iterable[ZonePrediction], zone: str) -> ZonePrediction:
    for prediction in predictions:
        if prediction.zone == zone:
            return prediction
    raise KeyError(zone)


def compute_contrasts(predictions: tuple[ZonePrediction, ...]) -> BoundaryContrasts:
    lower_zones = {
        "lower_chamber",
        "descending_passage_lower",
        "subterranean_horizontal_passage",
        "well_shaft_lower",
        "plug_upstream_face",
        "plug_interfaces",
    }
    upper_zones = {
        "ascending_passage_above_plugs",
        "grand_gallery_lower",
        "king_chamber_zone",
    }
    general_passage_zones = {
        "descending_passage_lower",
        "subterranean_horizontal_passage",
        "well_shaft_lower",
    }
    plug_upstream = get_prediction(predictions, "plug_upstream_face").adjusted_signal
    plug_interfaces = get_prediction(predictions, "plug_interfaces").adjusted_signal
    plug_downstream = get_prediction(predictions, "plug_downstream_face").adjusted_signal
    return BoundaryContrasts(
        lower_vs_upper_ratio=safe_ratio(mean_signal(predictions, lower_zones), mean_signal(predictions, upper_zones)),
        plug_upstream_vs_downstream_ratio=safe_ratio(plug_upstream, plug_downstream),
        plug_interface_vs_general_passage_ratio=safe_ratio(
            plug_interfaces,
            mean_signal(predictions, general_passage_zones),
        ),
    )


def assess_support(
    predictions: tuple[ZonePrediction, ...],
    contrasts: BoundaryContrasts,
) -> tuple[SupportStatus, tuple[str, ...]]:
    lower_mean = mean_signal(
        predictions,
        {
            "lower_chamber",
            "descending_passage_lower",
            "subterranean_horizontal_passage",
            "well_shaft_lower",
        },
    )
    upper_mean = mean_signal(
        predictions,
        {"ascending_passage_above_plugs", "grand_gallery_lower", "king_chamber_zone"},
    )
    plug_upstream = get_prediction(predictions, "plug_upstream_face").adjusted_signal
    plug_interfaces = get_prediction(predictions, "plug_interfaces").adjusted_signal
    plug_downstream = get_prediction(predictions, "plug_downstream_face").adjusted_signal
    contamination_mean = sum(
        (prediction.contamination_risk_score + prediction.modern_access_risk_score) / 2.0
        for prediction in predictions
    ) / len(predictions)
    spread = max(prediction.adjusted_signal for prediction in predictions) - min(
        prediction.adjusted_signal for prediction in predictions
    )

    messages: list[str] = []
    if spread < 0.15:
        messages.append("Residue predictions are near-uniform; spatial pattern support weakens.")
    if upper_mean >= lower_mean:
        messages.append("Upper finished zones equal or exceed lower-zone wet signature; model weakens.")
    if plug_upstream <= plug_downstream:
        messages.append("Plug upstream face does not exceed downstream face; plug-boundary contrast weakens.")
    if plug_interfaces <= plug_downstream:
        messages.append("Plug interfaces do not exceed downstream face; choke/isolation contrast weakens.")
    if contamination_mean >= 0.75:
        messages.append("Contamination/modern-access risk is high enough to dominate interpretation.")

    strong_pattern = (
        contrasts.lower_vs_upper_ratio > 1.25
        and contrasts.plug_upstream_vs_downstream_ratio > 1.10
        and contrasts.plug_interface_vs_general_passage_ratio > 1.05
        and contamination_mean < 0.75
        and spread >= 0.15
    )
    weak_pattern = (
        contrasts.lower_vs_upper_ratio > 1.0
        and contrasts.plug_upstream_vs_downstream_ratio > 1.0
        and contamination_mean < 0.85
        and spread >= 0.10
    )

    if strong_pattern:
        messages.append("Pattern follows lower wet zones and plug/choke boundary contrasts.")
        return "supports_screen", tuple(messages)
    if weak_pattern:
        messages.append("Pattern has partial boundary structure but remains validation-sensitive.")
        return "weak_support", tuple(messages)
    if not messages:
        messages.append("Pattern does not produce enough boundary contrast under current inputs.")
    return "fails_pattern", tuple(messages)


def evaluate_residue_gate(zones: Iterable[ZoneInput] | None = None) -> ResidueGateOutputs:
    zone_inputs = tuple(zones) if zones is not None else default_zone_inputs()
    predictions = tuple(predict_zone(zone) for zone in zone_inputs)
    hotspots = tuple(sorted(predictions, key=lambda row: row.adjusted_signal, reverse=True))
    contrasts = compute_contrasts(predictions)
    support_status, falsifier_summary = assess_support(predictions, contrasts)
    return ResidueGateOutputs(
        predictions=predictions,
        hotspots=hotspots,
        contrasts=contrasts,
        support_status=support_status,
        falsifier_summary=falsifier_summary,
        validation_needed=(
            "zone-by-zone mineral species map",
            "contamination and modern-access controls",
            "plug upstream/downstream/interface sampling",
            "lower-vs-upper substrate-specific residue comparison",
            "independent explanation testing for any upper wet signature",
        ),
    )


def export_csv(
    predictions: Iterable[ZonePrediction],
    path: Path | str = "giza_residue_prediction_gate.csv",
) -> Path:
    csv_path = Path(path)
    fieldnames = [
        "zone",
        "wet_exposure_score",
        "flow_velocity_score",
        "evaporation_score",
        "choke_boundary_score",
        "contamination_risk_score",
        "modern_access_risk_score",
        "low_flow_deposition_score",
        "sediment_capture_score",
        "residue_signal",
        "adjusted_signal",
        "classification",
        "expected_residue_classes",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for prediction in predictions:
            data = asdict(prediction)
            data["expected_residue_classes"] = "; ".join(prediction.expected_residue_classes)
            writer.writerow(data)
    return csv_path


def print_boundary() -> None:
    print("Boundary")
    print("This does not treat residues as proof.")
    print("It creates spatial predictions and falsifiers.")
    print("Residue chemistry only matters if it respects system geometry and contamination controls.")


def print_prediction_table(predictions: Iterable[ZonePrediction]) -> None:
    print("\nZone predictions")
    print(
        f"{'zone':>36} {'raw':>7} {'adjusted':>9} {'class':>18} "
        f"{'contam':>7} {'modern':>7} residues"
    )
    for row in predictions:
        residues = ", ".join(row.expected_residue_classes)
        print(
            f"{row.zone:>36} "
            f"{row.residue_signal:7.3f} "
            f"{row.adjusted_signal:9.3f} "
            f"{row.classification:>18} "
            f"{row.contamination_risk_score:7.2f} "
            f"{row.modern_access_risk_score:7.2f} "
            f"{residues}"
        )


def print_hotspots(hotspots: Iterable[ZonePrediction]) -> None:
    print("\nRanked expected residue hotspots")
    for index, row in enumerate(hotspots, start=1):
        print(f"{index:2d}. {row.zone}: adjusted_signal={row.adjusted_signal:.3f} ({row.classification})")


def print_contrasts(contrasts: BoundaryContrasts) -> None:
    print("\nBoundary contrast ratios")
    print(f"- lower_vs_upper_ratio: {contrasts.lower_vs_upper_ratio:.3f}")
    print(f"- plug_upstream_vs_downstream_ratio: {contrasts.plug_upstream_vs_downstream_ratio:.3f}")
    print(f"- plug_interface_vs_general_passage_ratio: {contrasts.plug_interface_vs_general_passage_ratio:.3f}")


def print_falsifier_summary(outputs: ResidueGateOutputs) -> None:
    print("\nFalsifier summary")
    print(f"Support status: {outputs.support_status}")
    for message in outputs.falsifier_summary:
        print(f"- {message}")
    print("\nValidation needed")
    for item in outputs.validation_needed:
        print(f"- {item}")


def run() -> None:
    outputs = evaluate_residue_gate()
    print("Giza Residue Prediction Gate\n")
    print_boundary()
    print_prediction_table(outputs.predictions)
    print_hotspots(outputs.hotspots)
    print_contrasts(outputs.contrasts)
    print_falsifier_summary(outputs)
    csv_path = export_csv(outputs.predictions)
    print(f"\nCSV export: {csv_path.resolve()}")


if __name__ == "__main__":
    run()
