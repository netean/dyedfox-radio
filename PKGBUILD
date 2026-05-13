# Maintainer: Yaroslav Krytsun <slavko7 at gmail dot com>
pkgname=dyedfox-radio
pkgver=0.1.0
pkgrel=1
pkgdesc="Desktop internet radio player"
arch=('any')
license=('GPL-3.0-or-later')
depends=(
    'python'
    'python-pyqt6'
    'python-requests'
    'python-dbus'
    'python-gobject'
    'gstreamer'
    'gst-plugins-base'
    'gst-plugins-good'
)
optdepends=(
    'gst-plugins-bad: additional codec support'
    'gst-libav: AAC and other codec support'
)
source=()
sha256sums=()

package() {
    install -dm755 "$pkgdir/usr/lib/$pkgname"
    cp -r "$startdir"/api \
          "$startdir"/data \
          "$startdir"/player \
          "$startdir"/tray \
          "$startdir"/ui \
          "$startdir"/assets \
          "$startdir"/main.py \
          "$pkgdir/usr/lib/$pkgname/"
    find "$pkgdir/usr/lib/$pkgname" -type d -name __pycache__ -exec rm -rf {} +

    install -Dm644 "$startdir/assets/icons/$pkgname.png" \
        "$pkgdir/usr/share/icons/hicolor/256x256/apps/$pkgname.png"
    install -Dm644 "$startdir/assets/icons/$pkgname-tray.svg" \
        "$pkgdir/usr/share/icons/hicolor/scalable/apps/$pkgname-tray.svg"
    install -Dm644 "$startdir/assets/icons/$pkgname.svg" \
        "$pkgdir/usr/share/icons/hicolor/scalable/apps/$pkgname.svg"

    install -Dm644 "$startdir/$pkgname.desktop" \
        "$pkgdir/usr/share/applications/$pkgname.desktop"

    install -dm755 "$pkgdir/usr/bin"
    cat > "$pkgdir/usr/bin/$pkgname" << 'LAUNCHER'
#!/bin/sh
exec python3 /usr/lib/dyedfox-radio/main.py "$@"
LAUNCHER
    chmod 755 "$pkgdir/usr/bin/$pkgname"
}
