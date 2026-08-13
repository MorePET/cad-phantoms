# Headless build environment for the phantom models.
#
# The repo is otherwise driven from VS Code + the OCP CAD Viewer, which makes
# the models unrunnable from a pipeline: exporting geometry for a simulation
# had to be done by hand. This image builds and exports them with no viewer and
# no display, so `export_parts()` and the tests can run anywhere.
#
#   podman build -t cad-phantoms:main -f Containerfile .
#   podman run --rm -v "$PWD":/work -w /work cad-phantoms:main -m pytest -q
#   podman run --rm -v "$PWD":/work -w /work cad-phantoms:main export_phantoms.py --out build/
FROM python:3.12-slim

# OCCT needs the GL/X11 shared objects present even when nothing is displayed.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git libgl1 libglu1-mesa libxrender1 libxext6 libsm6 \
    && rm -rf /var/lib/apt/lists/*

# py-mat's distribution name is `py-materials` (the import name is `pymat`), so
# it cannot be requested as `pymat @ git+...` — pip rejects the mismatch even
# though uv accepts it. Pinned to a commit so the image is reproducible;
# pyproject.toml asks for `rev = "latest"`, which an image must not.
ARG PYMAT_REV=a948f9ab313ff36a65c88740a7df581e8de855ed
RUN pip install --no-cache-dir \
        "build123d>=0.7.0" \
        "numpy>=2.4.0" \
        "pytest>=8.0" \
        "git+https://github.com/MorePET/py-mat.git@${PYMAT_REV}"

WORKDIR /work
ENTRYPOINT ["python3"]
