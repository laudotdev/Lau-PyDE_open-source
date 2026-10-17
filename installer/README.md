# Lau-PyDE Linux installer

## Generic Linux installation

From the repository root:

```sh
./installer/linux/install.sh
```

This installs Lau-PyDE into `~/.local/share/lau-pyde`, creates the `lau-pyde` command, installs the desktop entry, and registers the bundled logo as the application icon. It creates a Python virtual environment and installs dependencies there.

Uninstall with `./installer/linux/uninstall.sh`.

## Arch Linux

Build and install a native package:

```sh
./installer/arch/build-arch-package.sh
sudo pacman -U installer/arch/lau-pyde-1.1.0-1-any.pkg.tar.zst
```

The Arch package uses the system `python` and `python-pyside6` packages and installs the application under `/usr/share/lau-pyde`.
