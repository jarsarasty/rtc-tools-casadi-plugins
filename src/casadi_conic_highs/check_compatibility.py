#!/usr/bin/env python3
"""
Pre-validate CasADi/HiGHS API compatibility before building the plugin.

Compares the HiGHS C API signatures that highs_interface.cpp actually calls
against the headers bundled in the CasADi wheel and the headers of the
downloaded HiGHS release.  Also diffs highs_interface.cpp between the
bundled CasADi version and the cloned one to catch interface-level changes.

Exit codes:
  0  All called symbols present with matching signatures.
  1  One or more called symbols missing or signature mismatch (build will fail).
  2  highs_interface.cpp differs between CasADi versions (warning only).
"""

import argparse
import difflib
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

_COMMENT_RE = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)
_WS_RE = re.compile(r"\s+")
_CALL_RE = re.compile(r"\bHighs_\w+")
_DECL_RE = re.compile(r"^.+?\b(Highs_\w+)\s*\(")

_OK = "\033[32mPASS\033[0m"
_FAIL = "\033[31mFAIL\033[0m"
_WARN = "\033[33mWARN\033[0m"

_MAX_DIFF_LINES = 80

_RAW_URL = (
    "https://raw.githubusercontent.com/casadi/casadi"
    "/{tag}/casadi/interfaces/highs/highs_interface.cpp"
)


def _strip_comments(text: str) -> str:
    return _COMMENT_RE.sub(" ", text)


def _normalise(sig: str) -> str:
    return _WS_RE.sub(" ", sig).strip().removesuffix(";").strip()


def _parse_declarations(header_text: str) -> dict[str, str]:
    """Return {function_name: normalised_signature} for all Highs_* declarations."""
    text = _strip_comments(header_text)
    decls: dict[str, str] = {}
    buf = ""
    depth = 0
    for line in text.splitlines():
        stripped = line.strip()
        depth += stripped.count("(") - stripped.count(")")
        buf = (buf + " " + stripped).strip()
        if depth <= 0 and ";" in buf:
            for fragment in buf.split(";"):
                fragment = fragment.strip()
                m = _DECL_RE.match(fragment)
                if m:
                    decls[m.group(1)] = _normalise(fragment)
            buf = ""
            depth = 0
    return decls


def _find_header(highs_dir: Path) -> Path:
    candidates = [
        highs_dir / "include" / "highs" / "interfaces" / "highs_c_api.h",
        highs_dir / "include" / "Highs_c_api.h",
        highs_dir / "include" / "highs_c_api.h",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"highs_c_api.h not found under {highs_dir}. Tried:\n"
        + "\n".join(f"  {p}" for p in candidates)
    )


def _bundled_header(casadi_root: Path) -> Path:
    p = casadi_root / "include" / "highs" / "interfaces" / "highs_c_api.h"
    if p.exists():
        return p
    raise FileNotFoundError(f"Bundled HiGHS header not found: {p}")


def _extract_called_symbols(text: str) -> set[str]:
    return set(_CALL_RE.findall(_strip_comments(text)))


def _diff_interface(interface_text: str) -> bool:
    """Print a diff of highs_interface.cpp between the installed CasADi tag and the clone.

    Returns True if a warning was raised (diff exists or fetch failed), False if identical.
    """
    try:
        import casadi  # noqa: PLC0415
        casadi_version = casadi.__version__
    except ImportError:
        print("  [WARN] Could not detect installed CasADi version; skipping interface diff.")
        return True

    bundled_src = _fetch_bundled_interface(casadi_version)
    if bundled_src is None:
        print(
            f"  [{_WARN}] Could not fetch bundled highs_interface.cpp "
            f"(casadi {casadi_version}) from GitHub; skipping diff."
        )
        return True

    if bundled_src == interface_text:
        print(
            f"  [{_OK}] highs_interface.cpp identical between "
            f"casadi {casadi_version} and cloned source."
        )
        return False

    diff_lines = list(
        difflib.unified_diff(
            bundled_src.splitlines(keepends=True),
            interface_text.splitlines(keepends=True),
            fromfile=f"casadi/{casadi_version}/highs_interface.cpp",
            tofile="cloned/highs_interface.cpp",
            n=3,
        )
    )
    diff_text = "".join(diff_lines)
    touches_calls = bool(_CALL_RE.search(diff_text))
    print(
        f"  [{_WARN}] highs_interface.cpp differs"
        + (" — changes touch Highs_* call sites." if touches_calls else ".")
    )
    print(f"\n--- diff ({len(diff_lines)} lines) ---")
    for line in diff_lines[:_MAX_DIFF_LINES]:
        print(line, end="")
    if len(diff_lines) > _MAX_DIFF_LINES:
        print(f"\n  ... ({len(diff_lines) - _MAX_DIFF_LINES} more lines)")
    return True


def _fetch_bundled_interface(version: str) -> str | None:
    for tag in (version, f"v{version}"):
        url = _RAW_URL.format(tag=tag)
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, OSError, UnicodeDecodeError):
            continue
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--casadi-src-dir", required=True, type=Path)
    parser.add_argument("--highs-dir", required=True, type=Path)
    parser.add_argument("--casadi-root", required=True, type=Path)
    args = parser.parse_args()

    interface_cpp = (
        args.casadi_src_dir / "casadi" / "interfaces" / "highs" / "highs_interface.cpp"
    )

    print("=" * 70)
    print("CasADi / HiGHS API compatibility check")
    print("=" * 70)

    if not interface_cpp.exists():
        print(f"[FAIL] highs_interface.cpp not found: {interface_cpp}", file=sys.stderr)
        sys.exit(1)

    interface_text = interface_cpp.read_text(encoding="utf-8")
    called_decls = sorted(_extract_called_symbols(interface_text))
    print(f"\nSymbols called in highs_interface.cpp ({len(called_decls)}):")
    for sym in called_decls:
        print(f"  {sym}")

    try:
        bundled_hdr = _bundled_header(args.casadi_root)
    except FileNotFoundError as exc:
        print(f"\n[FAIL] {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        downloaded_hdr = _find_header(args.highs_dir)
    except FileNotFoundError as exc:
        print(f"\n[FAIL] {exc}", file=sys.stderr)
        sys.exit(1)

    bundled_decls = _parse_declarations(bundled_hdr.read_text(encoding="utf-8"))
    downloaded_decls = _parse_declarations(downloaded_hdr.read_text(encoding="utf-8"))

    print(f"\nBundled header   : {bundled_hdr} ({len(bundled_decls)} declarations)")
    print(f"Downloaded header: {downloaded_hdr} ({len(downloaded_decls)} declarations)")

    print("\nSignature comparison:")
    failures: list[str] = []

    for sym in called_decls:
        if sym not in bundled_decls:
            print(f"  [{_FAIL}] {sym}: missing from bundled CasADi header (sanity error)")
            failures.append(sym)
        elif sym not in downloaded_decls:
            print(f"  [{_FAIL}] {sym}: missing from downloaded HiGHS header")
            failures.append(sym)
        elif bundled_decls[sym] == downloaded_decls[sym]:
            print(f"  [{_OK}] {sym}")
        else:
            print(f"  [{_FAIL}] {sym}: signature mismatch")
            print(f"    bundled   : {bundled_decls[sym]}")
            print(f"    downloaded: {downloaded_decls[sym]}")
            failures.append(sym)

    print("\nhighs_interface.cpp diff (bundled CasADi tag vs cloned):")
    interface_warn = _diff_interface(interface_text)

    print("\n" + "=" * 70)
    if failures:
        print(f"[FAIL] {len(failures)} symbol(s) incompatible — build will fail.")
        print("       Incompatible: " + ", ".join(failures))
        sys.exit(1)

    if interface_warn:
        print("[WARN] All called signatures match, but highs_interface.cpp has changed.")
        print("       The build may succeed but behaviour could differ.")
        sys.exit(2)

    print("[PASS] All called symbols present with matching signatures.")
    sys.exit(0)


if __name__ == "__main__":
    main()
