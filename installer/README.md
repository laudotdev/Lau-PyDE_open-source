# Lau-PyDE Linux installer

Choose one of these installation options:

- **Full application using the Linux `.sh` installer** (Arch and other Linux distributions): follow [Generic Linux installation](#generic-linux-installation). This installs Lau-PyDE for your user under `~/.local`.
- **Native Arch package** (Arch Linux only): follow [Arch Linux](#arch-linux). This builds and installs the system package with `pacman`.

## Generic Linux installation

This installs the full application for your user. It is an alternative to pipx and does not replace the native Arch package instructions below.

1. Install Git and Python 3.10 or newer with `venv` support. Install the packages using your distribution's package manager. For example:

	- Arch Linux: `sudo pacman -S --needed git python`
	- Ubuntu/Debian: `sudo apt update && sudo apt install git python3 python3-venv`
	- Fedora: `sudo dnf install git python3`

2. Clone the repository and enter its directory:

	```sh
	git clone https://github.com/laudotdev/Lau-PyDE_open-source.git
	cd Lau-PyDE_open-source
	```

3. Run the installer from the repository root:

	```sh
	./installer/linux/install.sh
	```

The installer creates a virtual environment and installs Lau-PyDE under `~/.local/share/lau-pyde`. It creates the `lau-pyde` command in `~/.local/bin`, installs a desktop entry, and registers the bundled app icon. Ensure `~/.local/bin` is on your `PATH`, then launch the app with:

```sh
lau-pyde
```

To uninstall this user-local installation, run `./installer/linux/uninstall.sh` from the cloned repository.

## Arch Linux

Install the Arch build tools and package dependencies first:

```bash
sudo pacman -S --needed base-devel fakeroot debugedit python pyside6
```

Then build and install a native package:

```sh
./installer/arch/build-arch-package.sh
sudo pacman -U installer/arch/lau-pyde-1.2.0-1-any.pkg.tar.zst
```

The Arch package uses the system `python` and `pyside6` packages and installs the application under `/usr/share/lau-pyde`.
