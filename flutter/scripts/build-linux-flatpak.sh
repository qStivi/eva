#!/usr/bin/env bash
# Build Eva as a universal Linux desktop Flatpak.
#
# The host is atomic (no build toolchain), so the Flutter Linux release bundle is
# compiled inside the `eva-build` distrobox (ubuntu:24.04 with GTK3/clang/cmake/
# ninja/git). The bundle is then packaged against the GNOME runtime with
# flatpak-builder, installed for the user, and exported as a portable .flatpak.
#
# One-time prep:
#   distrobox create --name eva-build --image ubuntu:24.04 --yes
#   distrobox enter eva-build -- sudo apt-get install -y clang cmake ninja-build \
#       pkg-config libgtk-3-dev liblzma-dev git
#   flatpak install flathub org.flatpak.Builder org.gnome.Platform//47 org.gnome.Sdk//47
set -euo pipefail
FLUTTER_DIR="$(cd "$(dirname "$0")/.." && pwd)"   # flutter/

echo "==> Compiling Flutter Linux release bundle (distrobox eva-build)…"
distrobox enter eva-build -- bash -lc \
  "export PATH=\$HOME/flutter/bin:\$PATH; cd '$FLUTTER_DIR' && flutter build linux --release"

echo "==> Building + installing the Flatpak…"
cd "$FLUTTER_DIR/packaging/flatpak"
flatpak run org.flatpak.Builder --force-clean --user --install --repo=repo \
  builddir io.github.qstivi.Eva.yaml

echo "==> Exporting portable bundle to ~/Eva-0.1.0-x86_64.flatpak…"
flatpak build-bundle repo "$HOME/Eva-0.1.0-x86_64.flatpak" io.github.qstivi.Eva

echo "Done. Launch with:  flatpak run io.github.qstivi.Eva"
