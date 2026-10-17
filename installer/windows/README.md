# Windows installer preparation

The repository does not currently contain a PyInstaller spec or an Inno Setup script. The Windows installer should be prepared on Windows without changing the update checker into an automatic installer.

## Build prerequisites

Install Python 3.10 or newer, Git, PyInstaller, and Inno Setup on Windows. From the repository root, install the project dependencies and create a standalone build with the project entry point:

```powershell
py -m pip install -e .
py -m pip install pyinstaller
pyinstaller installer/windows/main.spec
```

Then compile `installer/windows/Lau-PyDE.iss` with Inno Setup Compiler (`ISCC.exe`). The expected output is:

```text
dist\installer\Lau-PyDE-Setup-v1.1.0.exe
```

The final Inno Setup script should consume the generated application files and produce:

```text
Lau-PyDE-Setup-v1.1.0.exe
```

The output name is a release convention only until an actual Windows build verifies it.

## Installer behavior to configure

The included Inno Setup script is configured to:

- show the project license text supplied by the repository once a license file is added;
- offer a Start Menu shortcut and an optional desktop shortcut;
- offer a launch-after-install checkbox;
- use the normal Windows uninstall entry;
- use `lau-pyde_logo.ico` for the installer, executable, shortcuts, and taskbar identity;
- preserve Lau-PyDE settings and project files when upgrading or uninstalling;
- install the application under a standard per-machine or per-user location selected by the installer configuration;
- not attempt to pin the application to the taskbar automatically, because Windows does not provide a stable supported installer action for that behavior.

## Validation required on Windows

Build and test the installer on Windows before publishing it:

1. Build the PyInstaller application.
2. Compile the Inno Setup script.
3. Install into a clean test account.
4. Confirm the application reports version `1.1.0`.
5. Confirm resources, icons, shortcuts, launch-after-install, uninstall, settings, and project files.
6. Confirm an upgrade does not erase user data.
7. Test the unsigned installer on a clean Windows machine.

This Arch environment has not built or runtime-tested a Windows installer. SmartScreen warnings are expected for an unsigned application; code signing is a future release improvement and is not part of this change.
