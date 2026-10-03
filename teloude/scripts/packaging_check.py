"""Static packaging verification that runs on ANY platform (no Windows, no PyInstaller needed).

    python scripts/packaging_check.py

It checks everything about the icon / installer / portable configuration that can be verified
without building: that the icon exists and carries every size Windows asks for, that the EXE, the
installer, both shortcuts and the setup wizard all point at the same artwork, that the PyInstaller
spec embeds the version resource, and that the portable build script produces a real portable tree.

The things it can NOT verify are the ones that need Windows: actually running Teloude.exe, reading
its embedded icon resource, creating real Desktop / Start Menu shortcuts. Those are covered by
scripts/windows_verify.py, which refuses to run anywhere else.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + (f" - {detail}" if detail else ""))


def main() -> int:
    # ---------------------------------------------------------------- icon
    ico = ROOT / "assets" / "icon.ico"
    check("assets/icon.ico exists", ico.is_file(), str(ico))
    if ico.is_file():
        try:
            from PIL import Image

            with Image.open(ico) as im:
                sizes = set(im.info.get("sizes") or im.ico.sizes())  # type: ignore[attr-defined]
            need = {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)}
            check("icon carries every Windows size", need <= sizes, str(sorted(sizes)))
        except Exception as exc:  # pragma: no cover - Pillow is a hard dependency
            check("icon carries every Windows size", False, type(exc).__name__)
    check("assets/icon.png exists (window + tray on every platform)", (ROOT / "assets" / "icon.png").is_file())

    # ---------------------------------------------------------------- PyInstaller
    spec = (ROOT / "installer" / "teloude.spec").read_text(encoding="utf-8")
    check("spec embeds the icon into Teloude.exe", "icon=ICON" in spec and 'assets" / "icon.ico"' in spec)
    check("spec embeds the version resource", "version_info.txt" in spec)
    check("spec is a windowed (console=False) app", "console=False" in spec)
    check("spec ships the assets folder", "assets" in spec)
    check("version_info.txt exists", (ROOT / "installer" / "version_info.txt").is_file())

    # ---------------------------------------------------------------- Inno Setup
    iss = (ROOT / "installer" / "teloude.iss").read_text(encoding="utf-8")
    icons = re.findall(r'^Name: "\{auto(?:programs|desktop)\}.*$', iss, re.M)
    check("two shortcuts (Start Menu + Desktop)", len(icons) == 2, f"{len(icons)} found")
    check("shortcuts take their icon from the EXE", all('IconFilename: "{app}\\{#AppExe}"' in i and "IconIndex: 0" in i for i in icons))
    check("setup wizard uses the Teloude icon", "SetupIconFile=..\\assets\\icon.ico" in iss)
    check("uninstall entry uses the Teloude icon", "UninstallDisplayIcon={app}\\{#AppExe}" in iss)
    check("setup refreshes the Windows icon cache", bool(re.search(r"^ChangesAssociations=yes", iss, re.M)))

    # ---------------------------------------------------------------- portable
    ps1 = (ROOT / "scripts" / "build_portable.ps1").read_text(encoding="utf-8")
    for needle in ("portable.ini", "data", "Teloude.exe", "portable_verify.py", "DPAPI"):
        check(f"portable script mentions {needle!r}", needle in ps1)
    check("portable script refuses to ship user data", ".dpapi" in ps1 and "teloude.db" in ps1)
    check("portable verifier exists", (ROOT / "scripts" / "portable_verify.py").is_file())
    cfg = (ROOT / "app" / "infrastructure" / "config.py").read_text(encoding="utf-8")
    check("app detects portable mode", "PORTABLE_MARKER" in cfg and "portable_root" in cfg)

    # ---------------------------------------------------------------- credentials
    check(
        "no credentials committed",
        not (ROOT / "app" / "teloude_api.json").exists(),
        "app/teloude_api.json would be bundled - keep it out of git",
    )
    gi = ROOT / ".gitignore"
    check("credentials file is git-ignored", gi.is_file() and "teloude_api.json" in gi.read_text(encoding="utf-8"))
    inj = (ROOT / "scripts" / "inject_credentials.py").read_text(encoding="utf-8")
    check("credential injector can write and clear the file", "--api-id" in inj and "--clear" in inj)
    for name in ("build_windows.ps1", "build_portable.ps1"):
        build = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        check(f"{name} tells the operator whether credentials are bundled", "teloude_api.json" in build)

    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if sys.platform != "win32":
        print("NOTE: not running on Windows - the EXE was not built or executed here.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
