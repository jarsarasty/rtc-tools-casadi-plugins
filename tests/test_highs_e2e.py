"""
Standalone runner for the HiGHS plugin end-to-end test.

Sets RTCTOOLS_EXTRA_CASADIPATH to the built plugin directory, then solves a
small QP using the custom libcasadi_conic_highs plugin.

Usage:
    uv run python run_highs_plugin_e2e.py
"""

import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent
PLUGIN_LIB_DIR = REPO_ROOT / "ci-work" / "plugin-install-highs1.14.0-casadi3.7.2" / "lib"

if sys.platform == "win32":
    # CasADi's plugin loader uses SetDllDirectory+LoadLibrary, which searches
    # the directory co-located with the plugin DLL for transitive dependencies.
    # libhighs.dll is already in PLUGIN_LIB_DIR alongside the plugin, so no
    # explicit pre-loading is needed here (unlike the pumped_hydro runner which
    # uses a separately-built libhighs.dll requiring zlib1.dll from MSYS2).
    os.add_dll_directory(str(PLUGIN_LIB_DIR))

os.environ["RTCTOOLS_EXTRA_CASADIPATH"] = str(PLUGIN_LIB_DIR)

# Add repo root so relative imports inside test modules resolve.
sys.path.insert(0, str(REPO_ROOT))

import numpy as np

import rtctools.util as rtctools_util
from tests.optimization.test_solvers import ModelHiGHS_alg

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("rtctools")

rtctools_util._configure_extra_casadi_path(logger)

problem = ModelHiGHS_alg()
problem.optimize()
results = problem.extract_results()

y = results["y"]
u = results["u"]
print(f"\ny      = {y}")
print(f"u      = {u}")
print(f"y + u  = {y + u}  (should be all 1.0)")

assert np.allclose(y + u, np.ones(len(problem.times())), atol=1e-6), "Constraint y+u=1 violated"
print("\nPASS: HiGHS plugin solved the QP correctly.")
