"""Unit tests for rtctools_highs.__init__ import-time behaviour."""
import importlib.util
import os
import re
import sys
from pathlib import Path

import casadi
import pytest

_INIT_SRC = Path(__file__).resolve().parent.parent / "src" / "rtctools_highs" / "__init__.py"

# Platform-specific suffix used by the binary check in __init__.py
_PLUGIN_SUFFIX = {"win32": ".dll", "linux": ".so"}.get(sys.platform, ".so")
_PLUGIN_BINARY = f"libcasadi_conic_highs{_PLUGIN_SUFFIX}"


@pytest.fixture(autouse=True)
def restore_casadi_path():
    """Restore CasADi's global plugin search path after each test."""
    original = casadi.GlobalOptions.getCasadiPath()
    yield
    casadi.GlobalOptions.setCasadiPath(original)


def _load_from(directory):
    """Execute rtctools_highs __init__.py from the given directory as a fresh module."""
    sys.modules.pop("rtctools_highs", None)
    spec = importlib.util.spec_from_file_location("rtctools_highs", directory / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules["rtctools_highs"] = module  # keep _dll_dir handle alive on Windows
    return module


def _write_init(directory):
    (directory / "__init__.py").write_text(
        _INIT_SRC.read_text(encoding="utf-8"), encoding="utf-8"
    )


class TestMissingBinary:
    def test_raises_import_error_when_no_binary(self, tmp_path):
        """ImportError with a build hint when libcasadi_conic_highs* is absent."""
        _write_init(tmp_path)
        with pytest.raises(ImportError, match="compiled plugin binary was not found"):
            _load_from(tmp_path)

    def test_error_message_contains_path(self, tmp_path):
        """ImportError message includes the directory that was searched."""
        _write_init(tmp_path)
        with pytest.raises(ImportError, match=re.escape(str(tmp_path))):
            _load_from(tmp_path)


class TestBinaryPresent:
    def test_no_error_when_binary_exists(self, tmp_path):
        """No ImportError when a matching plugin file is present."""
        (tmp_path / _PLUGIN_BINARY).touch()
        _write_init(tmp_path)
        _load_from(tmp_path)  # must not raise

    def test_plugin_dir_added_to_casadi_path(self, tmp_path):
        """Plugin directory is prepended to CasADi's search path after import."""
        (tmp_path / _PLUGIN_BINARY).touch()
        _write_init(tmp_path)
        _load_from(tmp_path)

        path_parts = [p for p in casadi.GlobalOptions.getCasadiPath().split(os.pathsep) if p]
        assert str(tmp_path) in path_parts

    def test_plugin_dir_not_duplicated(self, tmp_path):
        """Importing twice does not add the plugin directory to the path twice."""
        (tmp_path / _PLUGIN_BINARY).touch()
        _write_init(tmp_path)

        _load_from(tmp_path)
        _load_from(tmp_path)

        path_parts = [p for p in casadi.GlobalOptions.getCasadiPath().split(os.pathsep) if p]
        assert path_parts.count(str(tmp_path)) == 1


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only")
class TestMacOS:
    def test_raises_on_macos(self, tmp_path):
        """ImportError is raised on macOS with a clear message."""
        (tmp_path / _PLUGIN_BINARY).touch()
        _write_init(tmp_path)
        with pytest.raises(ImportError, match="does not provide a macOS wheel"):
            _load_from(tmp_path)


class TestVersion:
    def test_version_attribute_present(self, tmp_path):
        """__version__ is exposed and follows semver after a successful import."""
        (tmp_path / _PLUGIN_BINARY).touch()
        _write_init(tmp_path)
        module = _load_from(tmp_path)
        assert hasattr(module, "__version__")
        assert re.match(r"\d+\.\d+\.\d+", module.__version__)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
class TestWindowsPathPrepend:
    def test_libs_dir_prepended_to_path(self, tmp_path, monkeypatch):
        """rtctools_highs.libs/ is prepended to PATH when the directory exists."""
        (tmp_path / _PLUGIN_BINARY).touch()
        libs_dir = tmp_path.parent / "rtctools_highs.libs"
        _write_init(tmp_path)

        monkeypatch.setenv("PATH", os.environ.get("PATH", ""))
        monkeypatch.setattr("os.path.isdir", lambda p: p == str(libs_dir))
        _load_from(tmp_path)

        assert os.environ["PATH"].startswith(str(libs_dir) + os.pathsep)

    def test_path_unchanged_without_libs_dir(self, tmp_path, monkeypatch):
        """libs/ absent — its path must not appear as a PATH entry after import."""
        (tmp_path / _PLUGIN_BINARY).touch()
        libs_dir = str(tmp_path.parent / "rtctools_highs.libs")
        _write_init(tmp_path)

        monkeypatch.setenv("PATH", os.environ.get("PATH", ""))
        monkeypatch.setattr("os.path.isdir", lambda p: False)
        _load_from(tmp_path)

        path_entries = os.environ["PATH"].split(os.pathsep)
        assert libs_dir not in path_entries
