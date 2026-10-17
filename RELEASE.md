# Lau-PyDE v1.1.0

## What’s new

Lau-PyDE v1.1.0 adds a safer, more informative update experience and improves distribution support across Linux and Windows.

### Update notifications

- Lau-PyDE now checks GitHub Releases in the background when the application starts.
- Manual checking remains available from Help → Update Lau-PyDE.
- Checks use semantic version comparison instead of alphabetical text comparison.
- Legacy release tags such as `Lau-PyDE_v1.0`, `Lau-PyDE_v1.0.0`, `v1.0`, and `v1.0.0` are recognized.
- Draft and prerelease versions are ignored.
- Network failures do not interrupt the editor or produce repeated startup dialogs.
- Updates are never downloaded, installed, or executed automatically.

### Download guidance

- Windows releases can use the Windows installer asset when one is published.
- Arch Linux releases can use the `.pkg.tar.zst` asset when one is published.
- Other Linux distributions are directed to the verified downloads page.
- If a platform asset is unavailable, Lau-PyDE safely falls back to the downloads page.

### Linux packaging

- Installer files are organized under `installer/arch/` and `installer/linux/`.
- Arch Linux packaging continues to use the native `makepkg` workflow.
- Generic Linux installation continues to use a user-level virtual environment.
- Existing settings and project files are preserved during installation updates.

### Windows installer preparation

- Added a PyInstaller specification for the standalone application.
- Added an Inno Setup configuration for `Lau-PyDE-Setup-v1.1.0.exe`.
- Added the `lau-pyde_logo.ico` application and installer icon.
- Added license text, Start Menu and optional desktop shortcuts, and a launch-after-install option.
- The installer does not automatically pin Lau-PyDE to the taskbar.

## Notes

The `v1.1.0` GitHub release and Windows installer must be published and verified separately. The existing stable GitHub release remains unchanged.
