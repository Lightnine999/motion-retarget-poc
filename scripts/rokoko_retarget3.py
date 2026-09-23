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
act = target_armature.animation_data.action if target_armature.animation_data else None
print("target action:", act, "frame_range:", act.frame_range[:] if act else None)
if act:
    from rokoko_studio_live.operators.retargeting import get_action_fcurves
    fcs = list(get_action_fcurves(act, None))
    print("num fcurves:", len(fcs))
    for fc in fcs[:5]:
        print("  ", fc.data_path, fc.array_index, "keys:", len(fc.keyframe_points))


bpy.ops.export_scene.fbx(
    filepath="/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_retargeted.fbx",
    use_selection=False,
    add_leaf_bones=False,
    bake_anim=True,
)
print("exported")
