"""Shared fixtures for the phantom test suite.

`nema_wagi` builds its geometry as top-level module code (it doubles as a
`#%%` cell script), so the ~30-60 s cost is paid on *import*, not on calling
`compartments()`. These fixtures are session-scoped so that import happens
exactly once no matter how many test modules need the body phantom.
"""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(scope="session")
def wagi():
    import nema_wagi
    return nema_wagi


@pytest.fixture(scope="session")
def scatter():
    import nema_scatter
    return nema_scatter


@pytest.fixture(scope="session")
def placement_mod():
    import placement
    return placement


@pytest.fixture(scope="session")
def wagi_compartments(wagi):
    return wagi.compartments()


@pytest.fixture(scope="session")
def scatter_compartments(scatter):
    return scatter.compartments()
