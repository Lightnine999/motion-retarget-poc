import bpy

# 1) 애드온 활성화
result = bpy.ops.preferences.addon_enable(module="rokoko_studio_live")
print("addon_enable result:", result)
print("rsl_retargeting_use_pose exists:", hasattr(bpy.types.Scene, "rsl_retargeting_use_pose"))

# 2) 소스(SMPL, 애니메이션 있음)와 타겟(Mixamo, 순정 T포즈) 임포트
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

bpy.ops.import_scene.fbx(filepath="/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_clean.fbx")
source_objs = list(bpy.context.scene.objects)
bpy.ops.import_scene.fbx(filepath="/Users/kwonkwanggoo/motion-retarget-poc/blender/assets/mixamo_character.fbx")
all_objs = list(bpy.context.scene.objects)
target_objs = [o for o in all_objs if o not in source_objs]

source_armature = next(o for o in source_objs if o.type == "ARMATURE")
target_armature = next(o for o in target_objs if o.type == "ARMATURE")
print("source armature:", source_armature.name, "bones:", len(source_armature.data.bones))
print("target armature:", target_armature.name, "bones:", len(target_armature.data.bones))

scene = bpy.context.scene
scene.rsl_retargeting_armature_source = source_armature
scene.rsl_retargeting_armature_target = target_armature
scene.rsl_retargeting_auto_scaling = True
scene.rsl_retargeting_use_pose = "REST"

# 3) 본 리스트 자동 매칭
res = bpy.ops.rsl.build_bone_list()
print("build_bone_list result:", res)
print("bone list count:", len(scene.rsl_retargeting_bone_list))
unmapped = []
for item in scene.rsl_retargeting_bone_list:
    if not item.bone_name_target:
        unmapped.append(item.bone_name_source)
print("unmapped source bones:", unmapped)
for item in list(scene.rsl_retargeting_bone_list)[:40]:
    print(f"  {item.bone_name_source:20s} -> {item.bone_name_target}")
