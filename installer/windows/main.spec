from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

project_root = Path(SPECPATH).resolve().parents[1]

assets = collect_data_files("assets", include_py_files=False)
qt_libs = collect_dynamic_libs("PySide6")

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=qt_libs,
    datas=assets,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Lau-PyDE",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(project_root / "installer" / "windows" / "lau-pyde_logo.ico"),
)
