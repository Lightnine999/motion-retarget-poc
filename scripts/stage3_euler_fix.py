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

armature.animation_data_clear()
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = T

# 본마다 "이전 프레임과 최대한 가까운(연속적인)" 오일러로 변환하며 기록
prev_euler = {n: None for n in JOINT_NAMES}
for t in range(T):
    frame = t + 1
    scene.frame_set(frame)
    for name in JOINT_NAMES:
        j = JOINT_NAMES.index(name)
        rot = Matrix(global_R[t, j].tolist()) @ rest_basis[name]
        pb = armature.pose.bones[name]
        pb.rotation_mode = "XYZ"
        loc = pb.matrix.translation
        m = rot.to_4x4()
        m.translation = loc
        # compatible euler: 이전 프레임 오일러와 최대한 가깝게(연속적으로) 변환
        euler = m.to_euler("XYZ", prev_euler[name]) if prev_euler[name] is not None else m.to_euler("XYZ")
        pb.rotation_euler = euler
        pb.keyframe_insert(data_path="rotation_euler", frame=frame, group=name)
        pb.keyframe_insert(data_path="location", frame=frame, group=name)
        prev_euler[name] = euler

OUT = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/isolate_test_euler.fbx"
bpy.ops.object.select_all(action="DESELECT")
armature.select_set(True)
bpy.context.view_layer.objects.active = armature
bpy.ops.export_scene.fbx(
    filepath=OUT, use_selection=True, add_leaf_bones=False, bake_anim=True,
    bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
    bake_anim_step=1.0, bake_anim_force_startend_keying=True,
    bake_anim_simplify_factor=0.0,
)
print("exported", OUT)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=OUT)
armature2 = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature2 = obj
action = armature2.animation_data.action
fs, fe = int(action.frame_range[0]), int(action.frame_range[1])

CHECK = ["Neck", "Head", "L_Shoulder", "R_Shoulder"]
history = {n: [] for n in CHECK}
for f in range(fs, fe + 1):
    scene.frame_set(f)
    for name in CHECK:
        pb = armature2.pose.bones[name]
        # 오일러로 재import됐을 수 있으니, 모드에 상관없이 matrix에서 quaternion 추출해 비교
        q = pb.matrix_basis.to_quaternion() if pb.matrix_basis else pb.rotation_quaternion.copy()
        if history[name] and q.dot(history[name][-1]) < 0:
            q = q.copy()
            q.negate()
        history[name].append(q)

print("=== 오일러 연속성 필터 적용 -> FBX export -> re-import 후 ===")
for name in CHECK:
    qs = history[name]
    d = [math.degrees(qs[i].rotation_difference(qs[i+1]).angle) for i in range(len(qs)-1)]
    top = sorted(range(len(d)), key=lambda i: -d[i])[:5]
    print(f"  {name:12s} max={max(d):6.1f} mean={sum(d)/len(d):5.2f} top_frames={[(i+fs, round(d[i],1)) for i in top]}")
