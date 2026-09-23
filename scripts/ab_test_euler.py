import bpy
import numpy as np
import math
from mathutils import Matrix

JOINT_NAMES = ["Pelvis","L_Hip","R_Hip","Spine1","L_Knee","R_Knee","Spine2","L_Ankle","R_Ankle",
               "Spine3","L_Foot","R_Foot","Neck","L_Collar","R_Collar","Head",
               "L_Shoulder","R_Shoulder","L_Elbow","R_Elbow","L_Wrist","R_Wrist"]

global_R = np.load("/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/global_R_blender.npy")
T = global_R.shape[0]

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath="/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_clean.fbx")

armature = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj

rest_basis = {name: armature.data.bones[name].matrix_local.to_3x3() for name in JOINT_NAMES}

# 본 계층(부모) 확인
print("=== 본 계층 구조 확인 ===")
for name in ["Pelvis", "Spine1", "Spine2", "Spine3", "Neck", "L_Collar", "L_Shoulder"]:
    b = armature.data.bones[name]
    print(f"  {name}: parent={b.parent.name if b.parent else None}")

CHECK = ["Neck", "L_Shoulder"]

for method in ["absolute", "local_matrix_basis"]:
    for pb in armature.pose.bones:
        pb.matrix_basis.identity()
    prev = {n: None for n in CHECK}
    history = {n: [] for n in CHECK}
    for t in range(T):
        for name in JOINT_NAMES:
            j = JOINT_NAMES.index(name)
            rot = Matrix(global_R[t, j].tolist()) @ rest_basis[name]
            pb = armature.pose.bones[name]
            pb.rotation_mode = "XYZ"
            loc = pb.matrix.translation
            m = rot.to_4x4()
            m.translation = loc
            pb.matrix = m
            if name in CHECK:
                if method == "absolute":
                    src = m
                else:
                    src = pb.matrix_basis
                euler = src.to_euler("XYZ", prev[name]) if prev[name] is not None else src.to_euler("XYZ")
                pb.rotation_euler = euler
                prev[name] = euler
                history[name].append(pb.matrix.to_quaternion())  # 최종 절대 pose를 다시 읽어 검증
    print(f"\n=== method={method} (FBX 왕복 없이, 메모리상 최종 pose.matrix 기준) ===")
    for name in CHECK:
        qs = history[name]
        fixed = [qs[0].copy()]
        for i in range(1, len(qs)):
            q = qs[i].copy()
            if q.dot(fixed[-1]) < 0:
                q = -q
            fixed.append(q)
        d = [math.degrees(fixed[i].rotation_difference(fixed[i+1]).angle) for i in range(len(fixed)-1)]
        print(f"  {name:12s} max={max(d):6.1f} mean={sum(d)/len(d):5.2f}")
