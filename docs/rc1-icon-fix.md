# RC1: Qt icon initialization in the isolated CI environment

Date: 2026-10-22. Base: `7748122306199b735feb6e92d623d3c7bd881f0f`,
branch `port/kubuntu-26.04`. Version remains `1.0~rc1`, architecture `all`.

## Cause and reproduction

The original expression used the theme icon with a bundled SVG fallback. The
minimal CI dependencies omitted `qt6-svg-plugins`. Without that package and
without a theme providing this application's icon, neither source was usable.
This was a missing runtime dependency, not a QSettings identity or offscreen
platform problem. Device artwork also uses SVG and needs these plugins.

The official linux/amd64 image was fetched from Docker Hub, with its manifest
and both layer digests checked before extraction:

`ubuntu:26.04@sha256:42527649dbc4f9197a6073f426f488cbff0e9cc9f2afce32d91c383e4875634a`

Bubblewrap user namespaces ran this rootfs without installing anything on the
host. APT variants were explicitly cleared before dependencies were fetched,
with only the `amd64` index enabled. Tests ran as UID 1000, offscreen, without a
desktop session or access to the host system bus. The baseline source was
extracted with `git archive HEAD`, not modified to reproduce the failure.

Before adding the SVG package, the rootfs reported:

```text
ICON_PATH: /baseline/usr/share/icons/hicolor/scalable/apps/mainuan-gestao-drivers.svg
SVG: exists=True, readable=True, mode=0664, isNull=True, pixmap.isNull=True
PNG: exists=True, readable=True, mode=0664, isNull=False, pixmap.isNull=False
formats: bmp cur gif ico jfif jpeg jpg pbm pgm png ppm xbm xpm
old QIcon.fromTheme expression: isNull=True
```

The paths are derived from the Python module location, not from the developer's
home. The PNG is `usr/share/icons/hicolor/48x48/apps/mainuan-gestao-drivers.png`.
Qt's plugin path was `/usr/lib/x86_64-linux-gnu/qt6/plugins`; it contained no SVG
plugin. A fresh-process host experiment with only the offscreen platform plugin
available reproduced the same SVG failure and successful PNG rendering.

| Source / environment | Result |
| --- | --- |
| Original commit, pinned rootfs without SVG plugins | 357 tests; exactly 1 failure, original windowIcon assertion |
| Original commit, same rootfs after adding SVG plugins | 357 tests passed |
| Corrected source, rootfs without SVG plugins | All 9 original identity tests passed using the PNG fallback |
| Corrected source, rootfs with SVG plugins | 361 tests passed, no skips or failures |
| Corrected source, developer host | 361 tests passed, no skips or failures |

The added distribution packages were `qt6-svg-plugins` and its dependency
`libqt6svg6`, both `6.10.2-2`. No other runtime change was needed for the
before/after SVG comparison. In particular, the original failing assertion
was not removed, edited, skipped, or mocked out.

## Fix

- Declare `qt6-svg-plugins` in Debian Depends and explicitly install it in CI.
- Prefer a renderable theme icon, then the bundled SVG, then the existing
  official PNG. No generic artwork, fixed user paths, theme or palette changes.
- Derive both resource paths from the package location, supporting checkout
  execution and extracted/installed packages alike.
- Add four real-Qt subprocess tests: SVG rendering, PNG without SVG engines,
  theme precedence, and complete application startup without SVG engines.
- Require the SVG dependency in the package gate and require a nonnull,
  renderable window icon in the extracted-package CPU startup probe.

The container digest, APT variant policy, unprivileged test/build steps,
commit-named artifact upload, application ID and public launcher are unchanged.
No driver, PackageKit, Live Session, DKMS, Secure Boot or MOK rules changed.

Files changed:

- `usr/lib/mainuan/mainuan-gestao-drivers/mainuan_drivers/__init__.py`
- `usr/lib/mainuan/mainuan-gestao-drivers/mainuan_drivers/qt/application.py`
- `debian/control`
- `.github/workflows/build-mainuan-deb.yml`
- `.github/scripts/qt_startup_probe.py`
- `tests/inspect_deb.py`
- `tests/test_qt_only_packaging.py`
- `tests/test_application_icon.py` (new)
- `docs/rc1-icon-fix.md` (new)

## Validation and limits

- `python3 -m unittest discover -s tests -v`: 361 passed on the host and pinned
  rootfs. The original 357 tests are all retained.
- `python3 -m compileall -q usr tests`: passed on the host.
- `python3 tests/probe_packagekit_readonly.py`: host system bus introspection,
  CreateTransaction, Resolve, signals and Finished succeeded; no GI imports.
- `dpkg-buildpackage -us -uc -b`: passed on the host, as a normal user.
- Package metadata/content gate, `dpkg-deb -I/-c`, desktop validation and
  `lintian --fail-on error,warning`: passed. No ELF, legacy GTK, bytecode,
  manual probe or test code is shipped. SVG and PNG remain packaged.
- Extracted-package startup: normal entry with fixture I/O and `test` entry
  both passed, with a renderable window icon and no driver mutation.
- QEMU startup passed in the pinned rootfs, both without and with SVG plugins,
  using the existing CPU mask excluding v2/v3/v4 features. The loader CPUID
  checks passed; no `CPU ISA level is lower than required` error occurred.
  Native host startup was also checked, but is not baseline CPU evidence.
- The normal offscreen `propagateSizeHints()` warning remains nonfatal.

This is not a rerun of the remote GitHub job. Rootless preparation cannot fully
configure packages requiring ownership by other system users: the local
inventory still records pending configuration for dbus, debhelper,
libpam-systemd, lintian, packagekit and polkitd. The rootfs environment inventory
is explicitly `--report-only`, NOT a strict environment-gate pass; CI retains
the strict gate without this flag. All native architectures/variants in that
inventory are baseline amd64/all. Runtime Qt/SVG packages were configured.
Debian build, lint and the real PackageKit probe were therefore validated on
the host, not claimed as a complete rootfs workflow execution. The rootfs tests
and QEMU client startup above did execute successfully as UID 1000.

QEMU user-mode startup is not a full ISO, real legacy CPU, Plasma/Wayland or
PackageKit daemon CPU-compatibility test. Those remain manual integration checks.
No host packages were installed/removed, and no driver mutation was executed.

The validated package is
`/home/daigo/Github/mainuan-gestao-drivers_1.0~rc1_all.deb`.
SHA-256:
`7c4967eb3dd6a9ed43c4edba021d9036984acbc11879879628700d079336524e`.

Generated local evidence is under ignored `dist/icon-*.json` and the icon-fix
logs. The artifact checksum can be rechecked with `sha256sum --check SHA256SUMS`
in `dist/`. No commit, push, tag or release was performed.
