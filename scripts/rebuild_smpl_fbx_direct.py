"""
1단계 재구축: SMPL body_pose(로컬 axis-angle, 검증된 깨끗한 값)를 Motius의
글로벌 회전 합성 + 스무딩 파이프라인을 거치지 않고 뼈대의 로컬 회전에 직접 적용한다.

기존 export_smpl_source.py 경로:
  body_pose(로컬) -> _global_rotations(FK 합성) -> _smooth_global_rotations(스무딩, 의심 지점)
    -> _local_rotations(역산) -> Blender 본에 적용

이 스크립트의 경로:
  body_pose(로컬) -> 바로 Blender 본의 rotation_quaternion에 적용 (중간 합성/스무딩 없음)
"""
import bpy
import mathutils
import numpy as np
import math

PARAMS_PATH = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_params_raw.npz"
REF_FBX = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_clean.fbx"
OUT_FBX = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_direct.fbx"

# SMPL body_pose 배열 인덱스(0-based, 23개) -> 관절 이름
# body_pose가 63개(21관절) 뿐이라 SMPL22(손 관절 제외) 컨벤션임 — L_Hand/R_Hand 없음
JOINT_ORDER = [
    "L_Hip", "R_Hip", "Spine1", "L_Knee", "R_Knee", "Spine2",
    "L_Ankle", "R_Ankle", "Spine3", "L_Foot", "R_Foot", "Neck",
    "L_Collar", "R_Collar", "Head", "L_Shoulder", "R_Shoulder",
    "L_Elbow", "R_Elbow", "L_Wrist", "R_Wrist",
]

npz = np.load(PARAMS_PATH)
global_orient = npz["global_orient"]  # [T,3]
body_pose = npz["body_pose"]          # [T,69]
transl = npz["transl"]                # [T,3]
num_frames = global_orient.shape[0]
print(f"frames: {num_frames}")


def aa_to_quat(v):
    angle = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if angle < 1e-8:
        return mathutils.Quaternion((1.0, 0.0, 0.0, 0.0))
    axis = (v[0] / angle, v[1] / angle, v[2] / angle)
    s = math.sin(angle / 2)
    # mathutils.Quaternion 생성자는 (w,x,y,z)
    return mathutils.Quaternion((math.cos(angle / 2), axis[0] * s, axis[1] * s, axis[2] * s))


# 기존에 검증된 레스트포즈(본 계층/위치)를 그대로 재사용하기 위해 기존 FBX를 임포트
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=REF_FBX)

armature = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj
assert armature is not None

armature.animation_data_clear()
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = num_frames
scene.render.fps = 30

pose_bones = armature.pose.bones
for pb in pose_bones:
    pb.rotation_mode = "QUATERNION"

missing = [n for n in (["Pelvis"] + JOINT_ORDER) if n not in pose_bones]
print("missing bones:", missing)

for index in range(num_frames):
    frame = index + 1
    scene.frame_set(frame)

    pelvis = pose_bones["Pelvis"]
    pelvis.rotation_quaternion = aa_to_quat(global_orient[index])
    pelvis.location = mathutils.Vector(tuple(transl[index]))
    pelvis.keyframe_insert(data_path="rotation_quaternion", frame=frame)
    pelvis.keyframe_insert(data_path="location", frame=frame)

    for j, name in enumerate(JOINT_ORDER):
        if name not in pose_bones:
            continue
        pb = pose_bones[name]
        aa = body_pose[index, j * 3:j * 3 + 3]
        pb.rotation_quaternion = aa_to_quat(aa)
        pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)

scene.frame_set(1)

# 보간을 LINEAR로 고정 (베지어 오버슈트 방지)
if armature.animation_data and armature.animation_data.action:
    action = armature.animation_data.action
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        curves = legacy
    else:
        curves = []
        for layer in getattr(action, "layers", ()):
            for strip in getattr(layer, "strips", ()):
                for channelbag in getattr(strip, "channelbags", ()):
                    curves.extend(channelbag.fcurves)
    for curve in curves:
        for kp in curve.keyframe_points:
            kp.interpolation = "LINEAR"

bpy.ops.export_scene.fbx(
    filepath=OUT_FBX,
    use_selection=False,
    bake_anim=True,
    bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False,
    bake_anim_use_all_actions=False,
    bake_anim_force_startend_keying=True,
    bake_anim_simplify_factor=0.0,
    add_leaf_bones=False,
)
print("exported:", OUT_FBX)
