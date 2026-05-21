"""Giza lower-node construction sequence/access gate.

This is an engineering sequence screen only. It does not prove historical use.
Passing the sequence only shows that no required access/timing contradiction is
detected under the proposed lower-node hydraulic/isolation model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


SequenceStatus = Literal["passes_screen", "conditional_pass", "fails_sequence"]


@dataclass(frozen=True)
class Phase:
    name: str
    required_access_paths: tuple[str, ...] = ()
    paths_blocked_after_phase: tuple[str, ...] = ()
    required_open_paths: tuple[str, ...] = ()
    required_components_existing: tuple[str, ...] = ()
    components_created: tuple[str, ...] = ()
    irreversible_actions: tuple[str, ...] = ()
    conflict_if: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class PhaseResult:
    phase_index: int
    phase_name: str
    status: str
    open_paths_before: tuple[str, ...]
    blocked_paths_after: tuple[str, ...]
    existing_components_after: tuple[str, ...]
    conflicts: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class OpenPathWindow:
    path: str
    first_required_phase: str
    last_required_phase: str
    blocked_after_phase: str | None
    purpose: str


@dataclass(frozen=True)
class SequenceOutputs:
    sequence_name: str
    status: SequenceStatus
    phase_results: tuple[PhaseResult, ...]
    conflicts: tuple[str, ...]
    warnings: tuple[str, ...]
    critical_dependencies: tuple[str, ...]
    irreversible_action_warnings: tuple[str, ...]
    open_path_windows: tuple[OpenPathWindow, ...]


INITIAL_OPEN_PATHS = frozenset(
    {
        "construction_site_access",
        "surface_feed_access",
        "descending_passage_access",
        "ascending_passage_access",
        "vent_reset_path",
        "upper_work_access",
        "plug_staging_access",
        "decommissioning_access",
    }
)


def canonical_phases() -> tuple[Phase, ...]:
    return (
        Phase(
            "cut_lower_node",
            required_access_paths=("construction_site_access", "descending_passage_access"),
            components_created=("lower_node",),
            notes="Create Subterranean Chamber / lower receiving node.",
        ),
        Phase(
            "cut_descending_passage",
            required_access_paths=("descending_passage_access",),
            components_created=("descending_passage",),
            notes="Create feed/access route toward lower node.",
        ),
        Phase(
            "establish_surface_feed_possible",
            required_access_paths=("surface_feed_access", "descending_passage_access"),
            required_components_existing=("lower_node", "descending_passage"),
            components_created=("surface_feed_possible",),
            notes="Screen only: possible feed window exists, not historical proof.",
        ),
        Phase(
            "build_lower_hydraulic_use_window",
            required_access_paths=("surface_feed_access", "descending_passage_access"),
            required_open_paths=("surface_feed_access", "descending_passage_access"),
            required_components_existing=("lower_node", "surface_feed_possible"),
            components_created=("lower_hydraulic_use_window",),
            notes="Lower system can only be used while feed/access remains open.",
        ),
        Phase(
            "cut_or_open_vent_reset_path",
            required_access_paths=("vent_reset_path",),
            required_components_existing=("lower_node",),
            components_created=("vent_reset_path_established",),
            notes="Air displacement/reset path must exist before pressure use.",
        ),
        Phase(
            "build_ascending_passage",
            required_access_paths=("ascending_passage_access",),
            components_created=("ascending_passage",),
            notes="Upper access route remains open.",
        ),
        Phase(
            "stage_granite_plugs",
            required_access_paths=("plug_staging_access", "ascending_passage_access"),
            required_components_existing=("ascending_passage",),
            components_created=("granite_plugs_staged",),
            notes="Plugs staged, not finally seated.",
        ),
        Phase(
            "use_lower_system_if_needed",
            required_access_paths=("surface_feed_access", "descending_passage_access", "vent_reset_path"),
            required_open_paths=("surface_feed_access", "descending_passage_access", "vent_reset_path"),
            required_components_existing=(
                "lower_node",
                "surface_feed_possible",
                "vent_reset_path_established",
                "lower_hydraulic_use_window",
            ),
            components_created=("lower_system_used_or_screened",),
            conflict_if=("granite_plugs_seated", "lower_system_shutdown"),
            notes="Hydraulic/air-management use window; not a claim of historical use.",
        ),
        Phase(
            "complete_upper_chamber_zone",
            required_access_paths=("ascending_passage_access", "upper_work_access"),
            required_open_paths=("ascending_passage_access", "upper_work_access"),
            required_components_existing=("ascending_passage",),
            components_created=("upper_chamber_zone_complete",),
            conflict_if=("granite_plugs_seated",),
            notes="Upper chamber / Grand Gallery work must precede final plug isolation.",
        ),
        Phase(
            "final_lower_system_shutdown",
            required_access_paths=("descending_passage_access", "vent_reset_path"),
            required_open_paths=("descending_passage_access", "vent_reset_path"),
            required_components_existing=("lower_system_used_or_screened",),
            components_created=("lower_system_shutdown",),
            irreversible_actions=("wet_lower_domain_shutdown",),
            conflict_if=("granite_plugs_seated",),
            notes="Drain/reset/shut down lower wet/air domain before isolation.",
        ),
        Phase(
            "seat_granite_plugs",
            required_access_paths=("plug_staging_access", "ascending_passage_access"),
            required_components_existing=("granite_plugs_staged", "upper_chamber_zone_complete", "lower_system_shutdown"),
            components_created=("granite_plugs_seated",),
            paths_blocked_after_phase=("ascending_passage_access", "surface_feed_access", "descending_passage_access"),
            irreversible_actions=("final_plug_isolation",),
            conflict_if=("lower_system_open",),
            notes="Final isolation/decommissioning boundary.",
        ),
        Phase(
            "finish_upper_domain",
            required_access_paths=("upper_work_access",),
            required_open_paths=("upper_work_access",),
            required_components_existing=("upper_chamber_zone_complete", "granite_plugs_seated"),
            components_created=("upper_domain_finished",),
            conflict_if=("lower_system_open",),
            notes="Upper finish assumes lower wet domain is isolated.",
        ),
        Phase(
            "remove_access_decommission",
            required_access_paths=("decommissioning_access",),
            required_components_existing=("upper_domain_finished", "granite_plugs_seated"),
            components_created=("decommissioned",),
            paths_blocked_after_phase=("upper_work_access", "plug_staging_access", "decommissioning_access"),
            irreversible_actions=("access_removed", "construction_system_decommissioned"),
            notes="Remove construction/service access after the system no longer needs it.",
        ),
    )


def bad_sequence(name: str) -> tuple[Phase, ...]:
    phases = list(canonical_phases())
    by_name = {phase.name: phase for phase in phases}
    if name == "plugs_seated_too_early":
        order = [
            "cut_lower_node",
            "cut_descending_passage",
            "establish_surface_feed_possible",
            "cut_or_open_vent_reset_path",
            "build_ascending_passage",
            "stage_granite_plugs",
            "seat_granite_plugs",
            "complete_upper_chamber_zone",
            "final_lower_system_shutdown",
            "finish_upper_domain",
            "remove_access_decommission",
        ]
    elif name == "no_vent_before_pressure":
        order = [
            "cut_lower_node",
            "cut_descending_passage",
            "establish_surface_feed_possible",
            "build_lower_hydraulic_use_window",
            "build_ascending_passage",
            "stage_granite_plugs",
            "use_lower_system_if_needed",
            "cut_or_open_vent_reset_path",
            "complete_upper_chamber_zone",
            "final_lower_system_shutdown",
            "seat_granite_plugs",
            "finish_upper_domain",
            "remove_access_decommission",
        ]
    elif name == "final_shutdown_after_plugs":
        order = [
            "cut_lower_node",
            "cut_descending_passage",
            "establish_surface_feed_possible",
            "build_lower_hydraulic_use_window",
            "cut_or_open_vent_reset_path",
            "build_ascending_passage",
            "stage_granite_plugs",
            "use_lower_system_if_needed",
            "complete_upper_chamber_zone",
            "seat_granite_plugs",
            "final_lower_system_shutdown",
            "finish_upper_domain",
            "remove_access_decommission",
        ]
    elif name == "upper_finished_before_wet_isolation":
        order = [
            "cut_lower_node",
            "cut_descending_passage",
            "establish_surface_feed_possible",
            "build_lower_hydraulic_use_window",
            "cut_or_open_vent_reset_path",
            "build_ascending_passage",
            "stage_granite_plugs",
            "use_lower_system_if_needed",
            "complete_upper_chamber_zone",
            "finish_upper_domain",
            "final_lower_system_shutdown",
            "seat_granite_plugs",
            "remove_access_decommission",
        ]
    elif name == "no_feed_access_window":
        order = [
            "cut_lower_node",
            "cut_descending_passage",
            "cut_or_open_vent_reset_path",
            "build_lower_hydraulic_use_window",
            "build_ascending_passage",
            "stage_granite_plugs",
            "use_lower_system_if_needed",
            "complete_upper_chamber_zone",
            "final_lower_system_shutdown",
            "seat_granite_plugs",
            "finish_upper_domain",
            "remove_access_decommission",
        ]
    else:
        raise ValueError(f"unknown bad sequence: {name}")
    return tuple(by_name[item] for item in order)


def phase_by_name(phases: tuple[Phase, ...], name: str) -> Phase:
    for phase in phases:
        if phase.name == name:
            return phase
    raise KeyError(name)


def evaluate_sequence(sequence_name: str = "canonical", phases: tuple[Phase, ...] | None = None) -> SequenceOutputs:
    phase_tuple = phases if phases is not None else canonical_phases()
    open_paths = set(INITIAL_OPEN_PATHS)
    blocked_paths: set[str] = set()
    components: set[str] = set()
    all_conflicts: list[str] = []
    all_warnings: list[str] = []
    irreversible_warnings: list[str] = []
    phase_results: list[PhaseResult] = []

    for index, phase in enumerate(phase_tuple, start=1):
        conflicts: list[str] = []
        warnings: list[str] = []
        open_before = tuple(sorted(open_paths))

        for path in set(phase.required_access_paths + phase.required_open_paths):
            if path in blocked_paths or path not in open_paths:
                conflicts.append(f"{phase.name}: requires path '{path}' after it was blocked or unavailable")

        for component in phase.required_components_existing:
            if component not in components:
                conflicts.append(f"{phase.name}: requires component '{component}' before it exists")

        for component in phase.conflict_if:
            if component in components:
                conflicts.append(f"{phase.name}: conflicts with prior component/action '{component}'")

        if phase.name == "use_lower_system_if_needed" and "vent_reset_path_established" not in components:
            conflicts.append("use_lower_system_if_needed: lower hydraulic use requires vent/reset path first")

        if phase.name == "seat_granite_plugs" and "upper_chamber_zone_complete" not in components:
            conflicts.append("seat_granite_plugs: plugs seated before upper work requiring ascending access is complete")

        if phase.name == "seat_granite_plugs" and "lower_system_shutdown" not in components:
            conflicts.append("seat_granite_plugs: final closure happens before lower shutdown")

        if phase.name == "finish_upper_domain" and "granite_plugs_seated" not in components:
            conflicts.append("finish_upper_domain: upper finish begins before wet lower domain is isolated")

        if phase.name == "remove_access_decommission" and "upper_domain_finished" not in components:
            conflicts.append("remove_access_decommission: decommissioning before upper domain is finished")

        if phase.name == "build_lower_hydraulic_use_window" and "surface_feed_possible" not in components:
            conflicts.append("build_lower_hydraulic_use_window: no feed access window established")

        if phase.irreversible_actions:
            warnings.append(f"{phase.name}: irreversible actions: {', '.join(phase.irreversible_actions)}")
            irreversible_warnings.extend(warnings[-1:])

        components.update(phase.components_created)
        for path in phase.paths_blocked_after_phase:
            blocked_paths.add(path)
            open_paths.discard(path)

        status = "conflict" if conflicts else "ok"
        all_conflicts.extend(conflicts)
        all_warnings.extend(warnings)
        phase_results.append(
            PhaseResult(
                phase_index=index,
                phase_name=phase.name,
                status=status,
                open_paths_before=open_before,
                blocked_paths_after=tuple(sorted(blocked_paths)),
                existing_components_after=tuple(sorted(components)),
                conflicts=tuple(conflicts),
                warnings=tuple(warnings),
            )
        )

    open_path_windows = compute_open_path_windows(phase_tuple)
    critical_dependencies = (
        "surface feed/access window must exist before lower hydraulic use",
        "vent/reset path must exist before pressure use",
        "ascending/upper work access must remain open until upper chamber zone is complete",
        "granite plugs must be staged before seating but seated only after lower shutdown",
        "upper finish must follow wet-domain isolation",
        "decommissioning/access removal must come after final upper finish",
    )

    if all_conflicts:
        status: SequenceStatus = "fails_sequence"
    elif any("possible" in phase.name or "if_needed" in phase.name for phase in phase_tuple):
        status = "conditional_pass"
    else:
        status = "passes_screen"

    return SequenceOutputs(
        sequence_name=sequence_name,
        status=status,
        phase_results=tuple(phase_results),
        conflicts=tuple(all_conflicts),
        warnings=tuple(all_warnings),
        critical_dependencies=critical_dependencies,
        irreversible_action_warnings=tuple(irreversible_warnings),
        open_path_windows=open_path_windows,
    )


def compute_open_path_windows(phases: tuple[Phase, ...]) -> tuple[OpenPathWindow, ...]:
    path_purposes = {
        "surface_feed_access": "feed/access lower hydraulic use window",
        "vent_reset_path": "pressure relief and reset",
        "ascending_passage_access": "upper chamber and plug staging/seating access",
        "upper_work_access": "upper chamber / Grand Gallery finishing",
        "plug_staging_access": "stage and seat granite plugs",
        "decommissioning_access": "final access removal/decommissioning",
        "descending_passage_access": "lower node construction, feed, shutdown, and isolation",
    }
    windows: list[OpenPathWindow] = []
    for path, purpose in path_purposes.items():
        required_indices = [
            i
            for i, phase in enumerate(phases)
            if path in phase.required_access_paths or path in phase.required_open_paths
        ]
        if not required_indices:
            continue
        blocked_after = None
        for phase in phases:
            if path in phase.paths_blocked_after_phase:
                blocked_after = phase.name
                break
        windows.append(
            OpenPathWindow(
                path=path,
                first_required_phase=phases[min(required_indices)].name,
                last_required_phase=phases[max(required_indices)].name,
                blocked_after_phase=blocked_after,
                purpose=purpose,
            )
        )
    return tuple(windows)


def print_report(outputs: SequenceOutputs) -> None:
    print(f"Giza Sequence Boss Gate: {outputs.sequence_name}")
    print("Boundary: passing sequence does not prove historical use; it only screens access/timing consistency.")
    print(f"\nStatus: {outputs.status}")

    print("\nPhase table")
    print(f"{'#':>2} {'phase':>35} {'status':>10} {'conflicts':>9} {'blocked_after':>24}")
    for result in outputs.phase_results:
        print(
            f"{result.phase_index:2d} "
            f"{result.phase_name:>35} "
            f"{result.status:>10} "
            f"{len(result.conflicts):9d} "
            f"{', '.join(result.blocked_paths_after) or '-':>24}"
        )

    print("\nConflicts detected")
    if outputs.conflicts:
        for conflict in outputs.conflicts:
            print(f"- {conflict}")
    else:
        print("- none")

    print("\nCritical dependencies")
    for dependency in outputs.critical_dependencies:
        print(f"- {dependency}")

    print("\nIrreversible-action warnings")
    if outputs.irreversible_action_warnings:
        for warning in outputs.irreversible_action_warnings:
            print(f"- {warning}")
    else:
        print("- none")

    print("\nMinimum required open-path windows")
    for window in outputs.open_path_windows:
        blocked = window.blocked_after_phase or "not blocked in sequence"
        print(
            f"- {window.path}: {window.first_required_phase} -> {window.last_required_phase}; "
            f"blocked after: {blocked}; purpose: {window.purpose}"
        )


def run_variants() -> None:
    names = (
        "canonical",
        "plugs_seated_too_early",
        "no_vent_before_pressure",
        "final_shutdown_after_plugs",
        "upper_finished_before_wet_isolation",
        "no_feed_access_window",
    )
    print("\nVariant summary")
    print(f"{'sequence':>36} {'status':>18} {'conflicts':>10}")
    for name in names:
        outputs = evaluate_sequence(name, None if name == "canonical" else bad_sequence(name))
        print(f"{name:>36} {outputs.status:>18} {len(outputs.conflicts):10d}")


if __name__ == "__main__":
    print_report(evaluate_sequence())
    run_variants()
