import bpy
import numpy as np
import math
from mathutils import Matrix

JOINT_NAMES = ["Pelvis","L_Hip","R_Hip","Spine1","L_Knee","R_Knee","Spine2","L_Ankle","R_Ankle",
               "Spine3","L_Foot","R_Foot","Neck","L_Collar","R_Collar","Head",
               "L_Shoulder","R_Shoulder","L_Elbow","R_Elbow","L_Wrist","R_Wrist","L_Hand","R_Hand"]

global_R = np.load("/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/global_R_blender.npy")  # (T,22,3,3)
T = global_R.shape[0]

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath="/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_clean.fbx")

armature = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj

# rest_basis 추출 (SMPL 소스 아마추어의 rest orientation)
rest_basis = {}
for name in JOINT_NAMES:
    bone = armature.data.bones.get(name)
    rest_basis[name] = bone.matrix_local.to_3x3()

CHECK = ["Neck", "Head", "L_Shoulder", "R_Shoulder"]
history = {n: [] for n in CHECK}

# 키프레임 저장/FBX 왕복 없이, 메모리 상에서 바로 pose_bone.matrix 설정 -> quaternion 추출
for t in range(T):
    for name in CHECK:
        j = JOINT_NAMES.index(name)
        rot = Matrix(global_R[t, j].tolist()) @ rest_basis[name]
        pb = armature.pose.bones[name]
        # 위치는 무시(회전만 확인), matrix_basis 대신 pose matrix 구성 시 location은 임의 유지
        loc = pb.matrix.translation
        m = rot.to_4x4()
        m.translation = loc
        pb.matrix = m
        q = pb.rotation_quaternion.copy()
        if history[name] and q.dot(history[name][-1]) < 0:
            q = -q
        history[name].append(q)

print("=== Blender matrix->quaternion 변환만 거친 결과 (keyframe/FBX 왕복 없음) ===")
for name in CHECK:
    qs = history[name]
    d = [math.degrees(qs[i].rotation_difference(qs[i+1]).angle) for i in range(len(qs)-1)]
    top = sorted(range(len(d)), key=lambda i: -d[i])[:5]
    print(f"  {name:12s} max={max(d):6.1f} mean={sum(d)/len(d):5.2f} top_frames={[(i+1, round(d[i],1)) for i in top]}")
