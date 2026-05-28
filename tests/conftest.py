import pytest

# Module-level importorskip (not inside a fixture) so that:
#   1. The plugin is registered with CasADi before any test module is collected.
#   2. The Linux ctypes force-load (in __init__.py) primes the linker cache
#      before casadi is imported anywhere else in the test suite.
# A fixture with autouse=True runs *after* collection, which is too late.
pytest.importorskip("rtctools_highs")
