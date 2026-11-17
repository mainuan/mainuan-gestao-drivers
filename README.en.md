<div align="center">

<img src="usr/share/icons/hicolor/scalable/apps/mainuan-gestao-drivers.svg" width="96" alt="Mainuan Driver Manager icon">

# Mainuan Gestão de Drivers

Detects additional hardware drivers and installs or switches them safely through PackageKit and the Plasma PolicyKit agent.

[![CI](https://github.com/mainuan/mainuan-gestao-drivers/actions/workflows/build-mainuan-deb.yml/badge.svg)](https://github.com/mainuan/mainuan-gestao-drivers/actions/workflows/build-mainuan-deb.yml)
[![Release](https://img.shields.io/github/v/release/mainuan/mainuan-gestao-drivers)](https://github.com/mainuan/mainuan-gestao-drivers/releases/latest)
![Platform](https://img.shields.io/badge/Kubuntu%2026.04%20%7C%20Plasma%206.6-1d99f3)

[Português](README.md) · **English**

</div>

---

## About

The Mainuan hardware tool ("Driver Manager" in English). A Qt 6 Widgets/PyQt6 derivative of the **Linux Mint** Driver Manager (mintdrivers), with no GTK or XApp frontend. Detection uses `ubuntu-drivers-common` and APT; changes go through PackageKit and are authorised by the session PolicyKit agent. The app never asks for a password, never runs APT or dpkg directly and ships no privileged helper.

## Features

- Driver detection that respects Ubuntu recommendations and APT candidates/pinning, third-party repositories included.
- Preview of package changes, applied only after explicit confirmation.
- Read-only preflight for modules, kernel headers, DKMS, Secure Boot and MOK enrolment; unknown or pending states block changes.
- Re-evaluation after each transaction; changes are blocked in the Live session.
- `test` mode with fictitious devices, simulated in memory.
- Local diagnostics that can be copied from the Help menu, with no automatic upload.

Driver switches are not atomic and there is no automatic rollback, autoremove or key enrolment. See [docs/qt-transactions.md](docs/qt-transactions.md).

## Installation

Preinstalled on the Mainuan ISO. To install manually, download `mainuan-gestao-drivers_1.0_all.deb` and `SHA256SUMS` from the [latest release](https://github.com/mainuan/mainuan-gestao-drivers/releases/latest):

```bash
sha256sum --check --ignore-missing SHA256SUMS
sudo apt install ./mainuan-gestao-drivers_1.0_all.deb
```

## Usage

```text
mainuan-gestao-drivers [test] [--debug] [--version] [--help]
```

`test` uses fictitious devices and changes nothing on the system; `--debug` enables detailed logs. Manual page: `man mainuan-gestao-drivers`.

## Technical information

| Item | Value |
|---|---|
| Language | Python 3 |
| Toolkit | Qt 6 Widgets (PyQt6), QtDBus |
| Base | Kubuntu 26.04 LTS, KDE Plasma 6.6 |
| Package | `mainuan-gestao-drivers` (Debian, `all`) |
| Main dependencies | `python3-pyqt6`, `python3-apt`, `ubuntu-drivers-common`, `packagekit` |

## Build and test

```bash
sudo apt-get build-dep --no-install-recommends ./
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
python3 tests/probe_packagekit_readonly.py
dpkg-buildpackage -us -uc -b
```

Full CI sequence: [`.github/workflows/build-mainuan-deb.yml`](.github/workflows/build-mainuan-deb.yml).

## Translations

Complete in 33 languages; 68 more partial catalogs are inherited from Linux Mint. See [docs/i18n/README.md](docs/i18n/README.md).

## Contributing

Use [Issues](https://github.com/mainuan/mainuan-gestao-drivers/issues) and pull requests to `master`.

## Credits

Mainuan: Rafael Ruscher ([@ruscher](https://github.com/ruscher)) and Daigo ([@daigoasuka](https://github.com/daigoasuka)). Upstream: [Linux Mint mintdrivers](https://github.com/linuxmint/mintdrivers) by Clement Lefebvre, with Michael Webster, Frédéric Gaudet and other contributors; Launchpad translators are credited in each catalog.

## License

GPL-2.0-or-later, as stated in [`debian/copyright`](debian/copyright). There is no `LICENSE` file at the repository root.
