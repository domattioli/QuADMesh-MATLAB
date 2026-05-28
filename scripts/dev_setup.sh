#!/usr/bin/env bash
# dev_setup.sh — provision the QuADMESH pytest validation gate in a fresh container.
#
# The routine's QuADMESH validation gate is `pytest tests/`, but a fresh
# container ships without numpy/scipy/chilmesh/pytest, and `chilmesh` is NOT on
# PyPI (private research repo) so it cannot be resolved from the index — it must
# be editable-installed from the sibling CHILmesh checkout. This script does
# that idempotently. See issue #48.
#
# USAGE:
#   bash scripts/dev_setup.sh        # provision (idempotent)
#   . .venv/bin/activate && pytest tests/
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
venv="$repo_root/.venv"

# Locate the sibling CHILmesh checkout (editable dep — not on PyPI).
chilmesh_dir=""
for cand in "$repo_root/../CHILmesh" "$HOME/CHILmesh"; do
  if [ -f "$cand/pyproject.toml" ] || [ -f "$cand/setup.py" ]; then
    chilmesh_dir="$(cd "$cand" && pwd)"
    break
  fi
done
if [ -z "$chilmesh_dir" ]; then
  echo "ERROR: CHILmesh checkout not found (looked in ../CHILmesh and \$HOME/CHILmesh)." >&2
  echo "       chilmesh is not on PyPI; clone it next to this repo:" >&2
  echo "         git clone https://github.com/domattioli/CHILmesh.git ../CHILmesh" >&2
  exit 1
fi

if [ ! -d "$venv" ]; then
  echo "Creating venv at $venv"
  python3 -m venv "$venv"
fi
# shellcheck disable=SC1091
. "$venv/bin/activate"

python -m pip install --quiet --upgrade pip
echo "Installing chilmesh (editable) from $chilmesh_dir"
pip install --quiet -e "$chilmesh_dir"
echo "Installing quadmesh[dev] (editable)"
pip install --quiet -e "$repo_root/.[dev]"

echo "dev_setup OK | chilmesh=$chilmesh_dir | venv=$venv"
echo "Next: . .venv/bin/activate && pytest tests/"
