"""
giza_sequence_sim.py
====================
Course-by-course construction sequence simulation for a Giza-equivalent pyramid.

Adds a temporal axis to the giza_engineering_sim gate framework:
  - 210 courses from foundation to apex
  - Per-course geometry, throughput, precision, hydraulic phase, workcell state
  - Phase detection and milestone flagging
  - CSV and Markdown export to ./sequence_output/

STATUS  : VALIDATION-READY ENGINEERING RECONSTRUCTION -- NOT ARCHAEOLOGICALLY VALIDATED
HYDRAULIC: Conditional lower-node air-management / vent / reset / isolation only.
TRANSFER : Long-range lower-to-upper transfer FAILS BASELINE — not load-bearing.
HISTORY  : Historical use NOT CLAIMED.

Run:
    python giza_sequence_sim.py
"""

from __future__ import annotations

import csv
import dataclasses
import math
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Display labels keep the model portable and prevent output from overclaiming
# site-specific interpretations.
STRUCTURE_LABEL = "large precision stone body"
INTERNAL_STAGING_LABEL = "upper internal staging gallery"
LOWER_SUBSYSTEM_LABEL = "lower pressure/air-reset subsystem"

# ---------------------------------------------------------------------------
# Package imports — graceful fallback if run outside the package directory
# ---------------------------------------------------------------------------
try:
    from giza_engineering_sim.constants import PA_PER_PSI, FINAL_STATUS, CLAIM_BOUNDARY
    from giza_engineering_sim.mechanics import total_pull_required
    _PACKAGE_AVAILABLE = True
except ImportError:
    _PACKAGE_AVAILABLE = False
    PA_PER_PSI = 6894.757293168
    FINAL_STATUS = "VALIDATION-READY ENGINEERING RECONSTRUCTION -- NOT ARCHAEOLOGICALLY VALIDATED"
    CLAIM_BOUNDARY = (
        "Engineering feasibility under stated assumptions is not historical proof. "
        "The model does not prove hydraulic pyramid construction or claim water moved every block."
    )
    def total_pull_required(mu, mass, g, angle_deg):  # type: ignore[misc]
        r = math.radians(angle_deg)
        return mass * g * (mu * math.cos(r) + math.sin(r))


# ===========================================================================
# CONSTANTS
# ===========================================================================

BASE_SIDE_M: float      = 230.33   # Great Pyramid base side (m)
HEIGHT_M: float         = 146.7    # Apex height above base (m)
TOTAL_COURSES: int      = 210      # Masonry courses, foundation → apex
TOTAL_BLOCKS: int       = 2_300_000

BUILD_YEARS: float          = 20.0
WORKDAYS_PER_YEAR: float    = 300.0
HOURS_PER_DAY: float        = 10.0
TOTAL_WORKDAYS: float       = BUILD_YEARS * WORKDAYS_PER_YEAR        # 6 000 days
REQUIRED_BLOCKS_PER_DAY: float = TOTAL_BLOCKS / TOTAL_WORKDAYS       # ≈ 383.3

GRAVITY: float          = 9.81
WATER_DENSITY: float    = 1_000.0
AIR_DENSITY: float      = 1.2
LOWER_DEPTH_M: float    = 33.0     # Lower chamber / subterranean depth
HYDRAULIC_PRESSURE_PSI: float = (WATER_DENSITY * GRAVITY * LOWER_DEPTH_M) / PA_PER_PSI  # ≈ 46.9 psi
HYDRAULIC_PRESSURE_PA: float = WATER_DENSITY * GRAVITY * LOWER_DEPTH_M

# Reset-time gate: subsystem-control screen for lower-node vent/reset cycling.
RESET_EVENT_VOLUME_M3: float      = 10.0
RESET_VENT_AREA_M2: float         = 0.02
RESET_WATER_OUTLET_AREA_M2: float = 0.02
RESET_DISCHARGE_COEFF: float      = 0.62
ATMOSPHERIC_PRESSURE_PA: float    = 101_325.0
ALLOWED_RESET_CYCLE_S: float      = 300.0

# Hydraulic lifecycle course boundaries (0-indexed course number)
HYD_ACTIVE_START:        int = 6    # Lower node engaged (chamber complete)
HYD_DECOMMISSION_START:  int = 185  # Isolation / plug-staging begins
HYD_SEALED_COURSE:       int = 200  # Granite plug closure complete

# Lower-node friction support is credited ONLY in the lower zone.
# Blocked claim: "lower pulse seats upper blocks."
FRICTION_HEIGHT_LIMIT_M: float = 70.0   # Bottom third of pyramid (≈ courses 1-100)

# Throughput parameters (base values — height-scaled)
BASE_CYCLE_MIN:     float = 30.0    # Ramp haul cycle at ground level (minutes)
CYCLE_HEIGHT_COEFF: float = 0.102   # Additional minutes per metre of pyramid height
BASE_LANES:         int   = 32      # Maximum active haul lanes (full base)
MIN_LANES:          int   = 4       # Floor — apex / near-apex operations
LANE_FULL_SIDE_M:   float = 200.0   # Side length at which full lanes are available
LANE_FLOOR_SIDE_M:  float = 10.0    # Side length at which minimum lanes apply
DOWNTIME_FRAC:      float = 0.20    # Fraction of operational time lost to stoppages
ACCEPT_EFF:         float = 0.75    # Fraction of delivered blocks accepted / seated

# Precision drift parameters
DRIFT_BASE_MM:      float = 0.50    # Base drift contribution per course (mm)
DRIFT_HEIGHT_SCALE: float = 1.00    # Additional drift fraction at apex (doubles rate)
DETECT_THRESH_MM:   float = 1.50    # Minimum detectable mis-level (mm)
CORRECT_CAP_MM:     float = 10.0    # Maximum single-event correction (mm)
CHECK_INTERVAL:     int   = 1       # Correction-check cadence (every N courses)
TOLERANCE_MM:       float = 15.0    # Total allowable residual drift over full build

# Workcell thresholds
PHASED_SIDE_THRESH_M:   float = 80.0   # Platform side below which phased ops required
WORKCELL_REQUIRED_M2:   float = 180.0  # Minimum required workspace area (from scenario)

# Final-course closure first-pass area diagnostic. Area is necessary but not
# sufficient; final closure also requires braking/control, reference visibility,
# and access/removal sequencing.
FINAL_BLOCK_FOOTPRINT_M2:     float = 4.0
FINAL_CREW_FOOTPRINT_M2:      float = 20.0
FINAL_LEVER_CLEARANCE_M2:     float = 20.0
FINAL_REFERENCE_ACCESS_M2:    float = 15.0
FINAL_OPERATION_REQUIRED_M2:  float = (
    FINAL_BLOCK_FOOTPRINT_M2
    + FINAL_CREW_FOOTPRINT_M2
    + FINAL_LEVER_CLEARANCE_M2
    + FINAL_REFERENCE_ACCESS_M2
)

# Upper internal staging gallery
# Void confirmed: ScanPyramids 2017 muon tomography.
# Geometry: Egyptian royal-cubit prediction (falsifiable on physical survey).
ROYAL_CUBIT_M:          float = 0.5236
URWG_LENGTH_CUBITS:     float = 57.0   # → 29.845 m  (~30 m muon signature)
URWG_WIDTH_CUBITS:      float = 4.0    # → 2.094 m   (= Grand Gallery base width)
URWG_HEIGHT_CUBITS:     float = 3.5    # → 1.833 m   (lever-work headroom)
URWG_LENGTH_M:          float = URWG_LENGTH_CUBITS * ROYAL_CUBIT_M     # 29.845 m
URWG_WIDTH_M:           float = URWG_WIDTH_CUBITS  * ROYAL_CUBIT_M     # 2.094 m
URWG_HEIGHT_M:          float = URWG_HEIGHT_CUBITS * ROYAL_CUBIT_M     # 1.833 m
# 50% effective-use credit applied to gross staging area (matching gate model)
URWG_STAGING_CREDIT_M2: float = URWG_LENGTH_M * URWG_WIDTH_M * 0.50   # ~31.3 m²

# Mechanics
AVG_BLOCK_MASS_KG:      float = 2_500.0
MU:                     float = 0.10
BASE_RAMP_DEG:          float = 10.0   # Effective ramp angle at ground
APEX_RAMP_DEG_ADD:      float = 5.0    # Additional effective angle at full height
WORKER_PULL_N:          float = 300.0
MECH_ADVANTAGE:         float = 8.0
EFFICIENCY:             float = 0.60

# Block count normalization: blocks at course n ∝ (N - n)²
# Sum_{n=0}^{N-1} (N-n)² = N(N+1)(2N+1)/6
_N:           int   = TOTAL_COURSES
_BLOCK_DENOM: float = _N * (_N + 1) * (2 * _N + 1) / 6


# ===========================================================================
# ENUMERATIONS
# ===========================================================================

class HydraulicPhase(str, Enum):
    PRE_BUILD    = "pre_build"      # Chamber under construction / not yet engaged
    ACTIVE       = "active"         # Air-management / vent / reset / isolation live
    DECOMMISSION = "decommission"   # Isolation sequence and plug staging
    SEALED       = "sealed"         # Granite plugs in final closed position


class ThroughputStatus(str, Enum):
    GREEN    = "green"      # ratio >= 1.20  — schedule margin comfortable
    ADEQUATE = "adequate"   # ratio >= 1.00  — on schedule, thin margin
    WARNING  = "warning"    # ratio >= 0.85  — below schedule, repair needed
    CRITICAL = "critical"   # ratio <  0.85  — severe deficit, lane/cycle overhaul required


class PrecisionStatus(str, Enum):
    NOMINAL    = "nominal"     # Drift within detection threshold — no action
    CORRECTING = "correcting"  # Correction event fired this course
    WARNING    = "warning"     # Approaching tolerance limit after correction
    LOCKED_IN  = "locked_in"   # Uncorrectable residual embedded in structure


class BuildPhase(str, Enum):
    FOUNDATION             = "FOUNDATION"              # Courses   1–10
    LOWER_HYDRAULIC_ACTIVE = "LOWER_HYDRAULIC_ACTIVE"  # Courses  11–50
    MID_RISE               = "MID_RISE"                # Courses  51–130
    UPPER_TRANSITION       = "UPPER_TRANSITION"        # Courses 131–165
    UPPER_CONVERGENCE      = "UPPER_CONVERGENCE"       # Courses 166–195
    APEX_AND_DECOMMISSION  = "APEX_AND_DECOMMISSION"   # Courses 196–210


# ===========================================================================
# GEOMETRY
# ===========================================================================

def platform_side_at_course(n: int) -> float:
    """Working platform side length at course n (0-indexed). Metres."""
    return BASE_SIDE_M * max(0.0, 1.0 - n / TOTAL_COURSES)


def pyramid_height_at_course(n: int) -> float:
    """Pyramid height when course n is being placed. Metres."""
    return HEIGHT_M * n / TOTAL_COURSES


def platform_area_at_course(n: int) -> float:
    """Working platform area at course n. Square metres."""
    s = platform_side_at_course(n)
    return s * s


def blocks_at_course(n: int) -> int:
    """
    Estimated block count for course n, normalized so the full build totals
    TOTAL_BLOCKS. Distribution: proportional to (N - n)², reflecting the
    shrinking plan area as the pyramid tapers.
    """
    remaining = TOTAL_COURSES - n
    return round(TOTAL_BLOCKS * (remaining ** 2) / _BLOCK_DENOM)


def build_phase_at_course(n: int) -> BuildPhase:
    """Classify course n (0-indexed) into a named construction phase."""
    if n <= 9:
        return BuildPhase.FOUNDATION
    if n <= 50:
        return BuildPhase.LOWER_HYDRAULIC_ACTIVE
    if n <= 130:
        return BuildPhase.MID_RISE
    if n <= 165:
        return BuildPhase.UPPER_TRANSITION
    if n <= 195:
        return BuildPhase.UPPER_CONVERGENCE
    return BuildPhase.APEX_AND_DECOMMISSION


# ===========================================================================
# HYDRAULIC LIFECYCLE
# ===========================================================================

def hydraulic_phase_at_course(n: int) -> HydraulicPhase:
    """Lower-node hydraulic lifecycle phase at course n (0-indexed)."""
    if n < HYD_ACTIVE_START:
        return HydraulicPhase.PRE_BUILD
    if n < HYD_DECOMMISSION_START:
        return HydraulicPhase.ACTIVE
    if n < HYD_SEALED_COURSE:
        return HydraulicPhase.DECOMMISSION
    return HydraulicPhase.SEALED


def orifice_flow_m3_s(cd: float, area_m2: float, delta_p_pa: float, rho: float) -> float:
    """Lumped orifice flow screen. This is not CFD."""
    if cd <= 0 or area_m2 < 0 or delta_p_pa < 0 or rho <= 0:
        raise ValueError("invalid orifice-flow inputs")
    if area_m2 == 0 or delta_p_pa == 0:
        return 0.0
    return cd * area_m2 * math.sqrt(2.0 * delta_p_pa / rho)


def reset_time_s(event_volume_m3: float, flow_m3_s: float) -> float:
    """Time to pass one event volume through the limiting outlet."""
    if event_volume_m3 <= 0 or flow_m3_s < 0:
        raise ValueError("invalid reset-time inputs")
    if flow_m3_s == 0:
        return math.inf
    return event_volume_m3 / flow_m3_s


def reset_time_gate_metrics() -> tuple[float, float, float, float, str]:
    """
    Return air_time_s, water_time_s, required_time_s, ratio, status.

    Available budget : ALLOWED_RESET_CYCLE_S
    Required budget  : max(air_limited_reset_time_s, water_limited_reset_time_s)
    Ratio            : allowed / required
    """
    air_flow = orifice_flow_m3_s(
        RESET_DISCHARGE_COEFF,
        RESET_VENT_AREA_M2,
        HYDRAULIC_PRESSURE_PA,
        AIR_DENSITY,
    )
    water_flow = orifice_flow_m3_s(
        RESET_DISCHARGE_COEFF,
        RESET_WATER_OUTLET_AREA_M2,
        HYDRAULIC_PRESSURE_PA,
        WATER_DENSITY,
    )
    air_time = reset_time_s(RESET_EVENT_VOLUME_M3, air_flow)
    water_time = reset_time_s(RESET_EVENT_VOLUME_M3, water_flow)
    required_time = max(air_time, water_time)
    ratio = 0.0 if math.isinf(required_time) else ALLOWED_RESET_CYCLE_S / required_time
    status = "conditional_pass" if ratio >= 1.0 else "fails_baseline"
    return air_time, water_time, required_time, ratio, status


def friction_support_active_at_course(n: int) -> bool:
    """
    Returns True if lower-node hydraulic friction support is credited at course n.

    Surviving claim  : Lower node may function as air-management / vent / reset /
                       isolation infrastructure.
    BLOCKED claim    : Lower pulse seats upper blocks.
    Credit boundary  : Only below FRICTION_HEIGHT_LIMIT_M where lower-chamber
                       geometry can plausibly reduce contact friction on the
                       ascending passage bed-face blocks.
    """
    return (
        hydraulic_phase_at_course(n) == HydraulicPhase.ACTIVE
        and pyramid_height_at_course(n) <= FRICTION_HEIGHT_LIMIT_M
    )


# ===========================================================================
# THROUGHPUT MODEL
# ===========================================================================

def active_lanes_at_course(n: int) -> int:
    """
    Active haul-lane count at course n.
    Linearly tapers as the platform side shrinks, clamped to [MIN_LANES, BASE_LANES].
    """
    side = platform_side_at_course(n)
    if side >= LANE_FULL_SIDE_M:
        return BASE_LANES
    if side <= LANE_FLOOR_SIDE_M:
        return MIN_LANES
    frac = (side - LANE_FLOOR_SIDE_M) / (LANE_FULL_SIDE_M - LANE_FLOOR_SIDE_M)
    return max(MIN_LANES, round(MIN_LANES + (BASE_LANES - MIN_LANES) * frac))


def cycle_time_at_course(n: int) -> float:
    """
    Ramp cycle time (minutes) at course n.
    Increases linearly with pyramid height — longer haul travel to the working level.
    """
    return BASE_CYCLE_MIN + CYCLE_HEIGHT_COEFF * pyramid_height_at_course(n)


def effective_capacity_at_course(n: int) -> float:
    """
    Accepted blocks per workday at course n, after downtime and acceptance losses.
    effective = lanes × (daily_mins / cycle_min) × (1 − downtime) × acceptance
    """
    lanes = active_lanes_at_course(n)
    ct    = cycle_time_at_course(n)
    raw   = lanes * (HOURS_PER_DAY * 60.0 / ct) * (1.0 - DOWNTIME_FRAC)
    return raw * ACCEPT_EFF


def throughput_ratio_at_course(n: int) -> float:
    """
    Effective capacity / global average required rate.

    This is retained as a pressure diagnostic only. It is not the load-bearing
    schedule-closure gate because course block counts vary dramatically.
    """
    return effective_capacity_at_course(n) / REQUIRED_BLOCKS_PER_DAY


def throughput_status_at_course(n: int) -> ThroughputStatus:
    r = throughput_ratio_at_course(n)
    if r >= 1.20:
        return ThroughputStatus.GREEN
    if r >= 1.00:
        return ThroughputStatus.ADEQUATE
    if r >= 0.85:
        return ThroughputStatus.WARNING
    return ThroughputStatus.CRITICAL


def days_required_at_course(n: int) -> float:
    """Workdays required for course n under its own block count and capacity."""
    capacity = effective_capacity_at_course(n)
    if capacity <= 0:
        return math.inf
    return blocks_at_course(n) / capacity


def compute_total_schedule_days(snapshots: list["CourseSnapshot"] | None = None) -> float:
    """Total course-days required by the full sequence."""
    if snapshots is not None:
        return sum(s.days_required_for_course for s in snapshots)
    return sum(days_required_at_course(n) for n in range(TOTAL_COURSES))


def schedule_ratio(total_days: float) -> float:
    """Allowed workdays divided by computed schedule days."""
    if total_days <= 0:
        raise ValueError("total_days must be positive")
    return TOTAL_WORKDAYS / total_days


def schedule_status(ratio: float) -> str:
    if ratio >= 1.20:
        return "green"
    if ratio >= 1.00:
        return "adequate"
    if ratio >= 0.85:
        return "warning"
    return "critical"


# ===========================================================================
# PRECISION DRIFT MODEL
# ===========================================================================

@dataclass
class DriftState:
    """Mutable carry-forward precision state across all 210 courses."""
    cumulative_mm:               float = 0.0
    total_corrected_mm:          float = 0.0
    correction_events:           int   = 0
    locked_in_mm:                float = 0.0   # Residual that could not be corrected
    worst_single_correction_mm:  float = 0.0


def drift_contribution_at_course(n: int) -> float:
    """
    Expected drift added by course n.
    Base rate amplified by height — increased wind load, reduced reference-point
    visibility, thermal gradient growth, and longer sight-line error chains.
    """
    h     = pyramid_height_at_course(n)
    scale = 1.0 + DRIFT_HEIGHT_SCALE * (h / HEIGHT_M)
    return DRIFT_BASE_MM * scale


def apply_correction(state: DriftState) -> PrecisionStatus:
    """
    Perform a detect-and-correct cycle against the current drift state.
    Mutates state in place.  Returns the post-correction precision status.

    Each precision check compares the current working reference against a
    persistent external datum. The measured quantity is cumulative deviation,
    not local stone-to-stone error alone.
    """
    status = PrecisionStatus.NOMINAL

    if abs(state.cumulative_mm) >= DETECT_THRESH_MM:
        # Correction warranted — apply up to correction capacity
        error      = state.cumulative_mm
        correctable = min(abs(error), CORRECT_CAP_MM)
        corrected   = math.copysign(correctable, error)
        residual    = error - corrected

        # Any residual beyond half the detection threshold is considered locked in
        locked_increment = max(0.0, abs(residual) - DETECT_THRESH_MM * 0.5)

        state.cumulative_mm             = residual
        state.total_corrected_mm       += abs(corrected)
        state.correction_events        += 1
        state.locked_in_mm             += locked_increment
        state.worst_single_correction_mm = max(
            state.worst_single_correction_mm, abs(corrected)
        )
        status = PrecisionStatus.CORRECTING

    # Escalate status based on post-correction drift
    if abs(state.cumulative_mm) > TOLERANCE_MM * 0.70:
        status = PrecisionStatus.WARNING
    if state.locked_in_mm > TOLERANCE_MM * 0.50:
        status = PrecisionStatus.LOCKED_IN

    return status


# ===========================================================================
# WORKCELL MODEL
# ===========================================================================

def phased_ops_required_at_course(n: int) -> bool:
    """Phase-sequential operations required once platform side < threshold."""
    return platform_side_at_course(n) < PHASED_SIDE_THRESH_M


def urwg_active_at_course(n: int) -> bool:
    """
    URWG staging credit is applied once phased operations are required.
    The gallery provides interior staging that offloads the shrinking exterior platform.

    Void confirmed: ScanPyramids 2017.  Geometry: cubit prediction — 57 × 4 × 3.5 cubits.
    Blocked claim: URWG proves the Big Void's purpose.
    """
    return phased_ops_required_at_course(n)


def workcell_ratio_at_course(n: int) -> float:
    """
    Available workspace / Required workspace, with optional URWG staging credit.
    URWG credit (+31.3 m²) applied once phased ops are required (platform < 80 m side).
    Capped at 3.0 where space is unconstrained.  < 1.0 → workcell CRITICAL.
    """
    area        = platform_area_at_course(n)
    urwg_credit = URWG_STAGING_CREDIT_M2 if urwg_active_at_course(n) else 0.0
    return min((area + urwg_credit) / WORKCELL_REQUIRED_M2, 3.0) if area > 0 else 0.0


def workcell_status_at_course(n: int) -> str:
    ratio  = workcell_ratio_at_course(n)
    phased = phased_ops_required_at_course(n)
    if ratio >= 2.0:
        return "unrestricted"
    if ratio >= 1.2:
        return "adequate_phased" if phased else "adequate"
    if ratio >= 1.0:
        return "constrained_phased" if phased else "constrained"
    return "critical"


def final_course_closure_ratio_at_course(n: int) -> float:
    """First-pass area ratio for final-meter closure work at course n."""
    available = platform_area_at_course(n)
    if urwg_active_at_course(n):
        available += URWG_STAGING_CREDIT_M2
    return available / FINAL_OPERATION_REQUIRED_M2


def final_course_status_at_course(n: int) -> str:
    ratio = final_course_closure_ratio_at_course(n)
    if ratio >= 3.0:
        return "unrestricted"
    if ratio >= 1.5:
        return "adequate"
    if ratio >= 1.0:
        return "constrained"
    return "critical"


# ===========================================================================
# WORKER DEMAND
# ===========================================================================

def workers_per_block_at_course(n: int) -> int:
    """
    Workers required to move one average block to course n.
    Uses contact mechanics; effective ramp angle increases with height
    (longer, steeper approach ramp geometry at higher courses).
    """
    h               = pyramid_height_at_course(n)
    effective_angle = BASE_RAMP_DEG + (h / HEIGHT_M) * APEX_RAMP_DEG_ADD
    effective_angle = min(effective_angle, 20.0)
    force           = total_pull_required(MU, AVG_BLOCK_MASS_KG, GRAVITY, effective_angle)
    return math.ceil(force / (WORKER_PULL_N * MECH_ADVANTAGE * EFFICIENCY))


# ===========================================================================
# COURSE SNAPSHOT
# ===========================================================================

@dataclass
class CourseSnapshot:
    """Complete engineering state snapshot for one masonry course."""
    # Identity
    course:               int    # 0-indexed
    course_label:         int    # 1-indexed display value
    build_phase:          str

    # Geometry
    height_m:             float
    platform_side_m:      float
    platform_area_m2:     float
    blocks_at_course:     int
    blocks_cumulative:    int
    fraction_complete:    float  # 0.0 – 1.0

    # Throughput
    active_lanes:              int
    cycle_time_min:            float
    effective_capacity_per_day: float
    throughput_ratio:          float
    throughput_status:         str
    days_required_for_course:  float
    cumulative_days_required:  float
    schedule_margin_days:      float
    schedule_ratio_to_date:    float

    # Precision drift
    drift_this_course_mm: float
    cumulative_drift_mm:  float
    correction_applied:   bool
    locked_in_drift_mm:   float
    precision_status:     str

    # Hydraulic
    hydraulic_phase:         str
    hydraulic_pressure_psi:  float
    reset_air_limited_time_s:   float
    reset_water_limited_time_s: float
    reset_required_time_s:      float
    reset_time_ratio:           float
    reset_time_gate_status:     str
    friction_support_active: bool

    # Workcell
    phased_ops_required: bool
    urwg_active:         bool   # URWG staging credit applied (confirmed void, cubit geometry)
    workcell_ratio:      float
    workcell_status:     str
    final_course_closure_ratio:  float
    final_course_status:         str

    # Workers
    workers_per_block:         int
    workers_on_duty_per_day:   int   # Daily force commitment at required rate

    # Accumulated flags
    milestone: str = ""


# ===========================================================================
# MILESTONE TRACKER
# ===========================================================================

class MilestoneTracker:
    """Fires one-shot milestone labels as construction progresses."""

    def __init__(self) -> None:
        self._fired: set[str] = set()
        self._prev_friction: bool = False

    def check(self, snap: CourseSnapshot) -> list[str]:
        milestones: list[str] = []
        n = snap.course

        def once(key: str, condition: bool, label: str) -> None:
            if condition and key not in self._fired:
                self._fired.add(key)
                milestones.append(label)

        # --- Hydraulic lifecycle ---
        once("hyd_active",
             snap.hydraulic_phase == HydraulicPhase.ACTIVE.value,
             f"HYDRAULIC ACTIVE — lower node engaged  "
             f"({snap.hydraulic_pressure_psi:.1f} psi / {LOWER_DEPTH_M} m head)")

        once("reset_time_gate",
             snap.hydraulic_phase == HydraulicPhase.ACTIVE.value,
             f"RESET_TIME_GATE — {snap.reset_time_gate_status}  |  "
             f"required {snap.reset_required_time_s:.1f}s / allowed {ALLOWED_RESET_CYCLE_S:.0f}s  "
             f"(ratio {snap.reset_time_ratio:.2f})")

        once("friction_ends",
             not snap.friction_support_active and n >= HYD_ACTIVE_START,
             f"FRICTION SUPPORT ENDS — height {snap.height_m:.1f} m exceeds lower-zone limit "
             f"({FRICTION_HEIGHT_LIMIT_M:.0f} m)  |  BLOCKED: lower pulse does not seat upper blocks")

        once("hyd_decommission",
             snap.hydraulic_phase == HydraulicPhase.DECOMMISSION.value,
             "HYDRAULIC DECOMMISSION — isolation sequence begins, plug staging")

        once("hyd_sealed",
             snap.hydraulic_phase == HydraulicPhase.SEALED.value,
             "HYDRAULIC SEALED — granite plug closure complete, subsystem decommissioned")

        # --- Throughput pressure ---
        once("throughput_below_1",
             snap.throughput_ratio < 1.00,
             f"THROUGHPUT PRESSURE DIAGNOSTIC BELOW GLOBAL AVERAGE — ratio {snap.throughput_ratio:.3f} "
             f"(lanes={snap.active_lanes}, cycle={snap.cycle_time_min:.1f} min)")

        once("throughput_critical",
             snap.throughput_status == ThroughputStatus.CRITICAL.value,
             f"THROUGHPUT PRESSURE DIAGNOSTIC CRITICAL — ratio {snap.throughput_ratio:.3f} < 0.85 "
             f"| not the schedule-closure gate")

        # --- Workcell ---
        once("phased_ops",
             snap.phased_ops_required,
             f"PHASED OPS REQUIRED — platform {snap.platform_side_m:.1f} m "
             f"(< {PHASED_SIDE_THRESH_M:.0f} m threshold), sequential staging active")

        once("urwg_active",
             snap.urwg_active,
             f"UPPER INTERNAL STAGING CREDIT — {URWG_STAGING_CREDIT_M2:.1f} m² applied  "
             f"| {URWG_LENGTH_CUBITS:.0f} × {URWG_WIDTH_CUBITS:.0f} × {URWG_HEIGHT_CUBITS:.1f} cubits "
             f"({URWG_LENGTH_M:.2f} m × {URWG_WIDTH_M:.3f} m × {URWG_HEIGHT_M:.3f} m)  "
             f"| conditional upper internal volume interpretation  |  BLOCKED: does not establish its purpose")

        once("final_course_critical",
             snap.final_course_status == "critical",
             "FINAL-COURSE CLOSURE CRITICAL — area screen below threshold; optional internal staging "
             "reduces congestion but does not make final courses easy")

        once("workcell_constrained",
             snap.workcell_ratio < 1.2 and snap.phased_ops_required,
             f"WORKCELL CONSTRAINED — area {snap.platform_area_m2:.0f} m², "
             f"ratio {snap.workcell_ratio:.2f}")

        once("workcell_critical",
             snap.workcell_ratio < 1.0,
             f"WORKCELL CRITICAL — platform {snap.platform_area_m2:.0f} m² "
             f"below minimum required {WORKCELL_REQUIRED_M2:.0f} m²")

        # --- Progress ---
        once("quarter_mass",
             snap.fraction_complete >= 0.25,
             f"25% MASS PLACED — {snap.blocks_cumulative:,} blocks")

        once("half_mass",
             snap.fraction_complete >= 0.50,
             f"50% MASS PLACED — {snap.blocks_cumulative:,} blocks")

        once("three_quarter_mass",
             snap.fraction_complete >= 0.75,
             f"75% MASS PLACED — {snap.blocks_cumulative:,} blocks")

        once("quarter_height",
             snap.height_m >= HEIGHT_M * 0.25,
             f"25% HEIGHT — {snap.height_m:.1f} m above base")

        once("half_height",
             snap.height_m >= HEIGHT_M * 0.50,
             f"50% HEIGHT — {snap.height_m:.1f} m above base")

        once("three_quarter_height",
             snap.height_m >= HEIGHT_M * 0.75,
             f"75% HEIGHT — {snap.height_m:.1f} m above base")

        # --- Precision ---
        once("first_correction",
             snap.correction_applied,
             f"FIRST PRECISION CORRECTION — residual after correction: {snap.cumulative_drift_mm:.3f} mm  "
             f"(detect threshold {DETECT_THRESH_MM:.1f} mm)")

        once("precision_warning",
             snap.precision_status == PrecisionStatus.WARNING.value,
             f"PRECISION WARNING — drift approaching tolerance limit ({TOLERANCE_MM:.0f} mm)")

        self._prev_friction = snap.friction_support_active
        return milestones


# ===========================================================================
# MAIN SIMULATION LOOP
# ===========================================================================

def run_sequence_simulation() -> list[CourseSnapshot]:
    """
    Execute the full 210-course construction sequence simulation.
    Returns a CourseSnapshot for every course (0-indexed).
    """
    snapshots:   list[CourseSnapshot] = []
    drift_state: DriftState           = DriftState()
    tracker:     MilestoneTracker     = MilestoneTracker()
    cum_blocks:  int                  = 0
    cumulative_days: float            = 0.0

    for n in range(TOTAL_COURSES):
        # ── Geometry ────────────────────────────────────────────────────────
        h      = pyramid_height_at_course(n)
        side   = platform_side_at_course(n)
        area   = platform_area_at_course(n)
        b      = blocks_at_course(n)
        cum_blocks += b
        frac   = cum_blocks / TOTAL_BLOCKS

        phase = build_phase_at_course(n)

        # ── Throughput ───────────────────────────────────────────────────────
        lanes  = active_lanes_at_course(n)
        ct     = cycle_time_at_course(n)
        cap    = effective_capacity_at_course(n)
        t_rat  = throughput_ratio_at_course(n)
        t_stat = throughput_status_at_course(n)
        course_days = days_required_at_course(n)
        cumulative_days += course_days
        expected_allowed_days_to_date = TOTAL_WORKDAYS * (cum_blocks / TOTAL_BLOCKS)
        schedule_margin = TOTAL_WORKDAYS - cumulative_days
        schedule_ratio_to_date = (
            expected_allowed_days_to_date / cumulative_days
            if cumulative_days > 0 else math.inf
        )

        # ── Precision drift ──────────────────────────────────────────────────
        drift_contrib             = drift_contribution_at_course(n)
        drift_state.cumulative_mm += drift_contrib
        correction_applied        = False

        if n % CHECK_INTERVAL == 0:
            events_before      = drift_state.correction_events
            p_stat             = apply_correction(drift_state)
            correction_applied = drift_state.correction_events > events_before
        else:
            # Dead code at default CHECK_INTERVAL=1; retained for flexibility
            p_stat = PrecisionStatus.NOMINAL
            if abs(drift_state.cumulative_mm) > TOLERANCE_MM * 0.70:
                p_stat = PrecisionStatus.WARNING
            if drift_state.locked_in_mm > TOLERANCE_MM * 0.50:
                p_stat = PrecisionStatus.LOCKED_IN

        # ── Hydraulic ────────────────────────────────────────────────────────
        hyd_phase  = hydraulic_phase_at_course(n)
        friction   = friction_support_active_at_course(n)
        reset_air_time, reset_water_time, reset_required_time, reset_ratio, reset_status = reset_time_gate_metrics()

        # ── Workcell + URWG ──────────────────────────────────────────────────
        phased     = phased_ops_required_at_course(n)
        urwg_on    = urwg_active_at_course(n)
        wc_ratio   = workcell_ratio_at_course(n)
        wc_status  = workcell_status_at_course(n)
        final_ratio = final_course_closure_ratio_at_course(n)
        final_status = final_course_status_at_course(n)

        # ── Workers ──────────────────────────────────────────────────────────
        wpb            = workers_per_block_at_course(n)
        workers_daily  = round(REQUIRED_BLOCKS_PER_DAY * wpb)

        # ── Assemble snapshot ────────────────────────────────────────────────
        snap = CourseSnapshot(
            course                   = n,
            course_label             = n + 1,
            build_phase              = phase.value,
            height_m                 = round(h, 2),
            platform_side_m          = round(side, 2),
            platform_area_m2         = round(area, 1),
            blocks_at_course         = b,
            blocks_cumulative        = cum_blocks,
            fraction_complete        = round(frac, 5),
            active_lanes             = lanes,
            cycle_time_min           = round(ct, 3),
            effective_capacity_per_day = round(cap, 2),
            throughput_ratio         = round(t_rat, 5),
            throughput_status        = t_stat.value,
            days_required_for_course = round(course_days, 5),
            cumulative_days_required = round(cumulative_days, 5),
            schedule_margin_days     = round(schedule_margin, 5),
            schedule_ratio_to_date   = round(schedule_ratio_to_date, 5),
            drift_this_course_mm     = round(drift_contrib, 5),
            cumulative_drift_mm      = round(drift_state.cumulative_mm, 5),
            correction_applied       = correction_applied,
            locked_in_drift_mm       = round(drift_state.locked_in_mm, 5),
            precision_status         = p_stat.value,
            hydraulic_phase          = hyd_phase.value,
            hydraulic_pressure_psi   = round(HYDRAULIC_PRESSURE_PSI, 3),
            reset_air_limited_time_s   = round(reset_air_time, 3),
            reset_water_limited_time_s = round(reset_water_time, 3),
            reset_required_time_s      = round(reset_required_time, 3),
            reset_time_ratio           = round(reset_ratio, 5),
            reset_time_gate_status     = reset_status,
            friction_support_active  = friction,
            phased_ops_required      = phased,
            urwg_active              = urwg_on,
            workcell_ratio           = round(wc_ratio, 4),
            workcell_status          = wc_status,
            final_course_closure_ratio = round(final_ratio, 4),
            final_course_status        = final_status,
            workers_per_block        = wpb,
            workers_on_duty_per_day  = workers_daily,
        )

        ms            = tracker.check(snap)
        snap.milestone = "; ".join(ms)
        snapshots.append(snap)

    return snapshots


# ===========================================================================
# PHASE STATISTICS
# ===========================================================================

@dataclass
class PhaseStats:
    phase:                    str
    start_course:             int
    end_course:               int
    course_count:             int
    total_blocks:             int
    avg_throughput_ratio:     float
    min_throughput_ratio:     float
    max_throughput_ratio:     float
    avg_lanes:                float
    avg_cycle_min:            float
    total_days_required:      float
    avg_days_per_course:      float
    max_days_course:          float
    schedule_status_counts:   dict[str, int]
    hydraulic_phases:         list[str]
    workcell_status_counts:   dict[str, int]
    correction_events:        int
    milestones:               list[str]


def compute_phase_stats(snapshots: list[CourseSnapshot]) -> list[PhaseStats]:
    phase_map: dict[str, list[CourseSnapshot]] = {}
    for snap in snapshots:
        phase_map.setdefault(snap.build_phase, []).append(snap)

    stats: list[PhaseStats] = []
    for phase_val in [p.value for p in BuildPhase]:
        group = phase_map.get(phase_val, [])
        if not group:
            continue

        t_ratios = [s.throughput_ratio for s in group]
        wc_counts: dict[str, int] = {}
        for s in group:
            wc_counts[s.workcell_status] = wc_counts.get(s.workcell_status, 0) + 1
        sched_counts: dict[str, int] = {}
        for s in group:
            status = schedule_status(s.schedule_ratio_to_date)
            sched_counts[status] = sched_counts.get(status, 0) + 1

        stats.append(PhaseStats(
            phase                  = phase_val,
            start_course           = group[0].course_label,
            end_course             = group[-1].course_label,
            course_count           = len(group),
            total_blocks           = sum(s.blocks_at_course for s in group),
            avg_throughput_ratio   = sum(t_ratios) / len(t_ratios),
            min_throughput_ratio   = min(t_ratios),
            max_throughput_ratio   = max(t_ratios),
            avg_lanes              = sum(s.active_lanes for s in group) / len(group),
            avg_cycle_min          = sum(s.cycle_time_min for s in group) / len(group),
            total_days_required    = sum(s.days_required_for_course for s in group),
            avg_days_per_course    = sum(s.days_required_for_course for s in group) / len(group),
            max_days_course        = max(s.days_required_for_course for s in group),
            schedule_status_counts = sched_counts,
            hydraulic_phases       = sorted(set(s.hydraulic_phase for s in group)),
            workcell_status_counts = wc_counts,
            correction_events      = sum(1 for s in group if s.correction_applied),
            milestones             = [s.milestone for s in group if s.milestone],
        ))
    return stats


# ===========================================================================
# CONSOLE REPORT
# ===========================================================================

_W  = 92
_HR = "─" * _W


def _print_header() -> None:
    print(_HR)
    print("  GIZA SEQUENCE SIMULATION  ·  COURSE-BY-COURSE ENGINEERING RECONSTRUCTION")
    print(f"  {FINAL_STATUS}")
    print(_HR)
    print(f"  Base {BASE_SIDE_M} m  ·  Height {HEIGHT_M} m  ·  {TOTAL_COURSES} courses  ·  "
          f"{TOTAL_BLOCKS:,} blocks  ·  {BUILD_YEARS:.0f} yr × {WORKDAYS_PER_YEAR:.0f} days/yr")
    print(f"  Required rate {REQUIRED_BLOCKS_PER_DAY:.1f} blk/day  ·  "
          f"Lower-node depth {LOWER_DEPTH_M} m → {HYDRAULIC_PRESSURE_PSI:.1f} psi  ·  "
          f"Package {'available' if _PACKAGE_AVAILABLE else 'fallback mode'}")
    print(_HR)


def _print_phase_table(phase_stats: list[PhaseStats]) -> None:
    print(f"\n{'BUILD PHASE SUMMARY':}")
    hdr = (f"  {'Phase':<28} {'Courses':>8}  {'Blocks':>9}  "
           f"{'Days':>8}  {'T-avg':>7}  {'T-min':>7}  {'Lanes':>6}  {'Cycle':>6}  "
           f"{'Workcell dominant':>20}  {'Hydraulic'}")
    print(hdr)
    print("  " + "─" * (_W - 2))
    for ps in phase_stats:
        wc_dominant = max(ps.workcell_status_counts, key=ps.workcell_status_counts.get)
        hyd_str     = "/".join(ps.hydraulic_phases)
        print(
            f"  {ps.phase:<28} "
            f" {ps.start_course:>3}–{ps.end_course:<3} "
            f" {ps.total_blocks:>9,} "
            f" {ps.total_days_required:>8.1f} "
            f" {ps.avg_throughput_ratio:>7.3f} "
            f" {ps.min_throughput_ratio:>7.3f} "
            f" {ps.avg_lanes:>6.1f} "
            f" {ps.avg_cycle_min:>6.1f} "
            f" {wc_dominant:>20} "
            f" {hyd_str}"
        )
    print()


def _print_schedule_closure_summary(snapshots: list[CourseSnapshot], phase_stats: list[PhaseStats]) -> None:
    total_days = compute_total_schedule_days(snapshots)
    ratio = schedule_ratio(total_days)
    status = schedule_status(ratio)
    print("SCHEDULE CLOSURE SUMMARY")
    print("  Load-bearing schedule gate: total course-days required vs available workdays.")
    print("  The per-course global-average throughput ratio is retained only as a pressure diagnostic.")
    print(f"  Total computed schedule days : {total_days:.1f}")
    print(f"  Allowed workdays             : {TOTAL_WORKDAYS:.1f}")
    print(f"  Schedule ratio               : {ratio:.3f}")
    print(f"  Schedule status              : {status}")
    print(f"  Schedule closes              : {'yes, under stated assumptions' if ratio >= 1.0 else 'no, under stated assumptions'}")
    print("\n  Largest schedule-consuming phases")
    for ps in sorted(phase_stats, key=lambda p: p.total_days_required, reverse=True)[:5]:
        print(f"  - {ps.phase}: {ps.total_days_required:.1f} days ({ps.total_blocks:,} blocks)")
    print("\n  Top 10 courses by days required")
    for snap in sorted(snapshots, key=lambda s: s.days_required_for_course, reverse=True)[:10]:
        print(
            f"  - Course {snap.course_label:>3}: {snap.days_required_for_course:>7.2f} days, "
            f"{snap.blocks_at_course:,} blocks, capacity {snap.effective_capacity_per_day:.1f}/day"
        )
    print()


def _print_milestones(snapshots: list[CourseSnapshot]) -> None:
    print("MILESTONE LOG")
    any_ms = False
    for snap in snapshots:
        if snap.milestone:
            for m in snap.milestone.split("; "):
                h_str = f"h={snap.height_m:>6.1f} m"
                print(f"  Course {snap.course_label:>3}  {h_str}  │  {m}")
                any_ms = True
    if not any_ms:
        print("  (no milestones recorded)")
    print()


def _print_throughput_profile(snapshots: list[CourseSnapshot]) -> None:
    print("THROUGHPUT PRESSURE DIAGNOSTIC  (global-average comparison only, not schedule closure)")
    print("  Load-bearing schedule gate is total course-days required versus available workdays.")
    hdr_fmt  = "  {:>6}  {:>7}  {:>7}  {:>12}  {:>7}  {:>8}  {:>14}"
    data_fmt = "  {:>6}  {:>7}  {:>7.3f}  {:>12}  {:>7}  {:>8.2f}  {:>14}"
    print(hdr_fmt.format("Course", "h (m)", "T-ratio", "T-status", "Lanes", "Cycle(m)", "Hyd-phase"))
    print("  " + "-" * 72)
    prev_status = None
    for snap in snapshots:
        emit = (
            snap.course % 10 == 0
            or snap.throughput_status != prev_status
            or snap.milestone
        )
        if emit:
            print(data_fmt.format(
                snap.course_label,
                f"{snap.height_m:.1f}",
                snap.throughput_ratio,
                snap.throughput_status,
                snap.active_lanes,
                snap.cycle_time_min,
                snap.hydraulic_phase,
            ))
        prev_status = snap.throughput_status
    print()


def _print_precision_summary(snapshots: list[CourseSnapshot]) -> None:
    total_corrections = sum(1 for s in snapshots if s.correction_applied)
    max_drift         = max(s.cumulative_drift_mm for s in snapshots)
    final_snap        = snapshots[-1]

    print("PRECISION DRIFT SUMMARY")
    print(f"  Total correction events  : {total_corrections}")
    print(f"  Peak cumulative drift    : {max_drift:.4f} mm  "
          f"(tolerance {TOLERANCE_MM:.1f} mm — "
          f"{'OK' if max_drift <= TOLERANCE_MM else 'EXCEEDED'})")
    print(f"  Final locked-in drift    : {final_snap.locked_in_drift_mm:.4f} mm")
    print(f"  Detect threshold         : {DETECT_THRESH_MM:.1f} mm  |  "
          f"Correction capacity : {CORRECT_CAP_MM:.1f} mm  |  "
          f"Check interval : every {CHECK_INTERVAL} course(s)")
    print("  Precision checks compare cumulative deviation against a persistent external datum,")
    print("  not isolated local stone-to-stone error alone.")
    print()


def _print_final_course_closure_summary(snapshots: list[CourseSnapshot]) -> None:
    print("FINAL-COURSE CLOSURE DIAGNOSTIC")
    print(f"  Required operation area : {FINAL_OPERATION_REQUIRED_M2:.1f} m²")
    print(f"  Optional internal staging credit when active: {URWG_STAGING_CREDIT_M2:.1f} m²")
    print("  Area alone is not enough; final closure also requires braking/control,")
    print("  reference visibility, and access/removal sequencing.")
    for snap in snapshots[-10:]:
        print(
            f"  - Course {snap.course_label:>3}: ratio {snap.final_course_closure_ratio:>6.3f}, "
            f"status {snap.final_course_status}, platform {snap.platform_area_m2:.1f} m²"
        )
    print("  Blocked claim: final courses become easy.")
    print()


def _print_reset_time_gate_summary(snapshots: list[CourseSnapshot]) -> None:
    active = next((s for s in snapshots if s.hydraulic_phase == HydraulicPhase.ACTIVE.value), snapshots[0])
    print("RESET_TIME_GATE SUMMARY")
    print("  Subsystem              : hydraulic_air_management")
    print(f"  Event volume           : {RESET_EVENT_VOLUME_M3:.1f} m³")
    print(f"  Vent area              : {RESET_VENT_AREA_M2:.4f} m²")
    print(f"  Water outlet area      : {RESET_WATER_OUTLET_AREA_M2:.4f} m²")
    print(f"  Discharge coefficient  : {RESET_DISCHARGE_COEFF:.2f}")
    print(f"  Chamber pressure       : {ATMOSPHERIC_PRESSURE_PA + HYDRAULIC_PRESSURE_PA:.0f} Pa")
    print(f"  Atmospheric pressure   : {ATMOSPHERIC_PRESSURE_PA:.0f} Pa")
    print(f"  Air-limited reset      : {active.reset_air_limited_time_s:.3f} s")
    print(f"  Water-limited reset    : {active.reset_water_limited_time_s:.3f} s")
    print(f"  Required reset         : {active.reset_required_time_s:.3f} s")
    print(f"  Allowed cycle window   : {ALLOWED_RESET_CYCLE_S:.1f} s")
    print(f"  Ratio                  : {active.reset_time_ratio:.3f}")
    print(f"  Status                 : {active.reset_time_gate_status}")
    print("  Claim                  : conditional subsystem-control screen")
    print("  Falsifier              : physical water-air scale test cannot reset without air lock,")
    print("                           unsafe pressure, or uncontrolled discharge")
    print()


def _print_claims() -> None:
    surviving = [
        "Ordinary mechanics move and place mass.",
        "Throughput repaired by lane / cycle / workcell assumptions.",
        "Precision maintained by drift suppression and restoration loops.",
        f"Lower-node hydraulic: conditional air-management / vent / reset / isolation "
        f"(courses {HYD_ACTIVE_START + 1}–{HYD_SEALED_COURSE}).",
        "Reset-time gate: conditional subsystem-control screen.",
        "Granite plugs: final isolation / decommissioning boundary.",
        "Upper workcell closure requires phased sequencing.",
        f"{INTERNAL_STAGING_LABEL.capitalize()}: optional conditional congestion/staging assist.",
    ]
    blocked = [
        "Historical use is proven.",
        "Hydraulic lifting is proven.",
        "Water moved every block.",
        "Lower pulse seats upper blocks.",
        "Long-range hydraulic / vibration transfer closes upper placement.",
        "King's Chamber receives useful pressure from lower node under baseline.",
        "Grand Gallery is proven as waveguide.",
        "Salt / alum / sulfate residues prove the system by themselves.",
        "Reset timing proves historical hydraulic use.",
        "Upper workcell closes without phased sequencing.",
        "Optional internal staging gallery proves its own purpose.",
        "Final courses become easy.",
    ]
    print("SURVIVING CLAIMS")
    for s in surviving:
        print(f"  ✓  {s}")
    print("\nBLOCKED CLAIMS")
    for b in blocked:
        print(f"  ✗  {b}")
    print()


def _print_footer(snapshots: list[CourseSnapshot]) -> None:
    last = snapshots[-1]
    print(_HR)
    print(f"  Simulation complete.  Courses: {TOTAL_COURSES}  |  "
          f"Blocks placed: {last.blocks_cumulative:,}  |  "
          f"Fraction: {last.fraction_complete:.5f}")
    print(f"  Final drift: {last.cumulative_drift_mm:.4f} mm  |  "
          f"Locked-in: {last.locked_in_drift_mm:.4f} mm  |  "
          f"Hydraulic sealed course: {HYD_SEALED_COURSE}")
    print(f"\n  {CLAIM_BOUNDARY}")
    print(_HR)


def print_full_report(snapshots: list[CourseSnapshot], phase_stats: list[PhaseStats]) -> None:
    _print_header()
    _print_phase_table(phase_stats)
    _print_schedule_closure_summary(snapshots, phase_stats)
    _print_milestones(snapshots)
    _print_throughput_profile(snapshots)
    _print_precision_summary(snapshots)
    _print_final_course_closure_summary(snapshots)
    _print_reset_time_gate_summary(snapshots)
    _print_claims()
    _print_footer(snapshots)


# ===========================================================================
# CSV EXPORT
# ===========================================================================

def export_csv(snapshots: list[CourseSnapshot], path: Path) -> None:
    if not snapshots:
        return
    field_names = [f.name for f in dataclasses.fields(snapshots[0])]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=field_names)
        writer.writeheader()
        for snap in snapshots:
            row: dict[str, object] = {}
            for fname in field_names:
                v = getattr(snap, fname)
                row[fname] = str(v) if isinstance(v, bool) else v
            writer.writerow(row)


# ===========================================================================
# MARKDOWN REPORT
# ===========================================================================

def export_markdown(
    snapshots: list[CourseSnapshot],
    phase_stats: list[PhaseStats],
    path: Path,
) -> None:
    total_corrections = sum(1 for s in snapshots if s.correction_applied)
    max_drift         = max(s.cumulative_drift_mm for s in snapshots)
    final             = snapshots[-1]
    active_reset      = next((s for s in snapshots if s.hydraulic_phase == HydraulicPhase.ACTIVE.value), snapshots[0])
    total_schedule_days = compute_total_schedule_days(snapshots)
    final_schedule_ratio = schedule_ratio(total_schedule_days)
    final_schedule_status = schedule_status(final_schedule_ratio)
    top_schedule_phases = sorted(phase_stats, key=lambda p: p.total_days_required, reverse=True)[:5]
    top_schedule_courses = sorted(snapshots, key=lambda s: s.days_required_for_course, reverse=True)[:10]

    # First occurrences of each throughput status
    status_first: dict[str, int] = {}
    for snap in snapshots:
        if snap.throughput_status not in status_first:
            status_first[snap.throughput_status] = snap.course_label

    lines: list[str] = [
        "# Giza Sequence Simulation Report",
        "",
        f"**Status:** `{FINAL_STATUS}`",
        "",
        f"> {CLAIM_BOUNDARY}",
        "",
        "---",
        "",
        "## Pyramid Parameters",
        "",
        "| Parameter | Value |",
        "|---|---|",
        f"| Base side | {BASE_SIDE_M} m |",
        f"| Height | {HEIGHT_M} m |",
        f"| Total courses | {TOTAL_COURSES} |",
        f"| Total blocks | {TOTAL_BLOCKS:,} |",
        f"| Build duration | {BUILD_YEARS:.0f} yr × {WORKDAYS_PER_YEAR:.0f} days/yr"
        f" = {TOTAL_WORKDAYS:.0f} workdays |",
        f"| Required rate | {REQUIRED_BLOCKS_PER_DAY:.1f} blocks/day |",
        f"| Lower-node depth | {LOWER_DEPTH_M} m → {HYDRAULIC_PRESSURE_PSI:.2f} psi |",
        f"| Hydraulic active window | Courses {HYD_ACTIVE_START + 1}–{HYD_DECOMMISSION_START} |",
        f"| Reset-time gate | {active_reset.reset_time_gate_status}, ratio {active_reset.reset_time_ratio:.3f} |",
        f"| Friction support limit | {FRICTION_HEIGHT_LIMIT_M:.0f} m height |",
        "",
        "---",
        "",
        "## Build Phase Summary",
        "",
        "| Phase | Courses | Blocks | Days required | T-avg | T-min | T-max | Avg lanes | Hydraulic phases |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for ps in phase_stats:
        hyd = " / ".join(ps.hydraulic_phases)
        lines.append(
            f"| {ps.phase} "
            f"| {ps.start_course}–{ps.end_course} "
            f"| {ps.total_blocks:,} "
            f"| {ps.total_days_required:.1f} "
            f"| {ps.avg_throughput_ratio:.3f} "
            f"| {ps.min_throughput_ratio:.3f} "
            f"| {ps.max_throughput_ratio:.3f} "
            f"| {ps.avg_lanes:.1f} "
            f"| {hyd} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Schedule Closure Summary",
        "",
        "The load-bearing schedule gate is total course-days required versus available workdays.",
        "The old per-course throughput ratio is retained only as a pressure diagnostic.",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Total computed schedule days | {total_schedule_days:.1f} |",
        f"| Allowed workdays | {TOTAL_WORKDAYS:.1f} |",
        f"| Schedule ratio | {final_schedule_ratio:.3f} |",
        f"| Schedule status | {final_schedule_status} |",
        f"| Schedule closes under stated assumptions | {'yes' if final_schedule_ratio >= 1.0 else 'no'} |",
        "",
        "### Largest Schedule-Consuming Phases",
        "",
        "| Phase | Days required | Blocks |",
        "|---|---:|---:|",
    ]
    for ps in top_schedule_phases:
        lines.append(f"| {ps.phase} | {ps.total_days_required:.1f} | {ps.total_blocks:,} |")

    lines += [
        "",
        "### Top 10 Courses By Days Required",
        "",
        "| Course | Days required | Blocks | Capacity/day |",
        "|---:|---:|---:|---:|",
    ]
    for snap in top_schedule_courses:
        lines.append(
            f"| {snap.course_label} | {snap.days_required_for_course:.2f} | "
            f"{snap.blocks_at_course:,} | {snap.effective_capacity_per_day:.1f} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Milestone Log",
        "",
        "| Course | Height (m) | Milestone |",
        "|---|---|---|",
    ]
    for snap in snapshots:
        if snap.milestone:
            for m in snap.milestone.split("; "):
                lines.append(f"| {snap.course_label} | {snap.height_m:.1f} | {m} |")

    lines += [
        "",
        "---",
        "",
        "## Throughput Pressure Analysis",
        "",
        "The old per-course throughput ratio is retained as a pressure diagnostic. "
        "It compares course capacity to the global average required rate, not to the actual block count in that course. "
        "The load-bearing schedule gate is now total course-days required versus available workdays.",
        "",
        "| Status | First occurrence (course) | Implication |",
        "|---|---|---|",
        f"| green    | {status_first.get('green',    '—')} | Comfortable schedule margin ≥ 1.20 |",
        f"| adequate | {status_first.get('adequate', '—')} | On schedule, thin margin 1.00–1.20 |",
        f"| warning  | {status_first.get('warning',  '—')} | Below schedule 0.85–1.00 — lane/cycle repair needed |",
        f"| critical | {status_first.get('critical', '—')} | Severe deficit < 0.85 — structural intervention required |",
        "",
        "Surviving claim: throughput is **repairable** by lane / cycle / workcell assumptions.  ",
        "This simulation shows *where* that repair budget is consumed.",
        "",
        "---",
        "",
        "## Final-Course Closure Diagnostic",
        "",
        "The optional upper internal staging gallery reduces congestion but does not eliminate final-course criticality.",
        "Area alone is not enough; final closure also requires braking/control method, reference visibility, and access/removal sequencing.",
        "",
        "| Input / metric | Value |",
        "|---|---|",
        f"| block_footprint_m2 | {FINAL_BLOCK_FOOTPRINT_M2:.1f} |",
        f"| crew_footprint_m2 | {FINAL_CREW_FOOTPRINT_M2:.1f} |",
        f"| lever_clearance_m2 | {FINAL_LEVER_CLEARANCE_M2:.1f} |",
        f"| reference_access_m2 | {FINAL_REFERENCE_ACCESS_M2:.1f} |",
        f"| operation_required_area_m2 | {FINAL_OPERATION_REQUIRED_M2:.1f} |",
        f"| optional_internal_staging_credit_m2 | {URWG_STAGING_CREDIT_M2:.1f} |",
        "",
        "| Course | Ratio | Status | Platform area (m²) |",
        "|---:|---:|---|---:|",
    ]
    for snap in snapshots[-10:]:
        lines.append(
            f"| {snap.course_label} | {snap.final_course_closure_ratio:.3f} | "
            f"{snap.final_course_status} | {snap.platform_area_m2:.1f} |"
        )

    lines += [
        "",
        "**Blocked claim:** Final courses become easy.",
        "",
        "---",
        "",
        "## Hydraulic Lifecycle",
        "",
        "| Phase | Course range | Engineering role |",
        "|---|---|---|",
        f"| pre_build    | 1–{HYD_ACTIVE_START}           | Lower chamber excavation and preparation |",
        f"| active       | {HYD_ACTIVE_START + 1}–{HYD_DECOMMISSION_START}       "
        f"| Air-management / vent / reset / isolation active |",
        f"| decommission | {HYD_DECOMMISSION_START + 1}–{HYD_SEALED_COURSE} | Isolation sequence, plug staging |",
        f"| sealed       | {HYD_SEALED_COURSE + 1}–{TOTAL_COURSES}     | Granite plugs in final closed position |",
        "",
        f"Lower-node friction-reduction support is credited **only** where pyramid height ≤ {FRICTION_HEIGHT_LIMIT_M:.0f} m.",
        "",
        "**BLOCKED claim:** Lower pulse seats upper blocks.  ",
        "**SURVIVING claim:** Lower node may function as hydraulic air-management / vent / reset / isolation.",
        "",
        "### Reset-Time Gate",
        "",
        "| Input / metric | Value |",
        "|---|---|",
        f"| event_volume_m3 | {RESET_EVENT_VOLUME_M3:.1f} |",
        f"| vent_area_m2 | {RESET_VENT_AREA_M2:.4f} |",
        f"| discharge_coefficient | {RESET_DISCHARGE_COEFF:.2f} |",
        f"| chamber_pressure_pa | {ATMOSPHERIC_PRESSURE_PA + HYDRAULIC_PRESSURE_PA:.0f} |",
        f"| atmospheric_pressure_pa | {ATMOSPHERIC_PRESSURE_PA:.0f} |",
        f"| water_outlet_area_m2 | {RESET_WATER_OUTLET_AREA_M2:.4f} |",
        f"| allowed_cycle_time_s | {ALLOWED_RESET_CYCLE_S:.1f} |",
        f"| air_limited_reset_time_s | {active_reset.reset_air_limited_time_s:.3f} |",
        f"| water_limited_reset_time_s | {active_reset.reset_water_limited_time_s:.3f} |",
        f"| required_reset_time_s | {active_reset.reset_required_time_s:.3f} |",
        f"| ratio | {active_reset.reset_time_ratio:.3f} |",
        f"| status | {active_reset.reset_time_gate_status} |",
        "",
        "Pass condition: `allowed_cycle_time_s / required_reset_time_s >= 1.0`.  ",
        "Fail condition: reset takes longer than the available cycle window.  ",
        "Falsifier: physical water-air scale test cannot reset without air lock, unsafe pressure, or uncontrolled discharge.",
        "",
        "---",
        "",
        "## Precision Drift Summary",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total correction events | {total_corrections} |",
        f"| Peak cumulative drift | {max_drift:.4f} mm |",
        f"| Final locked-in drift | {final.locked_in_drift_mm:.4f} mm |",
        f"| Build tolerance | {TOLERANCE_MM:.1f} mm |",
        f"| Detection threshold | {DETECT_THRESH_MM:.1f} mm |",
        f"| Correction capacity (single event) | {CORRECT_CAP_MM:.1f} mm |",
        "",
        "Surviving claim: precision is maintained by drift suppression and restoration loops,  ",
        "not by repeated perfect placement.",
        "",
        "Each precision check compares the current working reference against a persistent external datum.  ",
        "The measured quantity is cumulative deviation, not local stone-to-stone error alone.",
        "",
        "---",
        "",
        "## Surviving Claims",
        "",
        "- Ordinary mechanics move and place mass.",
        "- Throughput is repaired by lane / cycle / workcell assumptions.",
        "- Precision is maintained by restoration loops.",
        f"- Lower-node hydraulic: conditional air-management / vent / reset / isolation "
        f"(courses {HYD_ACTIVE_START + 1}–{HYD_SEALED_COURSE}).",
        "- Reset-time gate: conditional subsystem-control screen.",
        "- Granite plugs are the final isolation / decommissioning boundary.",
        "- Upper workcell closure requires phased sequencing.",
        f"- {INTERNAL_STAGING_LABEL.capitalize()}: optional conditional congestion/staging assist.",
        "",
        "## Blocked Claims",
        "",
        "- Historical use is proven.",
        "- Hydraulic lifting is proven.",
        "- Water moved every block.",
        "- Lower pulse seats upper blocks.",
        "- Long-range hydraulic / vibration transfer closes upper placement.",
        "- King's Chamber receives useful pressure from lower node under baseline.",
        "- Grand Gallery is proven as waveguide.",
        "- Salt / alum / sulfate residues prove the system by themselves.",
        "- Reset timing proves historical hydraulic use.",
        "- Upper workcell closes without phased sequencing.",
        "- Optional internal staging gallery proves its own purpose.",
        "- Final courses become easy.",
        "",
        "---",
        "",
        f"*Generated by `giza_sequence_sim.py`  |  {FINAL_STATUS}*",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


# ===========================================================================
# ENTRY POINT
# ===========================================================================

def main() -> None:
    # Ensure UTF-8 output on Windows consoles
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    output_dir = Path(__file__).parent / "sequence_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "giza_sequence_summary.csv"
    md_path  = output_dir / "giza_sequence_report.md"

    snapshots   = run_sequence_simulation()
    phase_stats = compute_phase_stats(snapshots)

    print_full_report(snapshots, phase_stats)

    export_csv(snapshots, csv_path)
    export_markdown(snapshots, phase_stats, md_path)

    print(f"\n  CSV  →  {csv_path}")
    print(f"  MD   →  {md_path}\n")


if __name__ == "__main__":
    main()
