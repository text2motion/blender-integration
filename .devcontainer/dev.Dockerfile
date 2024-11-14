FROM mcr.microsoft.com/vscode/devcontainers/python:3.11

ARG DEBIAN_FRONTEND=noninteractive

# nvidia docker runtime env
ENV NVIDIA_VISIBLE_DEVICES \
        ${NVIDIA_VISIBLE_DEVICES:-all}
ENV NVIDIA_DRIVER_CAPABILITIES \
        ${NVIDIA_DRIVER_CAPABILITIES:+$NVIDIA_DRIVER_CAPABILITIES,}graphics,compat32,utility

RUN apt-get update &&\
        apt-get install -y \
        build-essential gdb \
        software-properties-common \
        git git-lfs python3-pip \
        # blender dependencies
        libxxf86vm-dev \
        libxfixes-dev \
        libxi6 \
        libxkbcommon-x11-0 \
        libsm-dev \
        libgl1-mesa-glx 


ARG BLENDER_MAJOR_VERISON=4.2
ARG BLENDER_VERSION=${BLENDER_MAJOR_VERISON}.3
RUN wget https://mirrors.ocf.berkeley.edu/blender/release/Blender${BLENDER_MAJOR_VERISON}/blender-${BLENDER_VERSION}-linux-x64.tar.xz  \
        && tar -xvf blender-${BLENDER_VERSION}-linux-x64.tar.xz --strip-components=1 -C /bin \
        && rm -rf blender-${BLENDER_VERSION}-linux-x64.tar.xz \
        && rm -rf blender-${BLENDER_VERSION}-linux-x64

WORKDIR /local