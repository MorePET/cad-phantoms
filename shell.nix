# NixOS dev shell for cad-phantoms.
#
# build123d ships OCP (OpenCascade python bindings) as a manylinux wheel that
# dynamically links libstdc++, libGL and a handful of X libraries. NixOS has
# no global /usr/lib, so those wheels fail at import with
# `ImportError: libstdc++.so.6: cannot open shared object file` (then libGL,
# then libX11 …) unless the loader is pointed at the nix store.
#
# Usage:
#   nix-shell            # then: uv sync --python $(command -v python3.12)
#   nix-shell --run 'python nema_wagi.py'
#
# uv's own downloaded CPython is a generic-linux dynamic executable and will
# not run here either — hence python312 from nixpkgs and `uv sync --python`.

{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  packages = with pkgs; [
    python312
    uv
  ];

  # Everything the OCP / VTK wheels dlopen at import time.
  LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath (with pkgs; [
    stdenv.cc.cc.lib # libstdc++
    libGL
    libglvnd
    fontconfig
    freetype
    xorg.libX11
    xorg.libXext
    xorg.libSM
    xorg.libICE
    libxrender
    libxi
    zlib
    expat
    libxml2
    xz
    bzip2
    openssl
    glib
  ]);

  shellHook = ''
    echo "cad-phantoms dev shell (NixOS). If .venv is missing:"
    echo "  uv sync --python \$(command -v python3.12)"
  '';
}
