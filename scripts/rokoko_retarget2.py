import bpy

bpy.ops.preferences.addon_enable(module="rokoko_studio_live")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

bpy.ops.import_scene.fbx(filepath="/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_clean.fbx")
source_objs = list(bpy.context.scene.objects)
bpy.ops.import_scene.fbx(filepath="/Users/kwonkwanggoo/motion-retarget-poc/blender/assets/mixamo_character.fbx")
all_objs = list(bpy.context.scene.objects)
target_objs = [o for o in all_objs if o not in source_objs]

source_armature = next(o for o in source_objs if o.type == "ARMATURE")
target_armature = next(o for o in target_objs if o.type == "ARMATURE")

scene = bpy.context.scene
scene.rsl_retargeting_armature_source = source_armature
scene.rsl_retargeting_armature_target = target_armature
scene.rsl_retargeting_auto_scaling = True
scene.rsl_retargeting_use_pose = "REST"

bpy.ops.rsl.build_bone_list()

MANUAL_FIX = {
    "L_Foot": "mixamorig10:LeftToeBase",
    "R_Foot": "mixamorig10:RightToeBase",
    "L_Shoulder": "mixamorig10:LeftArm",
    "R_Shoulder": "mixamorig10:RightArm",
}
for item in scene.rsl_retargeting_bone_list:
    if item.bone_name_source in MANUAL_FIX:
        item.bone_name_target = MANUAL_FIX[item.bone_name_source]

print("최종 매핑:")
for item in scene.rsl_retargeting_bone_list:
    print(f"  {item.bone_name_source:12s} -> {item.bone_name_target or '(미매칭, L_Hand/R_Hand는 손가락 디테일이라 스코프 밖)'}")

res = bpy.ops.rsl.retarget_animation()
print("retarget_animation result:", res)

act = target_armature.animation_data.action
frame_start, frame_end = act.frame_range
scene.frame_start = int(frame_start)
scene.frame_end = int(frame_end)
print("scene frame range set to:", scene.frame_start, scene.frame_end)
print("target_armature.animation_data.action right before export:", target_armature.animation_data.action, target_armature.animation_data.action.frame_range[:])

bpy.ops.object.select_all(action="DESELECT")
target_armature.select_set(True)
for m in target_objs:
    if m.type == "MESH":
        m.select_set(True)
bpy.context.view_layer.objects.active = target_armature

bpy.ops.export_scene.fbx(
    filepath="/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_retargeted.fbx",
    use_selection=True,
    add_leaf_bones=False,
    bake_anim=True,
    bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,
    bake_anim_step=1.0,
    bake_anim_force_startend_keying=True,
)
print("exported")
