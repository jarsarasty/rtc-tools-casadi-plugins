"""End-to-end test for the rtctools_highs plugin.

Verifies that the HiGHS solver, loaded via the plugin, produces numerically
correct solutions for a small mixed-integer LP and a QP.  These problems are
small enough to be solved analytically so the expected answers are exact.
"""
import casadi as ca


class TestLinearProgram:
    """min  -x - 2y  s.t.  x + y <= 4,  x <= 3,  y <= 3,  x,y >= 0
    Optimal: x=1, y=3, f=-7"""

    def test_lp(self):
        x = ca.MX.sym("x")
        y = ca.MX.sym("y")
        xy = ca.vertcat(x, y)
        g = ca.vertcat(x + y, x, y)
        qp = {"x": xy, "f": -x - 2 * y, "g": g}
        solver = ca.qpsol("lp", "highs", qp)
        sol = solver(lbx=0, ubx=ca.inf, lbg=[-ca.inf, -ca.inf, -ca.inf], ubg=[4, 3, 3])
        assert abs(float(sol["x"][0]) - 1.0) < 1e-6
        assert abs(float(sol["x"][1]) - 3.0) < 1e-6
        assert abs(float(sol["f"]) - (-7.0)) < 1e-6


class TestQuadraticProgram:
    """min  (x-1)^2 + (y-2)^2  s.t.  x + y <= 3,  x,y >= 0
    Unconstrained optimum (1,2) is feasible (1+2=3), so optimal = (1,2), f=0"""

    def test_qp(self):
        x = ca.MX.sym("x")
        y = ca.MX.sym("y")
        xy = ca.vertcat(x, y)
        qp = {"x": xy, "f": (x - 1) ** 2 + (y - 2) ** 2, "g": x + y}
        solver = ca.qpsol("qp", "highs", qp)
        sol = solver(lbx=0, ubx=ca.inf, lbg=-ca.inf, ubg=3)
        assert abs(float(sol["x"][0]) - 1.0) < 1e-5
        assert abs(float(sol["x"][1]) - 2.0) < 1e-5
        assert abs(float(sol["f"])) < 1e-9


class TestMixedIntegerLP:
    """min  -x - y  s.t.  x + y <= 3.5,  x,y in {0,1,2,...}
    Optimal: x+y=3, f=-3"""

    def test_milp(self):
        x = ca.MX.sym("x")
        y = ca.MX.sym("y")
        xy = ca.vertcat(x, y)
        qp = {"x": xy, "f": -x - y, "g": x + y}
        solver = ca.qpsol(
            "milp",
            "highs",
            qp,
            {"discrete": [True, True]},
        )
        sol = solver(lbx=0, ubx=10, lbg=-ca.inf, ubg=3.5)
        total = float(sol["x"][0]) + float(sol["x"][1])
        assert abs(total - 3.0) < 1e-6, f"Expected integer sum=3, got {total}"
        assert abs(float(sol["f"]) - (-3.0)) < 1e-6
