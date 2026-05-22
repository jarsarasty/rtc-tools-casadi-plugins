"""Smoke test: verify that importing rtctools_highs registers the HiGHS plugin
and that CasADi can solve a trivial LP through it."""
import casadi as ca
import pytest


def test_import_registers_plugin():
    path = ca.GlobalOptions.getCasadiPath()
    assert "rtctools_highs" in path.replace("\\", "/"), (
        f"rtctools_highs directory not found in CasADi plugin path: {path}"
    )


def test_highs_solves_trivial_lp():
    # min  x  s.t.  x >= 1
    x = ca.MX.sym("x")
    qp = {"x": x, "f": x, "g": x}
    solver = ca.qpsol("solver", "highs", qp)
    sol = solver(lbg=1.0, ubg=ca.inf)
    assert abs(float(sol["x"]) - 1.0) < 1e-6, f"Expected x=1, got x={float(sol['x'])}"
    assert abs(float(sol["f"]) - 1.0) < 1e-6, f"Expected f=1, got f={float(sol['f'])}"
