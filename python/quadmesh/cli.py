"""Command-line driver. Replaces MATLAB Main.m for the headless case."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from chilmesh import CHILmesh

from .pipeline import run_pipeline


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
    parser.add_argument("--n-smooth-iter", type=int, default=50)
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
    )

    print(f"output: {out.n_elems} elems, {out.n_verts} verts")
    out.write_to_fort14(str(args.output))
    print(f"written: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
