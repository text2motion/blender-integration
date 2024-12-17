#!/bin/bash
set -e

# Get the path of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
pushd ${SCRIPT_DIR}
./prepare_extension.sh --force

rm -rf build/
mkdir build/
blender --command extension build --source-dir ./addons/text2motion --output-dir ./build
popd