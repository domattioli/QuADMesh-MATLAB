"""End-to-end pipeline tests."""

from __future__ import annotations

import numpy as np
import pytest

from quadmesh import tri2quad
from quadmesh.doublet_collapse import doublet_collapse
from quadmesh.quad_vertex_merge import quad_vertex_merge
from quadmesh.cleanup_boundary_quads import cleanup_boundary_quads
from quadmesh.post_process import post_process_routine
from quadmesh.pipeline import run_pipeline


def test_doublet_collapse_no_op_on_input(test_case_1):
    """Doublet collapse should be safe even when no doublets exist."""
    out = doublet_collapse(test_case_1)
    assert out.n_elems > 0


def test_qvm_no_op_on_tri_mesh(test_case_1):
    """QVM does nothing on a pure tri mesh."""
    out = quad_vertex_merge(test_case_1)
    assert out.n_elems == test_case_1.n_elems


def test_post_process_on_tri2quad_output(test_case_1):
    """tri2quad → post_process should produce a valid CHILmesh."""
    quad = tri2quad(test_case_1, can_remove_edges=True)
    final = post_process_routine(quad, can_remove_edges=True, n_smooth_iter=10)
    assert final.n_elems > 0
    assert final.n_verts > 0
    # No zero-area elems.
    areas = final.signed_area()
    assert np.all(np.abs(areas) > 1e-12)


def test_run_pipeline_end_to_end(test_case_1):
    """The full pipeline runs without raising."""
    out = run_pipeline(
        test_case_1,
        polygon=None,
        can_remove_edges=True,
        n_smooth_iter=10,
        do_post_process=True,
    )
    assert out is not None
    assert out.n_elems > 0


def test_run_pipeline_skip_post_process(test_case_1):
    """Pipeline with do_post_process=False matches raw tri2quad behaviour."""
    raw = tri2quad(test_case_1, can_remove_edges=True)
    out = run_pipeline(
        test_case_1,
        polygon=None,
        can_remove_edges=True,
        do_post_process=False,
    )
    assert out.n_elems == raw.n_elems
