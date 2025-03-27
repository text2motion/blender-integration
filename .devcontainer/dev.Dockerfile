FROM nvidia/cuda:12.2.2-devel-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG BLENDER_MAJOR_VERISON=4.2
ARG BLENDER_VERSION=${BLENDER_MAJOR_VERISON}.3

# nvidia docker runtime env
ENV NVIDIA_VISIBLE_DEVICES \
        ${NVIDIA_VISIBLE_DEVICES:-all}
ENV NVIDIA_DRIVER_CAPABILITIES \
        ${NVIDIA_DRIVER_CAPABILITIES:+$NVIDIA_DRIVER_CAPABILITIES,}graphics,compat32,utility

RUN apt-get update &&\
    apt-get install -y \
    build-essential gdb \
    gettext \
    wget \
    software-properties-common \
    git git-lfs python3-pip

RUN wget https://mirrors.ocf.berkeley.edu/blender/release/Blender${BLENDER_MAJOR_VERISON}/blender-${BLENDER_VERSION}-linux-x64.tar.xz  \
        && tar -xvf blender-${BLENDER_VERSION}-linux-x64.tar.xz --strip-components=1 -C /bin \
        && rm -rf blender-${BLENDER_VERSION}-linux-x64.tar.xz \
        && rm -rf blender-${BLENDER_VERSION}-linux-x64

RUN apt-get install -y libxrender1 libxxf86vm1 libxfixes3 libxi6 libxkbcommon0 libsm6 libgl1 libglvnd0 libgl1-mesa-glx libgl1-mesa-dri

WORKDIR /tmp
COPY requirements.txt /tmp/requirements.txt
RUN /usr/bin/4.2/python/bin/python3.11 -m pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Needed for blender extension verification
RUN /usr/bin/4.2/python/bin/python3.11 -m pip install --no-cache-dir \
    ruff