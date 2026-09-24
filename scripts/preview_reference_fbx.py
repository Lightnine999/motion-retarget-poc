"""대조군: smpl_source_clean.fbx(원본, 수정 없음)를 그대로 같은 카메라 세팅으로 렌더링.
재구축 스크립트(rebuild_smpl_fbx_fk.py)의 결과가 망가진 게 내 로직 버그인지,
카메라 프레이밍/원래 포즈 문제인지 가려내기 위한 대조군."""
import bpy
import math
import os

REF_FBX = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_clean.fbx"
SHOT_DIR = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/ref_preview"

os.makedirs(SHOT_DIR, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=REF_FBX)

armature = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj
assert armature is not None

scene = bpy.context.scene
num_frames = int(armature.animation_data.action.frame_range[1]) if armature.animation_data and armature.animation_data.action else 312
print("num_frames (from action):", num_frames)

# 카메라를 캐릭터 전신이 들어오도록 넉넉하게 배치 (원점 기준, SMPL 스케일은 미터 단위)
bpy.ops.object.camera_add(location=(0, -6, 1.0), rotation=(math.radians(90), 0, 0))
cam_front = bpy.context.object
cam_front.name = "Cam_Front"
cam_front.data.type = "ORTHO"
cam_front.data.ortho_scale = 5.0

scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 480
scene.render.resolution_y = 640
scene.render.image_settings.file_format = "PNG"
scene.camera = cam_front

preview_frames = [1, 50, 100, 150, 200, 250, 300]
for f in preview_frames:
    scene.frame_set(f)
    scene.render.filepath = os.path.join(SHOT_DIR, f"front_frame{f:04d}.png")
    bpy.ops.render.render(write_still=True)
    print("saved frame", f)

print("done")
