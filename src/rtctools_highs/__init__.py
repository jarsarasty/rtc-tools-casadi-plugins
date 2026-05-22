"""
rtctools_highs - CasADi HiGHS solver plugin for rtc-tools.

**Import side-effect**: importing this module mutates CasADi's global plugin
search path (via ``casadi.GlobalOptions.setCasadiPath``) to prepend the
directory containing the bundled ``libcasadi_conic_highs`` binary. This is
intentional -- it is what makes the HiGHS solver available to CasADi without
any manual configuration. rtc-tools triggers this automatically at its entry
points via ``try: import rtctools_highs; except ImportError: pass``.

**Windows DLL isolation**: the wheel is processed by ``delvewheel`` at build
time, which renames transitive dependencies (e.g. ``libhighs.dll`` becomes
``libhighs-<hash>.dll``) and patches the plugin's import table accordingly.
This eliminates naming conflicts with the ``libhighs.dll`` bundled inside
CasADi. ``os.add_dll_directory`` is called so that Windows can locate the
renamed dependencies when CasADi's plugin loader opens the plugin DLL.
The handle must stay alive for the directory registration to remain active.

Note: ``os.add_dll_directory`` is only effective for loaders that use
``LoadLibraryEx`` with ``LOAD_LIBRARY_SEARCH_USER_DIRS``. CasADi 3.7.x uses
the legacy ``LoadLibrary`` path, so the renamed deps are found via the
``_rtctools_highs_libs`` subdirectory that ``delvewheel`` adds to PATH at
import time rather than via the DLL directory registration.

Not intended for use on macOS (the CasADi bundled HiGHS is used there instead).
"""
import os
import sys
from pathlib import Path

__version__ = "1.14.0"

if sys.platform == "darwin":
    raise ImportError(
        "rtctools_highs does not provide a macOS wheel; "
        "the CasADi bundled HiGHS will be used instead."
    )

_plugin_dir = Path(__file__).parent

_suffix = {"win32": ".dll", "linux": ".so"}.get(sys.platform, ".so")
if not any(_plugin_dir.glob(f"libcasadi_conic_highs*{_suffix}")):
    raise ImportError(
        f"rtctools_highs is installed but the compiled plugin binary was not found in "
        f"{_plugin_dir}. The package may have been installed from source without building "
        f"the plugin. Install a binary wheel instead."
    )

if sys.platform == "win32":
    # delvewheel injects a _rtctools_highs_libs/ loader shim at the top of this
    # file at repair time; the shim adds the libs directory to PATH so that
    # CasADi's legacy LoadLibrary() call finds the renamed transitive deps.
    # os.add_dll_directory is also registered as a belt-and-suspenders measure
    # for any future CasADi version that adopts LoadLibraryEx.
    _dll_dir = os.add_dll_directory(str(_plugin_dir))  # handle must stay alive

import casadi  # noqa: E402

_current_parts = [p for p in casadi.GlobalOptions.getCasadiPath().split(os.pathsep) if p]
_plugin_dir_str = str(_plugin_dir)
if os.path.normcase(os.path.normpath(_plugin_dir_str)) not in {
    os.path.normcase(os.path.normpath(p)) for p in _current_parts
}:
    casadi.GlobalOptions.setCasadiPath(
        os.pathsep.join([_plugin_dir_str] + _current_parts)
    )
