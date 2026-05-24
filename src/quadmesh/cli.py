"""Command-line driver. Replaces MATLAB Main.m for the headless case."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from chilmesh import CHILmesh

from .pipeline import run_pipeline
from .quality_report import compute_quality_stats, format_quality_report


def _load_polygon(path: Path) -> np.ndarray:
    """Load CSV of XY points. Two columns (x, y). Header row optional."""
    data = np.loadtxt(path, delimiter=",", skiprows=0, ndmin=2)
    if data.shape[1] < 2:
        raise ValueError(f"polygon CSV must have ≥2 cols (XY); got {data.shape}")
    return data[:, :2]


def main(argv=None) -> int:
    """Entry point. Returns CLI exit code (0 on success)."""
    parser = argparse.ArgumentParser(
        prog="quadmesh",
        description="Convert tri mesh to quad mesh (fort.14 in/out).",
    )
    parser.add_argument("input", type=Path, help="Input fort.14 path.")
    parser.add_argument("-o", "--output", type=Path, required=True,
                         help="Output fort.14 path.")
    parser.add_argument("--polygon", type=Path, default=None,
                         help="Optional polygon CSV mask (X,Y per row).")
    parser.add_argument("--no-post-process", action="store_true",
                         help="Skip doublet/QVM/cleanup/smooth post-process.")
    parser.add_argument("--no-remove-edges", action="store_true",
                         help="Don't collapse boundary edges/quads.")
    parser.add_argument("--n-smooth-iter", type=int, default=3,
                         help="FEM smooth passes after post-process (default 3).")
    parser.add_argument("--max-outer-iter", type=int, default=5,
                         help="Outer post-process loop cap (default 5).")
    parser.add_argument("--max-inner-iter", type=int, default=5,
                         help="Inner doublet+QVM loop cap (default 5).")
    args = parser.parse_args(argv)

    if not args.input.exists():
        parser.error(f"input not found: {args.input}")

    mesh = CHILmesh.read_from_fort14(args.input)
    print(f"loaded: {args.input.name} — {mesh.n_elems} elems, {mesh.n_verts} verts, {mesh.n_layers} layers")

    polygon = _load_polygon(args.polygon) if args.polygon else None

    out = run_pipeline(
        mesh,
        polygon=polygon,
        can_remove_edges=not args.no_remove_edges,
        n_smooth_iter=args.n_smooth_iter,
        do_post_process=not args.no_post_process,
        max_outer_iter=args.max_outer_iter,
        max_inner_iter=args.max_inner_iter,
    )

    stats = compute_quality_stats(out)
    print(f"output: {out.n_elems} elems, {out.n_verts} verts")
    print(format_quality_report(stats))
    out.write_to_fort14(str(args.output))
    print(f"written: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
