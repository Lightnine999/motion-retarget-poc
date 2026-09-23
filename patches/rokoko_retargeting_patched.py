import bpy
import copy
import time

from ..core import utils
from ..core.retargeting import get_source_armature, get_target_armature
from ..core import detection_manager as detector
from ..core import custom_schemes_manager
from ..panels.retargeting import BoneListItem

RETARGET_ID = '_RSL_RETARGET'


# ─────────────────────────────────────────────────────────────────────────────
# Blender 5.0 API notes (from official breaking changes doc):
#
#   action.fcurves / action.groups / action.id_root  → REMOVED in 5.0
#
#   Correct way to access fcurves (4.4+ / 5.0+):
#     from bpy_extras import anim_utils
#     channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
#     channelbag = anim_utils.action_ensure_channelbag_for_slot(action, slot)
#     fcurves = channelbag.fcurves
#
#   slot comes from:
#     armature.animation_data.action_slot
#
#   bone.select on data.bones → REMOVED in 5.0
#   Use pose_bone.select instead (pose.bones[name].select)
# ─────────────────────────────────────────────────────────────────────────────

def _v():
    return bpy.app.version

def _uses_slot_api():
    return _v() >= (4, 4, 0)

def _legacy_removed():
    return _v() >= (5, 0, 0)


# ── Core action/slot/channelbag helpers ───────────────────────────────────────

def get_action(armature):
    anim = armature.animation_data
    return anim.action if anim else None


def get_slot(armature):
    """Restituisce l'action_slot attivo (Blender 4.4+), None altrimenti."""
    if not _uses_slot_api():
        return None
    anim = armature.animation_data
    if not anim:
        return None
    return getattr(anim, 'action_slot', None)


def get_channelbag(action, slot, ensure=False):
    """
    Restituisce il channelbag per (action, slot).
    Doc ufficiale Blender 5.0:
      anim_utils.action_get_channelbag_for_slot(action, slot)    # leggi
      anim_utils.action_ensure_channelbag_for_slot(action, slot) # crea se non esiste
    """
    if action is None:
        return None
    try:
        from bpy_extras import anim_utils
        if ensure:
            return anim_utils.action_ensure_channelbag_for_slot(action, slot)
        else:
            return anim_utils.action_get_channelbag_for_slot(action, slot)
    except Exception as e:
        print(f"[RSL] get_channelbag error: {e}")
    return None


def get_action_fcurves(action, slot=None):
    """
    Restituisce le fcurves dell'action in modo compatibile con tutte le versioni.

    Blender < 4.4 : action.fcurves
    Blender 4.4+  : anim_utils.action_get_channelbag_for_slot(action, slot).fcurves
    Blender 5.0+  : identico a 4.4+, ma action.fcurves è stato RIMOSSO
    """
    if action is None:
        return []

    if not _uses_slot_api():
        return getattr(action, 'fcurves', [])

    # Blender 4.4+: usa channelbag
    # Se slot non passato, prova tutti gli slot finché ne trova uno con dati
    slots_to_try = []
    if slot is not None:
        slots_to_try = [slot]
    elif hasattr(action, 'slots'):
        slots_to_try = list(action.slots)

    for s in slots_to_try:
        cb = get_channelbag(action, s, ensure=False)
        if cb and hasattr(cb, 'fcurves') and len(cb.fcurves) > 0:
            return cb.fcurves

    # Nessuno slot con dati — se 4.4 (non 5.0) prova ancora l'alias
    if not _legacy_removed() and hasattr(action, 'fcurves'):
        return action.fcurves

    return []


def assign_action(armature, action):
    """
    Assegna action all'armatura con gestione slot per Blender 4.4+.
    """
    anim = armature.animation_data
    if anim is None:
        anim = armature.animation_data_create()

    anim.action = action

    if not _uses_slot_api() or action is None:
        return

    slot = None
    if hasattr(anim, 'action_suitable_slots') and anim.action_suitable_slots:
        slot = anim.action_suitable_slots[0]

    if slot is None and hasattr(action, 'slots'):
        if len(action.slots) > 0:
            slot = action.slots[0]
        else:
            try:
                slot = action.slots.new(for_id=armature)
            except Exception:
                try:
                    slot = action.slots.new('OBJECT', armature.name)
                except Exception as e:
                    print(f"[RSL] assign_action slot error: {e}")

    if slot is not None and hasattr(anim, 'action_slot'):
        try:
            anim.action_slot = slot
        except Exception as e:
            print(f"[RSL] assign_action slot assign error: {e}")


def remove_fcurve(action, slot, fcurve):
    """Rimuove fcurve dal channelbag corretto."""
    if not _uses_slot_api():
        if hasattr(action, 'fcurves'):
            action.fcurves.remove(fcurve)
        return
    cb = get_channelbag(action, slot, ensure=False)
    if cb:
        cb.fcurves.remove(fcurve)


def find_fcurve(action, slot, data_path, index):
    """Trova una fcurve per data_path+index nel channelbag corretto."""
    for fc in get_action_fcurves(action, slot):
        if fc.data_path == data_path and fc.array_index == index:
            return fc
    return None


def new_fcurve(action, slot, data_path, index, group_name=''):
    """
    Crea una nuova fcurve nel channelbag corretto.
    Doc Blender 5.0: il parametro si chiama group_name (non più action_group).
      channelbag.fcurves.new("location", index=2, group_name="Name")
    """
    if not _uses_slot_api():
        if hasattr(action, 'fcurves'):
            return action.fcurves.new(data_path=data_path, index=index, action_group=group_name)
        raise RuntimeError(f"[RSL] Cannot create fcurve: {data_path}[{index}]")

    cb = get_channelbag(action, slot, ensure=True)
    if cb is None:
        raise RuntimeError(f"[RSL] Cannot get channelbag for action '{action.name}'")

    # Blender 5.0: group_name; Blender 4.4: action_group
    try:
        return cb.fcurves.new(data_path=data_path, index=index, group_name=group_name)
    except TypeError:
        return cb.fcurves.new(data_path=data_path, index=index, action_group=group_name)


class BuildBoneList(bpy.types.Operator):
    bl_idname = "rsl.build_bone_list"
    bl_label = "Build Bone List"
    bl_description = "Builds the bone list from the animation and tries to automatically detect and match bones"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        armature_source = get_source_armature()
        armature_target = get_target_armature()

        if not armature_source.animation_data or not get_action(armature_source):
            self.report({'ERROR'}, 'No animation on the source armature found!'
                                   '\nSelect an armature with an animation as source.')
            return {'CANCELLED'}

        if armature_source.name == armature_target.name:
            self.report({'ERROR'}, 'Source and target armature are the same!'
                                   '\nPlease select different armatures.')
            return {'CANCELLED'}

        retargeting_dict = detector.detect_retarget_bones()

        context.scene.rsl_retargeting_bone_list.clear()

        for bone_source, bone_values in retargeting_dict.items():
            bone_target, bone_key = bone_values

            bone_item = context.scene.rsl_retargeting_bone_list.add()
            bone_item.bone_name_key = bone_key
            bone_item.bone_name_source = bone_source
            bone_item.bone_name_target = bone_target

        return {'FINISHED'}


class AddBoneListItem(bpy.types.Operator):
    bl_idname = "rsl.add_bone_list_item"
    bl_label = "Add Bone List Item"
    bl_description = "Adds a customizable bone list item"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        bone_item = context.scene.rsl_retargeting_bone_list.add()
        bone_item.is_custom = True
        context.scene.rsl_retargeting_bone_list_index = len(context.scene.rsl_retargeting_bone_list) - 1
        return {'FINISHED'}


class ClearBoneList(bpy.types.Operator):
    bl_idname = "rsl.clear_bone_list"
    bl_label = "Clear Bone List"
    bl_description = "Clears the bone list so that you can manually fill in all bones"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def execute(self, context):
        for bone_item in context.scene.rsl_retargeting_bone_list:
            bone_item.bone_name_target = ''
        return {'FINISHED'}


class RetargetAnimation(bpy.types.Operator):
    bl_idname = "rsl.retarget_animation"
    bl_label = "Retarget Animation"
    bl_description = "Retargets the animation from the source armature to the target armature"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    retarget_bone_list: [BoneListItem] = []

    def execute(self, context):
        armature_source = get_source_armature()
        armature_target = get_target_armature()

        if not armature_source.animation_data or not get_action(armature_source):
            self.report({'ERROR'}, 'No animation on the source armature found!'
                                   '\nSelect an armature with an animation as source.')
            return {'CANCELLED'}

        if armature_source.name == armature_target.name:
            self.report({'ERROR'}, 'Source and target armature are the same!'
                                   '\nPlease select different armatures.')
            return {'CANCELLED'}

        self.retarget_bone_list = [item for item in context.scene.rsl_retargeting_bone_list
                                   if item.bone_name_source and item.bone_name_target]

        if not self.retarget_bone_list:
            self.report({'ERROR'}, 'No bones are mapped!'
                                   '\nCheck if the bones are mapped correctly or try rebuilding the bone list.')
            return {'CANCELLED'}

        # Check for duplicate target bone entries
        seen = {}
        for item in self.retarget_bone_list:
            seen[item.bone_name_target] = seen.get(item.bone_name_target, 0) + 1
        duplicates = [k for k, v in seen.items() if v > 1]
        if duplicates:
            self.report({'ERROR'}, 'Duplicate target bone entries found! Please use each target bone only once:'
                                   f'\n{", ".join(duplicates)}')
            return {'CANCELLED'}

        custom_schemes_manager.save_retargeting_to_list()

        utils.set_active(armature_target)
        bpy.ops.object.mode_set(mode='OBJECT')
        utils.set_active(armature_source)
        bpy.ops.object.mode_set(mode='OBJECT')

        armature_source.data.pose_position = 'POSE'
        armature_target.data.pose_position = 'POSE'

        pose_source, pose_target = {}, {}
        if bpy.context.scene.rsl_retargeting_use_pose == 'REST':
            pose_source = self.get_and_reset_pose_rotations(armature_source)
            pose_target = self.get_and_reset_pose_rotations(armature_target)

        source_scale = None
        if context.scene.rsl_retargeting_auto_scaling:
            self.clean_animation(armature_source)
            source_scale = copy.deepcopy(armature_source.scale)
            root_bones_for_scale = self.find_root_bones(context, armature_source, armature_target)
            self.scale_armature(context, armature_source, armature_target, root_bones_for_scale)

        armature_source_original = armature_source
        armature_source = self.copy_rest_pose(context, armature_source)

        rotation_mode = armature_target.rotation_mode
        armature_target.rotation_mode = 'QUATERNION'
        rotation = copy.deepcopy(armature_target.rotation_quaternion)
        location = copy.deepcopy(armature_target.location)

        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(armature_target)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        bpy.ops.object.mode_set(mode='EDIT')

        bone_transforms = {}
        for bone in context.object.data.edit_bones:
            bone.select = False
            bone_transforms[bone.name] = (
                armature_source.matrix_world.inverted() @ bone.head.copy(),
                armature_source.matrix_world.inverted() @ bone.tail.copy(),
                utils.mat3_to_vec_roll(armature_source.matrix_world.inverted().to_3x3() @ bone.matrix.to_3x3())
            )

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(armature_source)
        bpy.ops.object.mode_set(mode='EDIT')

        for item in self.retarget_bone_list:
            bone_source = armature_source.data.edit_bones.get(item.bone_name_source)
            bone_new = armature_source.data.edit_bones.new(item.bone_name_target + RETARGET_ID)
            bone_new.head, bone_new.tail, bone_new.roll = bone_transforms[item.bone_name_target]
            bone_new.parent = bone_source

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        root_bones = self.find_root_bones(context, armature_source, armature_target)

        for item in self.retarget_bone_list:
            bone_target = armature_target.pose.bones.get(item.bone_name_target)

            constraint = bone_target.constraints.new('COPY_ROTATION')
            constraint.name += RETARGET_ID
            constraint.target = armature_source
            constraint.subtarget = item.bone_name_target + RETARGET_ID

            if bone_target.name in root_bones:
                constraint = bone_target.constraints.new('COPY_LOCATION')
                constraint.name += RETARGET_ID
                constraint.target = armature_source
                constraint.subtarget = item.bone_name_source

            # In Blender 5 la selezione va fatta tramite pose.bones
            bone_target.select = True  # Blender 5.0: usa PoseBone.select, non Bone.select (rimosso)

        self.bake_animation(armature_source, armature_target, root_bones)

        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(armature_source)
        bpy.data.actions.remove(get_action(armature_source))
        bpy.ops.object.delete()

        armature_source = armature_source_original

        # Rinomina l'action risultante
        action_on_target = get_action(armature_target)
        source_action = get_action(armature_source)
        if action_on_target and source_action:
            action_on_target.name = source_action.name + ' Retarget'

        for bone in armature_target.pose.bones:
            for constraint in bone.constraints:
                if RETARGET_ID in constraint.name:
                    bone.constraints.remove(constraint)

        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(armature_target)

        armature_target.rotation_quaternion = rotation
        armature_target.location = location
        armature_target.rotation_quaternion.w = -armature_target.rotation_quaternion.w
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        armature_target.rotation_quaternion = rotation
        armature_target.rotation_mode = rotation_mode

        if source_scale:
            armature_source.scale = source_scale

        bpy.ops.object.select_all(action='DESELECT')
        self.report({'INFO'}, 'Retargeted animation.')
        return {'FINISHED'}

    def find_root_bones(self, context, armature_source, armature_target):
        root_bones = []
        for bone in armature_target.pose.bones:
            if not bone.parent:
                root_bones.append(bone)

        root_bones_animated = []
        target_bones = [item.bone_name_target for item in self.retarget_bone_list]
        while root_bones:
            for bone in copy.copy(root_bones):
                root_bones.remove(bone)
                if bone.name in target_bones:
                    root_bones_animated.append(bone.name)
                else:
                    for bone_child in bone.children:
                        root_bones.append(bone_child)
        return root_bones_animated

    def clean_animation(self, armature_source):
        """Rimuove le fcurves di trasformazione radice dall'action sorgente."""
        deletable_paths = {'location', 'rotation_euler', 'rotation_quaternion', 'scale'}
        action = get_action(armature_source)
        slot = get_slot(armature_source)
        if not action:
            return
        to_remove = [fc for fc in get_action_fcurves(action, slot) if fc.data_path in deletable_paths]
        for fc in to_remove:
            remove_fcurve(action, slot, fc)

    def get_and_reset_pose_rotations(self, armature):
        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(armature)
        bpy.ops.object.mode_set(mode='POSE')

        pose_rotations = {}
        for bone in armature.pose.bones:
            if bone.rotation_mode == 'QUATERNION':
                pose_rotations[bone.name] = copy.deepcopy(bone.rotation_quaternion)
                bone.rotation_quaternion = (1, 0, 0, 0)
            else:
                pose_rotations[bone.name] = copy.deepcopy(bone.rotation_euler)
                bone.rotation_euler = (0, 0, 0)

        bpy.ops.object.mode_set(mode='OBJECT')
        return pose_rotations

    def load_pose_rotations(self, armature, pose_rotations):
        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(armature)
        bpy.ops.object.mode_set(mode='POSE')

        for bone in armature.pose.bones:
            rotation = pose_rotations.get(bone.name)
            if not rotation:
                continue
            if bone.rotation_mode == 'QUATERNION':
                bone.rotation_quaternion = rotation
            else:
                bone.rotation_euler = rotation

        bpy.ops.object.mode_set(mode='OBJECT')

    def scale_armature(self, context, armature_source, armature_target, root_bones):
        source_height = self.get_armature_height(armature_source, root_bones)
        target_height = self.get_armature_height(armature_target, root_bones)
        if source_height == 0:
            return
        scale_factor = target_height / source_height
        armature_source.scale *= scale_factor
        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(armature_source)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    def get_armature_height(self, armature, root_bones):
        height = 0
        for bone in armature.pose.bones:
            if bone.name not in root_bones:
                continue
            if bone.head.z > height:
                height = bone.head.z
        return height

    def copy_rest_pose(self, context, armature_source):
        bpy.ops.object.select_all(action='DESELECT')
        utils.set_active(armature_source)
        bpy.ops.object.duplicate()
        source_armature_copy = context.object

        action_tmp = get_action(source_armature_copy)
        slot_tmp = get_slot(source_armature_copy)
        if source_armature_copy.animation_data:
            source_armature_copy.animation_data.action = None

        # armature_apply() richiede Pose Mode con l'oggetto corretto attivo
        bpy.ops.object.select_all(action='DESELECT')
        source_armature_copy.select_set(True)
        bpy.context.view_layer.objects.active = source_armature_copy
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.armature_apply()
        bpy.ops.object.mode_set(mode='OBJECT')

        if source_armature_copy.animation_data and action_tmp:
            assign_action(source_armature_copy, action_tmp)
            if slot_tmp is not None and hasattr(source_armature_copy.animation_data, 'action_slot'):
                try:
                    source_armature_copy.animation_data.action_slot = slot_tmp
                except Exception as e:
                    print(f"[RSL-patch] restore slot failed: {e}")
            print(
                "[RSL-patch] copy_rest_pose action frame_range:",
                action_tmp.frame_range[:],
                "slot:", source_armature_copy.animation_data.action_slot if hasattr(source_armature_copy.animation_data, 'action_slot') else None,
            )

        for bone in source_armature_copy.pose.bones:
            constraint = bone.constraints.new('COPY_TRANSFORMS')
            constraint.name = bone.name
            constraint.target = armature_source
            constraint.subtarget = bone.name

        return source_armature_copy

    def bake_animation(self, armature_source, armature_target, root_bones):
        frame_split = 25
        frame_start, frame_end = self.read_anim_start_end(armature_source)
        frame_start, frame_end = int(frame_start), int(frame_end)
        utils.set_active(armature_target)

        actions_all = []

        current_step = 0
        steps = int((frame_end - frame_start) / frame_split) + 1
        wm = bpy.context.window_manager
        wm.progress_begin(current_step, steps)

        start_time = time.time()

        bpy.ops.object.mode_set(mode='POSE')
        for frame in range(frame_start, frame_end + 2, frame_split):
            start = frame
            end = min(frame + frame_split - 1, frame_end)
            if start > end:
                continue

            bpy.ops.nla.bake(
                frame_start=start,
                frame_end=end,
                visual_keying=True,
                only_selected=True,
                use_current_action=False,
                bake_types={'POSE'}
            )

            baked_action = get_action(armature_target)

            if baked_action is None:
                print(f"[RSL] Warning: nla.bake returned None at frame {frame}, searching bpy.data.actions...")
                for a in reversed(list(bpy.data.actions)):
                    if a.name.startswith('Action') or a.name.startswith('RSL'):
                        baked_action = a
                        assign_action(armature_target, baked_action)
                        break

            if baked_action is None:
                print(f"[RSL] Error: could not retrieve baked action at frame {frame}. Skipping.")
                current_step += 1
                wm.progress_update(current_step)
                continue

            baked_action.name = 'RSL_RETARGETING_' + str(frame)
            actions_all.append(baked_action)

            current_step += 1
            if steps != current_step:
                wm.progress_update(current_step)

        bpy.ops.object.mode_set(mode='OBJECT')

        if not actions_all:
            wm.progress_end()
            return

        # Conta tutti i keyframe per data_path+index
        # [RSL-patch] slot=None: ogni chunk action ha il proprio slot, non quello
        # (sbagliato) attualmente attivo su armature_target.
        key_counts = {}
        for action in actions_all:
            for fcurve in get_action_fcurves(action, None):
                key = fcurve.data_path + str(fcurve.array_index)
                key_counts[key] = key_counts.get(key, 0) + len(fcurve.keyframe_points)

        # Crea l'action finale combinata
        action_final = bpy.data.actions.new(name='RSL_RETARGETING_FINAL')
        action_final.use_fake_user = True

        if armature_target.animation_data is None:
            armature_target.animation_data_create()
        assign_action(armature_target, action_final)

        # Ricombina tutti i chunk in un'unica action
        # [RSL-patch] slot=None qui sotto per lo stesso motivo di key_counts.
        first_fcurves = list(get_action_fcurves(actions_all[0], None))
        for fcurve in first_fcurves:
            if fcurve.data_path.endswith('scale'):
                continue
            if fcurve.data_path.endswith('location'):
                bone_name = fcurve.data_path.split('"')
                if len(bone_name) != 3:
                    continue
                if bone_name[1] not in root_bones:
                    continue

            slot_final = get_slot(armature_target)
            curve_final = new_fcurve(
                action_final,
                slot_final,
                fcurve.data_path,
                fcurve.array_index,
                fcurve.group.name
            )
            keyframe_points = curve_final.keyframe_points
            keyframe_points.add(key_counts[fcurve.data_path + str(fcurve.array_index)])

            idx = 0
            for action in actions_all:
                # [RSL-patch] slot=None: cerca lo slot corretto per ogni chunk action.
                fc_to_add = find_fcurve(action, None, fcurve.data_path, fcurve.array_index)
                if fc_to_add is None:
                    continue
                for kp in fc_to_add.keyframe_points:
                    keyframe_points[idx].co.x = kp.co.x
                    keyframe_points[idx].co.y = kp.co.y
                    keyframe_points[idx].interpolation = 'LINEAR'
                    idx += 1

        # Pulizia: rimuove keyframe ridondanti (stesso valore di prev e next)
        for fcurve in get_action_fcurves(action_final, slot_final):
            if len(fcurve.keyframe_points) <= 2:
                continue

            kp_pre_pre = fcurve.keyframe_points[0]
            kp_pre = fcurve.keyframe_points[1]
            kp_to_delete = []

            for kp in fcurve.keyframe_points[2:]:
                if round(kp_pre_pre.co.y, 5) == round(kp_pre.co.y, 5) == round(kp.co.y, 5):
                    kp_to_delete.append(kp_pre)
                kp_pre_pre = kp_pre
                kp_pre = kp

            for kp in reversed(kp_to_delete):
                fcurve.keyframe_points.remove(kp)

        # Elimina i chunk intermedi
        for action in actions_all:
            bpy.data.actions.remove(action)

        print('[RSL] Retargeting Time:', round(time.time() - start_time, 2), 'seconds')
        wm.progress_end()

    def read_anim_start_end(self, armature_source):
        action = get_action(armature_source)
        if action:
            return action.frame_range
        scene = bpy.context.scene
        return scene.frame_start, scene.frame_end
