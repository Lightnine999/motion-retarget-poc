"""smpl_source_clean.fbx를 임포트한 직후, 애니메이션을 전혀 적용하지 않은
순수 레스트(바인드) 포즈를 렌더링. rest_basis/rest_head 자체가 정상인지 확인용."""
import bpy
import math
import os

REF_FBX = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_clean.fbx"
SHOT_DIR = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/rest_preview"

os.makedirs(SHOT_DIR, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=REF_FBX)

armature = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj
assert armature is not None

# 애니메이션 자체를 제거해서 진짜 바인드 포즈만 남긴다
armature.animation_data_clear()
for pb in armature.pose.bones:
    pb.matrix_basis.identity()

scene = bpy.context.scene
bpy.ops.object.camera_add(location=(0, -6, 1.0), rotation=(math.radians(90), 0, 0))
cam = bpy.context.object
cam.data.type = "ORTHO"
cam.data.ortho_scale = 5.0
scene.camera = cam

scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 480
scene.render.resolution_y = 640
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = os.path.join(SHOT_DIR, "rest_pose.png")
bpy.ops.render.render(write_still=True)
print("saved rest pose preview")

# 본 레스트 위치/방향도 함께 출력 (수치 검증용)
for b in armature.data.bones:
    print(b.name, "head_local=", tuple(round(v, 3) for v in b.head_local), "tail_local=", tuple(round(v, 3) for v in b.tail_local))
