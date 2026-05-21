#!/usr/bin/env python3
"""
Reduced Giza gate ledger.

This file is self-contained. It does not import the old simulation stack. It
records the final reduced engineering result, the surviving claims, the failed
claims, and the validation tests needed before any archaeology claim could be
made.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


GateStatus = Literal[
    "passes_screen",
    "conditional_pass",
    "fails_baseline",
    "empirical_validation_needed",
    "not_claimed",
    "blocked_claim",
]

ClaimClass = Literal[
    "survives",
    "conditional",
    "fails",
    "not_claimed",
    "blocked",
]


FINAL_STATUS = "VALIDATION-READY FULL-BUILD ENGINEERING CLOSURE - NOT ARCHAEOLOGICALLY VALIDATED"


@dataclass(frozen=True)
class Gate:
    name: str
    status: GateStatus
    claim_class: ClaimClass
    result: str
    surviving_claim: str
    blocked_claim: str
    binding_constraint: str
    falsifier: str
    validation_needed: tuple[str, ...]


@dataclass(frozen=True)
class ReducedLedger:
    title: str
    final_status: str
    engineering_closure_ratio: float
    required_failures: tuple[str, ...]
    conditional_gates: tuple[str, ...]
    gates: tuple[Gate, ...]
    surviving_system_statement: str
    blocked_claims: tuple[str, ...]
    critical_validation_tests: tuple[str, ...]


def build_reduced_ledger() -> ReducedLedger:
    gates = (
        Gate(
            name="water_applied_lower_node_gate",
            status="passes_screen",
            claim_class="survives",
            result="Water-applied lower node functions as hydraulic receiving/surge/reset candidate.",
            surviving_claim="The lower node can be screened as a functional water-applied engineering input.",
            blocked_claim="Water source archaeology is proven.",
            binding_constraint="A water-applied lower node must receive, surge, vent/reset, and remain controllable.",
            falsifier="A water-applied lower event cannot enter, cycle, reset, or remain pressure-safe.",
            validation_needed=(
                "source application route if making archaeological claim",
                "real lower chamber geometry",
                "water/air scale test",
            ),
        ),
        Gate(
            name="air_management_gate",
            status="passes_screen",
            claim_class="survives",
            result="Sealed pressure fails, but vent/Well Shaft/reset architecture rescues it.",
            surviving_claim="The lower hydraulic system survives as air/vent/reset/isolation infrastructure.",
            blocked_claim="Air path proves mechanical transfer.",
            binding_constraint="Displaced air must vent or buffer fast enough to avoid unsafe pressure.",
            falsifier="Measured Well Shaft or passage geometry cannot vent required air volume before unsafe pressure.",
            validation_needed=(
                "Well Shaft geometry",
                "vent capacity",
                "pressure decay model",
            ),
        ),
        Gate(
            name="long_range_mechanical_transfer_gate",
            status="fails_baseline",
            claim_class="fails",
            result="Pressure, air displacement, and coherent mechanical transfer die under baseline.",
            surviving_claim="Not load-bearing.",
            blocked_claim="Lower pulse seats/moves upper blocks.",
            binding_constraint="Useful coherent energy must reach a midlevel or upper work interface.",
            falsifier="Measured damping/coupling leaves surviving motion below useful interface thresholds.",
            validation_needed=(
                "only if someone wants to revive transfer claim: damping/coupling experiment",
            ),
        ),
        Gate(
            name="guided_path_gate",
            status="conditional_pass",
            claim_class="conditional",
            result="Grand Gallery / Ascending Passage strongest semi-guided candidate; Well Shaft air/bleed; granite stiff local candidate.",
            surviving_claim="Observed architecture can be classified as candidate guided/air-control/stiff local paths.",
            blocked_claim="Grand Gallery proven waveguide.",
            binding_constraint="Candidate paths must outperform rough limestone and remain active-phase coherent.",
            falsifier="Measured damping/coupling makes guided candidates no better than rough core transfer.",
            validation_needed=(
                "measured damping",
                "active-phase continuity",
                "residue/airflow evidence",
            ),
        ),
        Gate(
            name="plug_isolation_gate",
            status="passes_screen",
            claim_class="survives",
            result="Granite plugs screen as final isolation/decommissioning boundary.",
            surviving_claim="Plugs survive as final isolation boundary, not as proof by themselves.",
            blocked_claim="Plugs alone prove hydraulic construction.",
            binding_constraint="Final closure must isolate lower wet/air domains from upper domains.",
            falsifier="Plug location or geometry cannot meaningfully isolate air, water, or residue domains.",
            validation_needed=(
                "plug leakage",
                "seating geometry",
                "residue contrast above/below plugs",
            ),
        ),
        Gate(
            name="ordinary_mass_movement_gate",
            status="passes_screen",
            claim_class="survives",
            result="Throughput-limited baseline is repaired by modest lane/cycle changes.",
            surviving_claim="Ordinary mechanics move the mass under repaired throughput assumptions.",
            blocked_claim="Water is required to move every block.",
            binding_constraint="Force, worker density, braking, staging, and accepted-block throughput must close.",
            falsifier="Period-compatible movement cannot meet required accepted-block rate inside available lane/crew constraints.",
            validation_needed=(
                "ramp/terrace/lane layout",
                "crew cycle trials",
                "braking/staging tests",
            ),
        ),
        Gate(
            name="placement_seating_gate",
            status="passes_screen",
            claim_class="survives",
            result="Placement/seating screens under stated correction authority.",
            surviving_claim="Blocks count only after stopping, transfer, orientation, seating, checking, correction, and acceptance.",
            blocked_claim="Delivery equals placement.",
            binding_constraint="Moved blocks must become accepted placed blocks before lock-in.",
            falsifier="A block can arrive but cannot be oriented, seated, corrected, and accepted.",
            validation_needed=(
                "final-meter block trial",
                "wedge/lever/packer correction trials",
            ),
        ),
        Gate(
            name="precision_restoration_gate",
            status="passes_screen",
            claim_class="survives",
            result="Precision closes by drift suppression / restoration loops under stated thresholds.",
            surviving_claim="Precision is handled as detect-correct-recheck-lock restoration, not perfect manual placement.",
            blocked_claim="Precision required repeated perfect manual placement.",
            binding_constraint="Reference drift, detection thresholds, and correction authority must stay ahead of lock-in.",
            falsifier="Expected drift exceeds detection/correction authority before the next check interval.",
            validation_needed=(
                "detection threshold tests",
                "reference drift tests",
                "correction interval tests",
            ),
        ),
        Gate(
            name="upper_workcell_integration_gate",
            status="passes_screen",
            claim_class="survives",
            result="Simultaneous upper operations fail, but phased upper operations produce viable repaired layouts.",
            surviving_claim="Upper workcell closure depends on phased sequencing.",
            blocked_claim="Upper workcell closes without phased sequencing.",
            binding_constraint="Upper movement, braking, final placement, correction, references, casing, access removal, and throughput must coexist.",
            falsifier="No phased upper workcell layout can host required tasks while maintaining accepted-block throughput.",
            validation_needed=(
                "phased upper workcell physical layout trial",
                "upper throughput cycle trial",
                "casing/access-removal mockup",
            ),
        ),
        Gate(
            name="residue_prediction_gate",
            status="conditional_pass",
            claim_class="conditional",
            result="Residue model predicts lower wet/mineral zones and plug-isolation contrast; contamination controls required.",
            surviving_claim="Residue chemistry is a testable spatial prediction layer.",
            blocked_claim="Salt/alum/sulfate proves hydraulic use.",
            binding_constraint="Residues must form a controlled spatial pattern, not a generic contamination or decay signature.",
            falsifier="Measured residues are random, modern, substrate-only, or contradict lower-wet / plug-isolation / upper-dry predictions.",
            validation_needed=(
                "mineral species map",
                "contamination controls",
                "spatial sampling by zone/joint/shaft/substrate",
            ),
        ),
        Gate(
            name="historical_attestation_gate",
            status="not_claimed",
            claim_class="not_claimed",
            result="Historical use is not claimed.",
            surviving_claim="Engineering closure can be reported without archaeology claim.",
            blocked_claim="This proves what happened historically.",
            binding_constraint="Historical proof requires independent archaeological or textual evidence.",
            falsifier="A historical claim is made without independent evidence.",
            validation_needed=(
                "independent archaeological evidence",
                "datable operational context",
                "excavation or textual bridge",
            ),
        ),
    )
    blocked_claims = (
        "Hydraulic lifting is proven.",
        "Water moved every block.",
        "Lower pulse mechanically seats upper blocks.",
        "Long-range hydraulic/vibration transfer closes.",
        "Grand Gallery is proven as a hydraulic waveguide.",
        "King Chamber receives useful pressure from the lower node under baseline.",
        "Salt/alum/sulfate residues prove hydraulic use without spatial controls.",
        "Historical use is proven.",
        "Upper workcell closes without phased sequencing.",
    )
    critical_validation_tests = (
        "source/lower-node geometry check",
        "lower water-air scale model",
        "Well Shaft / vent capacity survey",
        "plug leakage/isolation test",
        "phased upper workcell mockup",
        "final-meter placement/seating trial",
        "precision reference/correction trial",
        "residue mineral map with contamination controls",
        "midlevel granite replacement/load model",
    )
    return ReducedLedger(
        title="Giza Reduced Gate Ledger",
        final_status=FINAL_STATUS,
        engineering_closure_ratio=1.000,
        required_failures=(),
        conditional_gates=("guided_path_gate", "residue_prediction_gate"),
        gates=gates,
        surviving_system_statement=(
            "Given water applied to the lower node, repaired ordinary throughput, and phased upper-workcell operations, "
            "the model reaches full-chain engineering closure with no required simulated gate failing. Ordinary mechanics "
            "move and place mass; precision restoration suppresses drift; the lower hydraulic subsystem manages "
            "water/air/reset/isolation; phased upper workcells close final placement, correction, casing finish, and "
            "access-removal coexistence. Historical use is not claimed."
        ),
        blocked_claims=blocked_claims,
        critical_validation_tests=critical_validation_tests,
    )


def print_ledger(ledger: ReducedLedger) -> None:
    print("=" * 112)
    print(ledger.title.upper())
    print("=" * 112)
    print(f"Final status:              {ledger.final_status}")
    print(f"Engineering closure ratio: {ledger.engineering_closure_ratio:.3f}")
    print(f"Required failures:         {', '.join(ledger.required_failures) if ledger.required_failures else 'none'}")
    print(f"Conditional gates:         {', '.join(ledger.conditional_gates) if ledger.conditional_gates else 'none'}")
    print()
    print("Surviving system statement:")
    print(ledger.surviving_system_statement)
    print()
    print("Gate Summary")
    print(f"{'gate':<38} {'status':<24} {'claim':<14} result")
    print("-" * 112)
    for gate_item in ledger.gates:
        print(f"{gate_item.name:<38} {gate_item.status:<24} {gate_item.claim_class:<14} {gate_item.result}")
    print()
    print("Detailed Gates")
    for gate_item in ledger.gates:
        print("-" * 112)
        print(gate_item.name)
        print(f"  status:              {gate_item.status}")
        print(f"  claim class:         {gate_item.claim_class}")
        print(f"  surviving claim:     {gate_item.surviving_claim}")
        print(f"  blocked claim:       {gate_item.blocked_claim}")
        print(f"  binding constraint:  {gate_item.binding_constraint}")
        print(f"  falsifier:           {gate_item.falsifier}")
        print("  validation needed:")
        for item in gate_item.validation_needed:
            print(f"    - {item}")
    print()
    print("Blocked Claims")
    for claim in ledger.blocked_claims:
        print(f"  - {claim}")
    print("Critical Validation Tests")
    for test in ledger.critical_validation_tests:
        print(f"  - {test}")
    print()


def export_markdown(ledger: ReducedLedger) -> str:
    lines = [
        f"# {ledger.title}",
        "",
        "## Final Status",
        "",
        f"`{ledger.final_status}`",
        "",
        f"Engineering closure ratio: `{ledger.engineering_closure_ratio:.3f}`",
        "",
        "Required failures: none",
        "",
        f"Conditional gates: {', '.join(ledger.conditional_gates)}",
        "",
        "## Surviving System Statement",
        "",
        ledger.surviving_system_statement,
        "",
        "## Gate Summary",
        "",
        "| Gate | Status | Claim Class | Result |",
        "| --- | --- | --- | --- |",
    ]
    for gate_item in ledger.gates:
        lines.append(
            f"| {gate_item.name} | {gate_item.status} | {gate_item.claim_class} | {gate_item.result} |"
        )
    lines.extend(["", "## Detailed Gates", ""])
    for gate_item in ledger.gates:
        lines.extend(
            [
                f"### {gate_item.name}",
                "",
                f"- Status: {gate_item.status}",
                f"- Claim class: {gate_item.claim_class}",
                f"- Result: {gate_item.result}",
                f"- Surviving claim: {gate_item.surviving_claim}",
                f"- Blocked claim: {gate_item.blocked_claim}",
                f"- Binding constraint: {gate_item.binding_constraint}",
                f"- Falsifier: {gate_item.falsifier}",
                "- Validation needed:",
            ]
        )
        lines.extend(f"  - {item}" for item in gate_item.validation_needed)
        lines.append("")
    lines.extend(["## Blocked Claims", ""])
    lines.extend(f"- {claim}" for claim in ledger.blocked_claims)
    lines.extend(["", "## Critical Validation Tests", ""])
    lines.extend(f"- {test}" for test in ledger.critical_validation_tests)
    lines.append("")
    return "\n".join(lines)


def export_json(ledger: ReducedLedger) -> str:
    return json.dumps(asdict(ledger), indent=2)


def main() -> None:
    ledger = build_reduced_ledger()
    print_ledger(ledger)
    output_dir = Path(__file__).resolve().parent
    markdown_path = output_dir / "REDUCED_GATE_LEDGER_EXPORT.md"
    json_path = output_dir / "reduced_gate_ledger_export.json"
    markdown_path.write_text(export_markdown(ledger), encoding="utf-8")
    json_path.write_text(export_json(ledger), encoding="utf-8")
    print(f"Wrote {markdown_path.name}")
    print(f"Wrote {json_path.name}")


if __name__ == "__main__":
    main()
