#!/bin/bash
set -e

./prepare_extension.sh --force

rm -rf build/
mkdir build/
blender --command extension build --source-dir ./src/text2motion --output-dir ./build
