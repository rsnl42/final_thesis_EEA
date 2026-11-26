"""
Root conftest.py — adds the scripts/ directory to sys.path so that
tests can import scripts modules directly (e.g. `from make_synthetic_giga import ...`).
"""
import sys
from pathlib import Path

# Allow bare imports like `from make_synthetic_giga import ...`
# (the scripts live in scripts/, not the repo root)
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
