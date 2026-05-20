"""Pytest fixtures. Load test .14 meshes from `03_CHILMesh_Test_Cases/01_.14_Files`."""

from __future__ import annotations

from pathlib import Path

import pytest

from chilmesh import CHILmesh


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "03_CHILMesh_Test_Cases" / "01_.14_Files"


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
