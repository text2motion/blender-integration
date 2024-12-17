from enum import Enum
import math
from .t2m_animation import T2MFrames
import logging
import bpy
import bpy_extras
import mathutils

import text2motion_client_api.api
import text2motion_client_api.api.generate_api
import text2motion_client_api.models
from text2motion_client_api.models.skeleton import Skeleton
from text2motion_client_api.models.bone import Bone


logger = logging.getLogger("text2motion")


def matrix_to_list(matrix: mathutils.Matrix):
    result = [0]*16
    for i in range(4):
        for j in range(4):
            result[i+j*4] = matrix[i][j]
    return result


BLENDER_FORWARD = "Y"
BLENDER_UP = "Z"
T2M_FORWARD = "-Z"
T2M_UP = "Y"
blender_to_t2m_matrix = bpy_extras.io_utils.axis_conversion(from_forward=BLENDER_FORWARD, from_up=BLENDER_UP,
                                                            to_forward=T2M_FORWARD, to_up=T2M_UP).to_4x4()

t2m_to_blender_matrix = bpy_extras.io_utils.axis_conversion(from_forward=T2M_FORWARD, from_up=T2M_UP,
                                                            to_forward=BLENDER_FORWARD, to_up=BLENDER_UP).to_4x4()

cached_target_skeleton = None
cached_active_object = None

class ModelVersion(str, Enum):
    STABLE = 'stable'
    LAB_V_0_1_0 = 'labs (0.1.0)'


def get_target_skeleton(active_object):
    global cached_target_skeleton, cached_active_object
    if active_object.type != 'ARMATURE':
        raise ValueError("Active object is not an armature")

    if active_object != cached_active_object:
        cached_target_skeleton = None

    if not cached_target_skeleton:
        logger.debug("Loading target skeleton")
    else:
        logger.debug("Using cached target skeleton")
        return cached_target_skeleton

    my_armature = bpy.data.armatures[active_object.data.name]
    root_armature_bone = my_armature.bones[0]

    stack = []
    t2m_root_bone = None
    stack.append((root_armature_bone, None))

    while len(stack) > 0:
        current_armature_bone, parent = stack.pop()

        current_bone_name = current_armature_bone.name.replace(
            "mixamorig:", "mixamorig")

        current_pose_bone = active_object.pose.bones[current_armature_bone.name]

        # set bone to reset pose before fetching the matrix
        current_pose_bone.matrix_basis.identity()

        if current_armature_bone.parent:
            converted_m = current_armature_bone.parent.matrix_local.inverted_safe(
            ) @ current_armature_bone.matrix_local
        else:
            converted_m = blender_to_t2m_matrix @ current_armature_bone.matrix_local

        matrix = matrix_to_list(converted_m)

        t2m_bone = Bone(
            name=current_bone_name,
            matrix=matrix,
            children=[],
        )

        if parent:
            parent.children.append(t2m_bone)
        else:
            t2m_root_bone = t2m_bone

        for child in current_armature_bone.children:
            stack.append((child, t2m_bone))

    world_matrix = matrix_to_list(mathutils.Matrix.Identity(4))

    result = Skeleton(
        root=t2m_root_bone,
        world_matrix=world_matrix,
    )
    cached_active_object = active_object
    cached_target_skeleton = result
    return result


def load_frames(
        frames_str: str,
        action_name: str = "T2MGeneratedAction",
        apply_root_motion: bool = True):
    active_object = bpy.context.active_object
    active_object.animation_data_create()
    active_object.animation_data.action = bpy.data.actions.new(
        name=action_name)
    bpy.ops.object.mode_set(mode='POSE')

    frames: T2MFrames = T2MFrames.model_validate_json(frames_str)
    scene = bpy.context.scene
    scene.frame_start = 0
    scene.frame_end = int(
        math.ceil(frames.duration * bpy.context.scene.render.fps))

    for bone_name, track in frames.bones.items():
        bone_name = bone_name.replace("mixamorig", "mixamorig:")

        if bone_name not in active_object.pose.bones:
            logger.warning(f"Bone {bone_name} not found in armature")
            continue

        current_bone = active_object.pose.bones[bone_name]
        current_armature_bone = active_object.data.bones[bone_name]

        if not apply_root_motion:
            # Assuming only root bone has both position and rotation transformation.
            if len(track.position.items()) > 0 and len(track.rotation.items()) > 0:
                logger.debug(
                    f"Skipping frames for root bone {bone_name} as root motion is disabled")
                continue

        for frame_timestamp_str, quaternion_list in track.rotation.items():
            frame = float(
                frame_timestamp_str) * bpy.context.scene.render.fps

            # server side is (x, y, z, w), blender is (w, x, y, z)
            q = mathutils.Quaternion(
                [
                    quaternion_list[3],
                    quaternion_list[0],
                    quaternion_list[1],
                    quaternion_list[2]
                ])
            m = q.normalized().to_matrix().to_4x4()

            # put the bone in t-pose
            current_bone.matrix_basis.identity()

            if current_armature_bone.parent:
                converted_m = current_armature_bone.matrix_local.inverted_safe(
                ) @ current_armature_bone.parent.matrix_local @ m
            else:
                converted_m = m

            current_bone.rotation_quaternion = converted_m.to_quaternion()
            current_bone.keyframe_insert(
                data_path='rotation_quaternion', frame=frame)

        for frame_timestamp_str, vector3 in track.position.items():
            frame = float(
                frame_timestamp_str) * bpy.context.scene.render.fps
            current_bone.location[0] = vector3[0]
            current_bone.location[1] = vector3[1]
            current_bone.location[2] = vector3[2]

            current_bone.keyframe_insert(
                data_path='location', frame=frame)


def make_server_request(
        prompt: str, 
        target_skeleton: Skeleton, 
        seconds: int,
        api_key: str,
        model_version: ModelVersion = ModelVersion.STABLE
        ):
    logger.info(f"Requesting Text2Motion Server with prompt: {prompt}")
    configuration = text2motion_client_api.Configuration(
        host="https://api.text2motion.ai"
    )
    configuration.api_key['APIKeyHeader'] = api_key

    with text2motion_client_api.ApiClient(configuration) as api_client:
        api_instance = text2motion_client_api.GenerateApi(api_client)
        generate_request_body = text2motion_client_api.GenerateRequestBody(
            prompt=prompt,
            target_skeleton=target_skeleton,
            seconds=seconds,
        )

        match model_version:
            case ModelVersion.LAB_V_0_1_0:
                api_response = api_instance.generate_api_labs010_generate_post(
                    generate_request_body)
            case _:
                api_response = api_instance.generate_api_generate_post(
                    generate_request_body)
        return api_response.result
