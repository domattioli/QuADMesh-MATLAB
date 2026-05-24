"""CLI smoke test. Verify the `quadmesh` entry point reads + writes fort.14."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from chilmesh import CHILmesh

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "meshes"


def test_cli_runs(tmp_path):
    """End-to-end CLI: read .14, run pipeline, write .14, reload."""
    input_path = FIXTURE_DIR / "Test_Case_1.14"
    if not input_path.exists():
        pytest.skip(f"fixture missing: {input_path}")
    output_path = tmp_path / "out.14"

    result = subprocess.run(
        [sys.executable, "-m", "quadmesh.cli", str(input_path),
         "-o", str(output_path), "--n-smooth-iter", "0"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert output_path.exists()
    # Re-load to verify it's a valid fort.14.
    reloaded = CHILmesh.read_from_fort14(output_path)
    assert reloaded.n_elems > 0
