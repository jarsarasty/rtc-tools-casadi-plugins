"""
rtctools_highs — CasADi HiGHS solver plugin for rtc-tools.

Registers the bundled libcasadi_conic_highs binary with CasADi on import.
Not intended for use on macOS (the CasADi bundled HiGHS is used there instead).
"""
import sys

if sys.platform == "darwin":
    raise ImportError(
        "rtctools_highs does not provide a macOS wheel; "
        "the CasADi bundled HiGHS will be used instead."
    )

# TODO: implement path registration via setCasadiPath() for CasADi 3.7.x,
# and via CASADI_PLUGIN_SEARCH_PATH for CasADi 3.8+ (see delivery plan).
