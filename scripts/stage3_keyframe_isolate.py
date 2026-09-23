import bpy
import numpy as np
import math
from mathutils import Matrix

JOINT_NAMES = ["Pelvis","L_Hip","R_Hip","Spine1","L_Knee","R_Knee","Spine2","L_Ankle","R_Ankle",
               "Spine3","L_Foot","R_Foot","Neck","L_Collar","R_Collar","Head",
               "L_Shoulder","R_Shoulder","L_Elbow","R_Elbow","L_Wrist","R_Wrist","L_Hand","R_Hand"]

global_R = np.load("/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/global_R_blender.npy")
T = global_R.shape[0]

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath="/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_clean.fbx")

armature = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj

rest_basis = {}
for name in JOINT_NAMES:
    rest_basis[name] = armature.data.bones[name].matrix_local.to_3x3()

CHECK = ["Neck", "Head", "L_Shoulder", "R_Shoulder"]
armature.animation_data_clear()
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = T

# 1) 키프레임을 실제로 찍는다 (연속성 보정 포함)
prev_q = {n: None for n in CHECK}
for t in range(T):
    frame = t + 1
    scene.frame_set(frame)
    for name in CHECK:
        j = JOINT_NAMES.index(name)
        rot = Matrix(global_R[t, j].tolist()) @ rest_basis[name]
        pb = armature.pose.bones[name]
        loc = pb.matrix.translation
        m = rot.to_4x4()
        m.translation = loc
        pb.matrix = m
        pb.rotation_mode = "QUATERNION"
        q = pb.rotation_quaternion.copy()
        if prev_q[name] is not None and q.dot(prev_q[name]) < 0:
            q.negate()
            pb.rotation_quaternion = q
        pb.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=name)
        prev_q[name] = q.copy()

# 2) 애니메이션 커브를 "재생"하며(scene.frame_set으로 evaluate) 다시 읽어서 델타 측정
#    -> 이게 FBX 왕복 없이, Blender 내부 애니메이션 시스템만 거친 결과
history = {n: [] for n in CHECK}
for t in range(T):
    frame = t + 1
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    for name in CHECK:
        pb = armature.pose.bones[name]
        q = pb.rotation_quaternion.copy()
        history[name].append(q)

print("=== keyframe 저장 + Blender 애니메이션 재생 후 (FBX 왕복 없음) ===")
for name in CHECK:
    qs = history[name]
    fixed = [qs[0].copy()]
    for i in range(1, len(qs)):
        q = qs[i].copy()
        if q.dot(fixed[-1]) < 0:
            q = -q
        fixed.append(q)
    d = [math.degrees(fixed[i].rotation_difference(fixed[i+1]).angle) for i in range(len(fixed)-1)]
    top = sorted(range(len(d)), key=lambda i: -d[i])[:5]
    print(f"  {name:12s} max={max(d):6.1f} mean={sum(d)/len(d):5.2f} top_frames={[(i+1, round(d[i],1)) for i in top]}")
