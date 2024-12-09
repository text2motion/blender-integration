# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import textwrap
from .t2m_server_request_wrapper import get_target_skeleton, load_frames, make_server_request
import logging
import bpy
import webbrowser
from bpy.props import (StringProperty, BoolProperty,
                       PointerProperty, IntProperty, EnumProperty)
from text2motion_client_api.exceptions import ApiException
from http import HTTPStatus

bl_info = {
    "name": "Text2Motion",
    "author": "support@text2motion.ai",
    "description": "",
    "blender": (2, 80, 0),
    "version": (0, 0, 1),
    "location": "",
    "warning": "",
    "category": "Generic",
}


logger = logging.getLogger("text2motion")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    logger.addHandler(logging.StreamHandler())


def _label_multiline(context, text, parent):
    # https://b3d.interplanety.org/en/multiline-text-in-blender-interface-panels/
    chars = int(context.region.width / 7)   # 7 pix on 1 character
    wrapper = textwrap.TextWrapper(width=chars)
    text_lines = wrapper.wrap(text=text)
    for text_line in text_lines:
        parent.label(text=text_line)

# ------------------------------------------------------------------------
#    Scene Properties
# ------------------------------------------------------------------------

MAX_DURATION_SECONDS = 30
current_duration_unit_selector = 'seconds'
current_duration = 5

class T2MSceneProperties(bpy.types.PropertyGroup):
    def set_frame(self, context):
        fps = bpy.context.scene.render.fps
        MAX_FRAMES = MAX_DURATION_SECONDS * fps
        if self.frames > MAX_FRAMES:
            self.frames = MAX_FRAMES
        elif self.frames < fps:
            self.frames = fps
        elif self.frames % fps != 0:
            # this allow the widget to snap to the nearest fps increment
            remainder = self.frames % fps
            if remainder < round(fps / 2):
                self.frames = self.frames - remainder + fps
            else:
                self.frames = self.frames - remainder

    def change_duration_unit(self, context):
        global current_duration_unit_selector, current_duration
        if current_duration_unit_selector != self.duration_unit:
            prev_duration_unit_selector = current_duration_unit_selector
            current_duration_unit_selector = self.duration_unit
            current_duration = self.get(prev_duration_unit_selector, 5)
            if prev_duration_unit_selector == 'seconds':
                self.frames = current_duration * bpy.context.scene.render.fps
            else:
                self.seconds = round(current_duration / bpy.context.scene.render.fps)

    prompt: StringProperty(
        name="Prompt",
        description="Text prompt for the animation to generate.",
        default="Walk around the room",
        maxlen=2048,
    )
    api_key: StringProperty(
        name="Api Key",
        description="API key used for making request to Text2Motion API server.",
        subtype='PASSWORD',
    )
    action_name: StringProperty(
        name="Name",
        description="Name of the generated action",
        default="T2MGeneratedAction",
        maxlen=63,
    )
    is_root_motion_enabled: BoolProperty(
        name="Apply Root Motion",
        description="Apply root motion for the generated animation",
        default=True,
    )
    duration_unit: EnumProperty(
        name="",
        description="Duration unit selector",
        items=[('seconds', "Seconds", ""),
               ('frames', "Frames",
                "Rounded to the nearest FPS increment"),
               ],
        update=change_duration_unit,
    )
    is_auto_duration: BoolProperty(
        name="Auto",
        description="Decide duration automatically",
        default=True,
    )
    seconds: IntProperty(
        name="",
        description="The duration of the animation in seconds",
        default=5,
        min=1,
        max=MAX_DURATION_SECONDS,
    )
    frames: IntProperty(
        name="",
        description="The duration of the animation in number of frames.\nRounded to the nearest FPS increment",
        default=120,
        min=1,
        update=set_frame,
    )


# ------------------------------------------------------------------------
#    Preferences
# ------------------------------------------------------------------------


class T2MPreferences(bpy.types.AddonPreferences):
    # this must match the add-on name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __name__

    api_key: StringProperty(
        name="API Key",
        description="API key used for making request to Text2Motion API server.",
        subtype='PASSWORD',
    )

    def draw(self, context):
        layout = self.layout
        layout.operator("text2motion.open_developer_portal", icon="LINKED")
        layout.prop(self, "api_key")

# ------------------------------------------------------------------------
#    Operators
# ------------------------------------------------------------------------


class T2MSaveApiKeyOperator(bpy.types.Operator):
    """Save API Key to Preferences"""
    bl_idname = "text2motion.save_api_key"
    bl_label = "Save API Key"

    def execute(self, context):
        api_key = context.scene.t2m_scene_properties.api_key
        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        addon_prefs.api_key = api_key
        return {'FINISHED'}


class T2MOpenDeveloperPortalOperator(bpy.types.Operator):
    """Open Text2Motion Developer Portal in browser"""
    bl_idname = "text2motion.open_developer_portal"
    bl_label = "Open Developer Portal"

    def execute(self, context):
        if not bpy.app.online_access:
            self.report(
                {"ERROR"}, "Cannot open developer portal without internet access permission")
            return {'CANCELLED'}
        
        webbrowser.open('https://developer.text2motion.ai/get-started')
        return {'FINISHED'}


class T2MOpenLicenseLinkOperator(bpy.types.Operator):
    """Open License Link"""
    bl_idname = "text2motion.open_license"
    bl_label = "CC-by-4.0 License"

    def execute(self, context):
        if not bpy.app.online_access:
            self.report(
                {"ERROR"}, "Cannot open license link without internet access permission")
            return {'CANCELLED'}
        
        webbrowser.open('https://creativecommons.org/licenses/by/4.0/')
        return {'FINISHED'}


class T2MServerRequestOperator(bpy.types.Operator):
    """Make generate request to Text2Motion Server"""
    bl_idname = "text2motion.generate"
    bl_label = "Generate Animation"

    def execute(self, context):
        active_object = bpy.context.active_object
        if active_object.type != 'ARMATURE':
            error_message = "Active object is not an armature, cannot generate animation"
            logger.warning(error_message)
            self.report({"WARNING"}, error_message)
            return {'CANCELLED'}

        target_skeleton = get_target_skeleton(active_object)

        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        prompt = context.scene.t2m_scene_properties.prompt
        logger.debug(f"Prompt: {prompt}")

        if not context.scene.t2m_scene_properties.is_auto_duration:
            if context.scene.t2m_scene_properties.duration_unit == 'seconds':
                seconds = context.scene.t2m_scene_properties.seconds
            else:
                seconds = round(context.scene.t2m_scene_properties.frames / bpy.context.scene.render.fps)
        else:
            seconds = 0

        response = None
        try:
            if not bpy.app.online_access:
                self.report(
                    {"ERROR"}, "Cannot make server request without internet access permission")
                return {'CANCELLED'}
            
            response = make_server_request(
                prompt, 
                target_skeleton, 
                seconds, 
                addon_prefs.api_key)
        except ApiException as e:
            logger.error(
                f"Failed to generate request for prompt: {prompt} \n"
                f"HTTPStatus: {e.status} \n"
                f"Reason: {e.reason} \n"
                f"Body: {e.body}")

            match e.status:
                case (HTTPStatus.BAD_REQUEST |
                      HTTPStatus.NOT_FOUND |
                      HTTPStatus.METHOD_NOT_ALLOWED |
                      HTTPStatus.CONFLICT |
                      HTTPStatus.UNPROCESSABLE_ENTITY |
                      HTTPStatus.UNSUPPORTED_MEDIA_TYPE
                      ):
                    logging.error(
                        "Text2Motion request failed due to issue on the client.")

                    error_message = ("Failed to generate request due to client error. \n"
                                     f'prompt: "{prompt}" \n'
                                     f'reason: "{e.reason}" \n'
                                     "Please contact support@text2motion.ai for help.")

                    self.report(
                        {"ERROR"}, error_message)
                case HTTPStatus.UPGRADE_REQUIRED:
                    logging.error(
                        "Text2Motion request failed due to outdated package.")
                    error_message = 'Add-on update required. Please download the latest add-ons zip from Github and reinstall it.'
                    self.report(
                        {"ERROR"}, error_message)
                case HTTPStatus.UNAUTHORIZED | HTTPStatus.FORBIDDEN:
                    logging.error(
                        "Text2Motion request failed due to auth issue.")
                    error_message = 'Invalid API Key. Please go to "Edit > Preferences > Add-ons > Text2Motion" and reconfigure your API key.'
                    self.report(
                        {"ERROR"}, error_message)
                case HTTPStatus.TOO_MANY_REQUESTS:
                    logging.error(
                        "Text2Motion request failed due to throttling.")
                    error_message = "Request Throttled. Please wait for some time and try again later."
                    self.report(
                        {"ERROR"}, error_message)
                case HTTPStatus.INTERNAL_SERVER_ERROR | HTTPStatus.BAD_GATEWAY | HTTPStatus.GATEWAY_TIMEOUT:
                    logging.error(
                        "Text2Motion request failed due to server issue.")
                    error_message = "Server has encountered an error. Please try again later."
                    self.report(
                        {"ERROR"}, error_message)
                case HTTPStatus.SERVICE_UNAVAILABLE:
                    logging.error(
                        f"Text2Motion server maintenance in progress. Message: {e.body}")
                    error_message = "Text2Motion server maintenance in progress. Please try again later."
                    self.report(
                        {"ERROR"}, error_message)
                case _:
                    logging.error(
                        "Text2Motion request failed due to unknown issue.")
                    error_message = "Text2Motion request failed due to unknown issue."
                    self.report(
                        {"ERROR"}, error_message)

        except Exception as e:
            logger.error(
                "Exception when calling GenerateApi->generate_api_generate_post: %s\n" % e)
            self.report(
                {"ERROR"}, f"Failed to make Text2Motion request for prompt: {prompt}")

        if not response:
            return {'CANCELLED'}

        load_frames(frames_str=response,
                    action_name=context.scene.t2m_scene_properties.action_name,
                    apply_root_motion=context.scene.t2m_scene_properties.is_root_motion_enabled)
        return {'FINISHED'}


# ------------------------------------------------------------------------
#    Panels
# ------------------------------------------------------------------------


class T2MPanelBase:
    """ Display panel in 3D view"""
    bl_category = "Animation"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'HEADER_LAYOUT_EXPAND'}


class OBJECT_PT_T2MAllowInternetAccessPanel(T2MPanelBase, bpy.types.Panel):
    bl_idname = "OBJECT_PT_T2MAllowInternetAccessPanel"
    bl_label = "Text2Motion"

    @ classmethod
    def poll(self, context):
        # only show panel if internet access is not allowed
        return not bpy.app.online_access

    def draw(self, context):
        layout = self.layout
        _label_multiline(
            context, "Allow Online Access must be enabled to use this extension. "
            "Enable it in Edit > Preferences > System > Network > Allow Online Access", layout)

class OBJECT_PT_T2MConfigureApiKeyPanel(T2MPanelBase, bpy.types.Panel):
    bl_idname = "OBJECT_PT_T2MConfigureApiKeyPanel"
    bl_label = "Text2Motion"

    @ classmethod
    def poll(self, context):
        # only show panel if API key is not set
        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        return not addon_prefs.api_key and bpy.app.online_access

    def draw(self, context):
        layout = self.layout
        layout.label(
            text="Configure API Key",
            icon="INFO")
        col = layout.column(align=True)
        col.operator("text2motion.open_developer_portal", icon="LINKED")
        col.separator()
        col.prop(context.scene.t2m_scene_properties, "api_key")
        col.operator("text2motion.save_api_key", icon="KEYINGSET")


class OBJECT_PT_T2MPanel(T2MPanelBase, bpy.types.Panel):
    bl_idname = "OBJECT_PT_T2MPanel"
    bl_label = "Text2Motion"

    @ classmethod
    def poll(self, context):
        # only show panel if API key is set
        preferences = context.preferences
        addon_prefs = preferences.addons[__package__].preferences
        return addon_prefs.api_key and bpy.app.online_access

    def draw(self, context):
        layout = self.layout
        active_object = bpy.context.active_object
        if not active_object or active_object.type != 'ARMATURE':
            layout.label(
                text="Select an armature", icon="ERROR")
            return
        col = layout.column(align=True)
        col.prop(context.scene.t2m_scene_properties, "prompt")
        col.operator("text2motion.generate", icon="RENDER_ANIMATION")


class OBJECT_PT_T2MAdvancedOptionsPanel(T2MPanelBase, bpy.types.Panel):
    bl_parent_id = "OBJECT_PT_T2MPanel"
    bl_label = "Advanced Options"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.prop(context.scene.t2m_scene_properties, "action_name")
        col.prop(context.scene.t2m_scene_properties, "is_root_motion_enabled")


class OBJECT_PT_T2MAnimationDurationOptionsPanel(T2MPanelBase, bpy.types.Panel):
    bl_parent_id = "OBJECT_PT_T2MAdvancedOptionsPanel"
    bl_label = "Animation Duration"

    def draw(self, context):
        global current_duration_unit_selector, current_duration
        layout = self.layout
        col = layout.column(align=True)
        col.prop(context.scene.t2m_scene_properties, "is_auto_duration")

        if not context.scene.t2m_scene_properties.is_auto_duration:
            row = col.row()
            split = row.split(factor=0.6)
            col = split.column()
            col.prop(context.scene.t2m_scene_properties,
                    context.scene.t2m_scene_properties.duration_unit)
            split = split.split()
            col = split.column()
            col.prop(context.scene.t2m_scene_properties, "duration_unit")


class OBJECT_PT_T2MLicenseInfoPanel(T2MPanelBase, bpy.types.Panel):
    bl_parent_id = "OBJECT_PT_T2MPanel"
    bl_label = "License Info"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        _label_multiline(
            context, "All generated animations are licensed under", layout)
        layout.operator("text2motion.open_license", icon="LINKED")

# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------


classes = (
    OBJECT_PT_T2MAllowInternetAccessPanel,
    OBJECT_PT_T2MConfigureApiKeyPanel,
    OBJECT_PT_T2MPanel,
    OBJECT_PT_T2MAdvancedOptionsPanel,
    OBJECT_PT_T2MAnimationDurationOptionsPanel,
    OBJECT_PT_T2MLicenseInfoPanel,
    T2MServerRequestOperator,
    T2MSaveApiKeyOperator,
    T2MOpenDeveloperPortalOperator,
    T2MOpenLicenseLinkOperator,
    T2MSceneProperties,
    T2MPreferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.t2m_scene_properties = PointerProperty(
        type=T2MSceneProperties)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.t2m_scene_properties


if __name__ == "__main__":
    register()
