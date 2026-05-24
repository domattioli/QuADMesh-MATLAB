"""QuADMESH+ Python port. Tri-to-quad mesh generator on top of chilmesh."""
from __future__ import annotations

__version__ = "0.1.0"

from .tri2quad import tri2quad_routine as tri2quad
from .post_process import post_process_routine as post_process, two_part_smoother
from .quality_report import compute_quality_stats, format_quality_report
from .repair import repair_chilmesh, repair_mesh

__all__ = [
    "tri2quad",
    "post_process",
    "two_part_smoother",
    "compute_quality_stats",
    "format_quality_report",
    "repair_mesh",
    "repair_chilmesh",
    "__version__",
]


def __getattr__(name: str):
    if name == "create_quad_domain":
        from .create_quad_domain import create_quad_domain
        return create_quad_domain
    if name == "run_pipeline":
        from .pipeline import run_pipeline
        return run_pipeline
    raise AttributeError(f"module 'quadmesh' has no attribute {name!r}")
