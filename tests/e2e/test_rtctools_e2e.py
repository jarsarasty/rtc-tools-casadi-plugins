"""End-to-end test: pumped hydropower example via rtc-tools + rtctools_highs.

Requires rtc-tools and the pumped_hydropower_system example directory.
The example is looked up in the following order:
  1. RTCTOOLS_EXAMPLE_DIR environment variable
  2. examples/pumped_hydropower_system/ relative to the repo root
  3. Skipped if neither is found.
"""
import logging
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("rtctools", reason="rtc-tools not installed")
import rtctools_highs  # noqa: E402 — registers the HiGHS plugin with CasADi


def _find_example_dir() -> Path | None:
    if env := os.environ.get("RTCTOOLS_EXAMPLE_DIR"):
        return Path(env)
    repo_root = Path(__file__).resolve().parents[2]
    candidate = repo_root / "examples" / "pumped_hydropower_system"
    if candidate.exists():
        return candidate
    return None


EXAMPLE_DIR = _find_example_dir()
pytestmark = pytest.mark.skipif(
    EXAMPLE_DIR is None,
    reason="pumped_hydropower_system example directory not found; set RTCTOOLS_EXAMPLE_DIR",
)


class TestPumpedHydropowerE2E:
    """Full stack: rtctools_highs → CasADi → HiGHS → rtc-tools goal programming."""

    def test_solves_optimally(self):
        """All goal-programming priorities must converge to Optimal."""
        from rtctools.util import run_optimization_problem

        sys.path.insert(0, str(EXAMPLE_DIR / "src"))
        try:
            from example import PumpStorage
        finally:
            sys.path.pop(0)

        log_records = []

        class _Capture(logging.Handler):
            def emit(self, record):
                log_records.append(record.getMessage())

        handler = _Capture()
        rtctools_logger = logging.getLogger("rtctools")
        rtctools_logger.addHandler(handler)
        try:
            run_optimization_problem(PumpStorage, base_folder=str(EXAMPLE_DIR))
        finally:
            rtctools_logger.removeHandler(handler)

        solver_lines = [m for m in log_records if "Solver succeeded" in m]
        assert solver_lines, "No 'Solver succeeded' lines found in rtc-tools log"
        for line in solver_lines:
            assert "Optimal" in line, f"Non-optimal solver status: {line}"
