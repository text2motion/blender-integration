#!/bin/bash
set -e

if [ -z "$PACKAGE_VERSION" ]; then
    echo "PACKAGE_VERSION is required in the environment."
    exit 1
fi

docker build -t blender-devcontainer .devcontainer/ -f .devcontainer/dev.Dockerfile
docker run --rm \
    --user $(id -u):$(id -g) \
    -v "${PWD}:/local" \
    -e PACKAGE_VERSION=$PACKAGE_VERSION \
    blender-devcontainer \
    /bin/bash build_extension.sh
