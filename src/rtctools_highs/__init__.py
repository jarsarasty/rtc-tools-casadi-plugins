"""
rtctools_highs - CasADi HiGHS solver plugin for rtc-tools.

**Import side-effect**: importing this module mutates CasADi's global plugin
search path (via ``casadi.GlobalOptions.setCasadiPath``) to prepend the
directory containing the bundled ``libcasadi_conic_highs`` binary. This is
intentional -- it is what makes the HiGHS solver available to CasADi without
any manual configuration. rtc-tools triggers this automatically at its entry
points via ``try: import rtctools_highs; except ImportError: pass``.

**Windows limitation**: ``os.add_dll_directory`` is called before CasADi is
imported so that ``libhighs.dll`` resolves from the wheel directory rather than
from the CasADi bundled install on PATH. However, if ``libhighs.dll`` is
already resident in the process (e.g. because a HiGHS solve was performed via
the bundled CasADi before this module was imported), Windows will reuse the
cached DLL handle and the fix has no effect. Import ``rtctools_highs`` before
any CasADi solver calls to ensure correct DLL loading.

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
    # On Windows, libcasadi_conic_highs.dll's transitive dependency (libhighs.dll) is
    # resolved via the standard DLL search order (PATH). Without this call, the bundled
    # CasADi libhighs.dll on PATH wins over the one co-located with the plugin -- wrong
    # version, silent ABI mismatch. os.add_dll_directory() inserts the plugin dir into
    # the DLL search path at the highest priority, fixing transitive dep resolution.
    # Available from Python 3.8+; pyproject.toml enforces requires-python = ">=3.10".
    # Drop this workaround once CasADi 3.8 ships with AddDllDirectory support (#4340).
    _dll_dir = os.add_dll_directory(str(_plugin_dir))  # handle must stay alive

import casadi  # noqa: E402 — must come after os.add_dll_directory on Windows

_current_parts = [p for p in casadi.GlobalOptions.getCasadiPath().split(os.pathsep) if p]
_plugin_dir_str = str(_plugin_dir)
if os.path.normcase(os.path.normpath(_plugin_dir_str)) not in {
    os.path.normcase(os.path.normpath(p)) for p in _current_parts
}:
    casadi.GlobalOptions.setCasadiPath(
        os.pathsep.join([_plugin_dir_str] + _current_parts)
    )
