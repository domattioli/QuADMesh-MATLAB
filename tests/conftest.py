"""Pytest fixtures. Load test .14 meshes from `tests/fixtures/meshes`."""

from __future__ import annotations

from pathlib import Path

import pytest

from chilmesh import CHILmesh


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "meshes"


def _load(name: str) -> CHILmesh:
    path = FIXTURE_DIR / name
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")
    return CHILmesh.read_from_fort14(path)


@pytest.fixture(scope="session")
def test_case_1() -> CHILmesh:
    return _load("Test_Case_1.14")


@pytest.fixture(scope="session")
def test_case_2() -> CHILmesh:
    return _load("Test_Case_2.14")


@pytest.fixture(scope="session")
def mixed_test() -> CHILmesh:
    return _load("Mixed_Test.14")


@pytest.fixture(scope="session")
def _block_o() -> CHILmesh:
    """Block_O fixture for parity scaffold (test_parity.py)."""
    return _load("Block_O.14")
