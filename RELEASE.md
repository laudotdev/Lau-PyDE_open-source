# Lau-PyDE v1.1.0 release notes

Status: prepared, not yet published.

## Highlights

- Added background GitHub Releases update checking.
- Added semantic version handling for standard and legacy Lau-PyDE release tags.
- Added platform-aware download routing with a safe website fallback.
- Organized Linux installer files under `installer/arch/` and `installer/linux/`.
- Prepared the Windows PyInstaller and Inno Setup workflow.
- Added the `lau-pyde_logo.ico` Windows application and installer icon.

## Windows build

Run on Windows from the repository root:

```powershell
py -m pip install -e .
py -m pip install pyinstaller
pyinstaller installer/windows/main.spec
iscc installer/windows/Lau-PyDE.iss
```

Expected output:

```text
dist\installer\Lau-PyDE-Setup-v1.1.0.exe
```

The installer must be tested on Windows before publishing. This repository checkout has not produced or runtime-tested the Windows executable.

## Linux validation

```sh
python3 -m pytest -q
python3 -m compileall -q core ui main.py launcher.py
./installer/arch/build-arch-package.sh
./installer/linux/install.sh
```

The Arch package requires an Arch Linux environment with `makepkg`. The generic Linux installer is user-level and should be tested without unnecessary root privileges.

## Publishing checklist

- Confirm all tests pass.
- Build and test the Windows installer on Windows.
- Build and inspect the Arch package on Arch Linux.
- Test the generic Linux installer.
- Publish the stable GitHub release with tag `v1.1.0`.
- Upload only verified release assets.
- Verify the updater against the published release after publication.
- Update the website download links separately and verify deployment.
