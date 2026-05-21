"""
giza_sequence_viz.py
====================
PyVista 3D visualisation companion for giza_sequence_sim.py.

Reads sequence_output/giza_sequence_summary.csv and renders a
course-stratified pyramid mesh coloured by any simulation scalar.

Views available
---------------
  throughput   — T-ratio per course  (green = good, red = critical)
  hydraulic    — Lifecycle phase      (grey / blue / orange / dark-red)
  drift        — Cumulative precision drift (mm)
  workcell     — Workcell area ratio
  all          — 2×2 subplot of all four (default)

Optional
--------
  --gif        — Export animated build sequence to sequence_output/giza_build.gif

Requirements
------------
    pip install pyvista

Run
---
    python giza_sequence_viz.py
    python giza_sequence_viz.py --mode throughput
    python giza_sequence_viz.py --mode hydraulic
    python giza_sequence_viz.py --gif
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import pyvista as pv

# ---------------------------------------------------------------------------
# Locate the CSV produced by giza_sequence_sim.py
# ---------------------------------------------------------------------------
_HERE    = Path(__file__).parent
_CSV     = _HERE / "sequence_output" / "giza_sequence_summary.csv"
_GIF_OUT = _HERE / "sequence_output" / "giza_build.gif"

# Pyramid geometry constants (must match giza_sequence_sim.py)
BASE_SIDE_M:   float = 230.33
HEIGHT_M:      float = 146.7
TOTAL_COURSES: int   = 210


# ===========================================================================
# Data loading
# ===========================================================================

def load_csv(path: Path = _CSV) -> list[dict]:
    if not path.exists():
        print(f"[ERROR] CSV not found: {path}")
        print("        Run giza_sequence_sim.py first to generate it.")
        sys.exit(1)
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ===========================================================================
# Geometry helpers
# ===========================================================================

def course_frustum_points(side_bot: float, side_top: float,
                           z_bot: float, z_top: float) -> np.ndarray:
    """
    Return 8 vertices of one course frustum (square cross-section).
    Vertex order:
        0-3: bottom ring (counter-clockwise from -x,-y corner)
        4-7: top ring    (same order)
    """
    hb, ht = side_bot / 2.0, side_top / 2.0
    return np.array([
        [-hb, -hb, z_bot],  # 0
        [ hb, -hb, z_bot],  # 1
        [ hb,  hb, z_bot],  # 2
        [-hb,  hb, z_bot],  # 3
        [-ht, -ht, z_top],  # 4
        [ ht, -ht, z_top],  # 5
        [ ht,  ht, z_top],  # 6
        [-ht,  ht, z_top],  # 7
    ], dtype=float)


def course_frustum_faces(offset: int) -> list[list[int]]:
    """
    6 quad faces for the frustum, referenced from vertex index `offset`.
    PyVista face format: [n_verts, i0, i1, i2, i3, ...]
    Normals point outward.
    """
    o = offset
    return [
        [4, o+3, o+2, o+1, o+0],  # bottom  (facing -z)
        [4, o+4, o+5, o+6, o+7],  # top     (facing +z)
        [4, o+0, o+1, o+5, o+4],  # front   (-y face)
        [4, o+1, o+2, o+6, o+5],  # right   (+x face)
        [4, o+2, o+3, o+7, o+6],  # back    (+y face)
        [4, o+3, o+0, o+4, o+7],  # left    (-x face)
    ]


# ===========================================================================
# Mesh builder
# ===========================================================================

_HYD_INT = {"pre_build": 0, "active": 1, "decommission": 2, "sealed": 3}
_TSTAT_INT = {"green": 3, "adequate": 2, "warning": 1, "critical": 0}


def build_pyramid_mesh(rows: list[dict]) -> pv.PolyData:
    """
    Build a single PolyData mesh whose cells are one frustum per course.
    Each course contributes 6 quad faces (bottom, top, 4 sides).
    Cell data arrays are attached for every simulation scalar.
    """
    course_h = HEIGHT_M / TOTAL_COURSES

    all_pts:   list[np.ndarray] = []
    all_faces: list[int]        = []

    # Per-cell scalar accumulators  (6 cells per course = 6 identical values)
    t_ratio:    list[float] = []
    hyd_int:    list[int]   = []
    drift_mm:   list[float] = []
    wc_ratio:   list[float] = []
    tstat_int:  list[int]   = []
    course_num: list[int]   = []
    height_arr: list[float] = []
    lanes_arr:  list[int]   = []
    friction_a: list[int]   = []

    point_offset = 0

    for row in rows:
        n        = int(row["course"])
        side_bot = float(row["platform_side_m"])
        side_top = BASE_SIDE_M * max(0.0, 1.0 - (n + 1) / TOTAL_COURSES)
        z_bot    = float(row["height_m"])
        z_top    = z_bot + course_h

        pts = course_frustum_points(side_bot, side_top, z_bot, z_top)
        all_pts.append(pts)

        for face in course_frustum_faces(point_offset):
            all_faces.extend(face)

        # 6 faces per course → 6 identical cell scalars
        for _ in range(6):
            t_ratio.append(float(row["throughput_ratio"]))
            hyd_int.append(_HYD_INT.get(row["hydraulic_phase"], 0))
            drift_mm.append(float(row["cumulative_drift_mm"]))
            wc_ratio.append(min(float(row["workcell_ratio"]), 3.0))
            tstat_int.append(_TSTAT_INT.get(row["throughput_status"], 0))
            course_num.append(int(row["course_label"]))
            height_arr.append(float(row["height_m"]))
            lanes_arr.append(int(row["active_lanes"]))
            friction_a.append(1 if row["friction_support_active"] == "True" else 0)

        point_offset += 8

    mesh = pv.PolyData(
        np.vstack(all_pts),
        np.array(all_faces, dtype=int),
    )
    mesh.cell_data["throughput_ratio"]     = np.array(t_ratio,    dtype=float)
    mesh.cell_data["hydraulic_phase_int"]  = np.array(hyd_int,    dtype=int)
    mesh.cell_data["cumulative_drift_mm"]  = np.array(drift_mm,   dtype=float)
    mesh.cell_data["workcell_ratio"]       = np.array(wc_ratio,   dtype=float)
    mesh.cell_data["throughput_status_int"]= np.array(tstat_int,  dtype=int)
    mesh.cell_data["course_number"]        = np.array(course_num, dtype=int)
    mesh.cell_data["height_m"]             = np.array(height_arr, dtype=float)
    mesh.cell_data["active_lanes"]         = np.array(lanes_arr,  dtype=int)
    mesh.cell_data["friction_support"]     = np.array(friction_a, dtype=int)
    return mesh


# ===========================================================================
# Individual plot configurations
# ===========================================================================

def _add_throughput(pl: pv.Plotter, mesh: pv.PolyData) -> None:
    pl.add_mesh(
        mesh,
        scalars="throughput_ratio",
        cmap="RdYlGn",
        clim=[0.0, 1.25],
        show_scalar_bar=True,
        scalar_bar_args={
            "title": "Throughput Ratio\n(cap / required)",
            "n_labels": 6,
            "label_font_size": 11,
        },
    )
    pl.add_text("Throughput Pressure\nGreen ≥ 1.0   Red < 0.85",
                position="upper_left", font_size=9, color="white")
    # Horizontal reference lines at schedule milestones
    for h, label, col in [
        (HEIGHT_M * 0.30, "30% h — hydraulic friction zone ends", "cyan"),
        (HEIGHT_M * 0.50, "50% h", "yellow"),
        (HEIGHT_M * 0.75, "75% h", "orange"),
    ]:
        line = pv.Line((-BASE_SIDE_M * 0.55, 0, h), (BASE_SIDE_M * 0.55, 0, h))
        pl.add_mesh(line, color=col, line_width=1.5, label=label)


def _add_hydraulic(pl: pv.Plotter, mesh: pv.PolyData) -> None:
    from matplotlib.colors import ListedColormap

    cmap = ListedColormap(["#888888", "#4a90d9", "#e8a838", "#8b0000"])
    pl.add_mesh(
        mesh,
        scalars="hydraulic_phase_int",
        cmap=cmap,
        clim=[-0.5, 3.5],
        show_scalar_bar=True,
        annotations={0: "pre_build", 1: "active", 2: "decommission", 3: "sealed"},
        scalar_bar_args={
            "title": "Hydraulic Phase",
            "n_labels": 0,
            "label_font_size": 10,
        },
    )
    pl.add_text(
        "Hydraulic Lifecycle\n"
        "Grey=pre  Blue=active  Amber=decommission  Red=sealed",
        position="upper_left", font_size=9, color="white",
    )


def _add_drift(pl: pv.Plotter, mesh: pv.PolyData) -> None:
    pl.add_mesh(
        mesh,
        scalars="cumulative_drift_mm",
        cmap="coolwarm",
        clim=[0.0, 1.5],
        show_scalar_bar=True,
        scalar_bar_args={
            "title": "Cumulative Drift (mm)\n1.5 mm = detect threshold",
            "n_labels": 5,
            "label_font_size": 11,
        },
    )
    pl.add_text("Precision Drift\nCool=nominal   Warm=near detection threshold",
                position="upper_left", font_size=9, color="white")


def _add_workcell(pl: pv.Plotter, mesh: pv.PolyData) -> None:
    pl.add_mesh(
        mesh,
        scalars="workcell_ratio",
        cmap="RdYlBu",
        clim=[0.0, 3.0],
        show_scalar_bar=True,
        scalar_bar_args={
            "title": "Workcell Ratio\n(area / 180 m²)",
            "n_labels": 5,
            "label_font_size": 11,
        },
    )
    pl.add_text("Workcell Constraint\nBlue=unrestricted   Red=critical (<1.0)",
                position="upper_left", font_size=9, color="white")


# ===========================================================================
# Plot modes
# ===========================================================================

def _camera_kwargs() -> dict:
    return dict(
        azimuth=35, elevation=20,
    )


def plot_single(mesh: pv.PolyData, mode: str) -> None:
    """Single-window plot for one scalar mode."""
    title_map = {
        "throughput": "Throughput Pressure",
        "hydraulic":  "Hydraulic Lifecycle",
        "drift":      "Precision Drift",
        "workcell":   "Workcell Constraint",
    }
    pl = pv.Plotter(
        title=f"Giza Sequence — {title_map.get(mode, mode)}",
        window_size=(1200, 900),
    )
    pl.set_background("black")
    adders = {
        "throughput": _add_throughput,
        "hydraulic":  _add_hydraulic,
        "drift":      _add_drift,
        "workcell":   _add_workcell,
    }
    adders[mode](pl, mesh)
    pl.add_axes(line_width=2)
    pl.camera.azimuth   = 35
    pl.camera.elevation = 20
    pl.show()


def plot_all(mesh: pv.PolyData) -> None:
    """2×2 subplot showing all four scalars simultaneously."""
    pl = pv.Plotter(
        shape=(2, 2),
        title="Giza Sequence Simulation — Four-View Panel",
        window_size=(1600, 1100),
    )
    pl.set_background("black")

    for row_i, col_i, adder in [
        (0, 0, _add_throughput),
        (0, 1, _add_hydraulic),
        (1, 0, _add_drift),
        (1, 1, _add_workcell),
    ]:
        pl.subplot(row_i, col_i)
        pl.set_background("black")
        adder(pl, mesh)
        pl.camera.azimuth   = 35
        pl.camera.elevation = 20
        pl.add_axes(line_width=2)

    pl.link_views()   # synchronise camera rotation across all subplots
    pl.show()


# ===========================================================================
# Animated build-sequence GIF
# ===========================================================================

def _build_course_meshes(rows: list[dict]) -> list[pv.PolyData]:
    """
    Build a list of incremental pyramid meshes — mesh[i] contains courses 0..i.
    Used for the animated build sequence.
    """
    course_h = HEIGHT_M / TOTAL_COURSES
    meshes: list[pv.PolyData] = []

    all_pts:    list[np.ndarray] = []
    all_faces:  list[int]        = []
    t_ratios:   list[float]      = []
    hyd_ints:   list[int]        = []
    point_offset = 0

    for i, row in enumerate(rows):
        n        = int(row["course"])
        side_bot = float(row["platform_side_m"])
        side_top = BASE_SIDE_M * max(0.0, 1.0 - (n + 1) / TOTAL_COURSES)
        z_bot    = float(row["height_m"])
        z_top    = z_bot + course_h

        pts = course_frustum_points(side_bot, side_top, z_bot, z_top)
        all_pts.append(pts)

        for face in course_frustum_faces(point_offset):
            all_faces.extend(face)

        for _ in range(6):
            t_ratios.append(float(row["throughput_ratio"]))
            hyd_ints.append(_HYD_INT.get(row["hydraulic_phase"], 0))

        point_offset += 8

        # Take a snapshot at every 5th course + final course
        if i % 5 == 0 or i == len(rows) - 1:
            snap = pv.PolyData(
                np.vstack(all_pts),
                np.array(all_faces, dtype=int),
            )
            snap.cell_data["throughput_ratio"]    = np.array(t_ratios, dtype=float)
            snap.cell_data["hydraulic_phase_int"] = np.array(hyd_ints, dtype=int)
            meshes.append(snap)

    return meshes


def export_gif(rows: list[dict], out_path: Path = _GIF_OUT) -> None:
    """
    Render an animated build sequence GIF.
    Each frame adds the next 5 courses, coloured by throughput ratio.
    Saves to sequence_output/giza_build.gif (~180 frames at 5-course steps).
    """
    print(f"[gif] Building animation frames ... (this takes ~60 s)")
    incremental = _build_course_meshes(rows)

    pl = pv.Plotter(
        off_screen=True,
        window_size=(1024, 768),
        title="Giza Build Sequence",
    )
    pl.set_background("black")
    pl.open_gif(str(out_path), fps=12)

    for snap in incremental:
        pl.clear_actors()
        pl.add_mesh(
            snap,
            scalars="throughput_ratio",
            cmap="RdYlGn",
            clim=[0.0, 1.25],
            show_scalar_bar=False,
        )
        pl.camera.azimuth   = 35
        pl.camera.elevation = 20
        pl.add_axes(line_width=2)
        pl.write_frame()

    pl.close()
    print(f"[gif] Saved → {out_path}")


# ===========================================================================
# CLI entry point
# ===========================================================================

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="PyVista 3D visualisation for giza_sequence_sim.py output."
    )
    p.add_argument(
        "--mode",
        choices=["throughput", "hydraulic", "drift", "workcell", "all"],
        default="all",
        help="Which scalar to visualise (default: all = 2×2 panel)",
    )
    p.add_argument(
        "--gif",
        action="store_true",
        help="Export animated build-sequence GIF instead of opening a window",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    rows = load_csv()

    if args.gif:
        export_gif(rows)
        return

    print(f"[viz] Building pyramid mesh from {len(rows)} courses ...")
    mesh = build_pyramid_mesh(rows)
    print(f"[viz] Mesh: {mesh.n_points:,} points  {mesh.n_cells:,} cells")
    print(f"[viz] Scalars: {list(mesh.cell_data.keys())}")
    print(f"[viz] Mode: {args.mode}")
    print()
    print("  Controls: left-drag=rotate  right-drag=zoom  middle-drag=pan")
    print("  Press Q to close the window.")
    print()

    if args.mode == "all":
        plot_all(mesh)
    else:
        plot_single(mesh, args.mode)


if __name__ == "__main__":
    main()
