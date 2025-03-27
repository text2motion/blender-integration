#!/bin/bash
set -e

force_wheel_update=false

if [ -z "$PACKAGE_VERSION" ]; then
    echo "PACKAGE_VERSION is required in the environment."
    exit 1
fi

# Function to display script usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo " -h, --help      Display this help message"
    echo " -f, --force     Force update wheels directory even if it exists"
}

has_argument() {
    [[ ("$1" == *=* && -n ${1#*=}) || (! -z "$2" && "$2" != -*) ]]
}

extract_argument() {
    echo "${2:-${1#*=}}"
}

# Function to handle options and arguments
handle_options() {
    while [ $# -gt 0 ]; do
        case $1 in
        -h | --help)
            usage
            exit 0
            ;;
        -f | --force)
            force_wheel_update=true
            ;;
        *)
            echo "Invalid option: $1" >&2
            usage
            exit 1
            ;;
        esac
        shift
    done
}

update_wheel() {
    rm -rf wheels
    mkdir wheels
    pip download -r ../../requirements.txt --dest ./wheels --only-binary=:all: --python-version=3.11
    pip download -r ../../requirements.txt --dest ./wheels --only-binary=:all: --python-version=3.11 --platform=win_amd64 --exists-action=i
}

# Main script execution
handle_options "$@"

cd addons/text2motion

should_update_wheel=true
if [ "$force_wheel_update" = false ]; then
    if [ -d "wheels" ]; then
        should_update_wheel=false
    fi
fi

if [ "$should_update_wheel" = true ]; then
    echo "Updating wheels..."
    update_wheel
else
    echo "Wheels directory already exists. Skipping wheel update."
fi

readarray -d '' wheel_files < <(find ./wheels/* -print0)
exclude_list=("urllib3")
result="["
for i in "${wheel_files[@]}"; do
    skip=false
    for exclude in "${exclude_list[@]}"; do
        if [[ "$i" == *"$exclude"* ]]; then
            skip=true
            break
        fi
    done

    if [ "$skip" = false ]; then
        result+="\"$i\", "
    fi
done
result+="]"
export PACKAGE_WHEELS=$result

cd ../..

echo "Generating addons/text2motion/blender_manifest.toml..."
envsubst <blender_manifest.toml.template >addons/text2motion/blender_manifest.toml
