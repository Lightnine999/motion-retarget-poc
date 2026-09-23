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

ALL_NAMES = JOINT_NAMES[:22]
armature.animation_data_clear()
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = T

prev_q = {n: None for n in ALL_NAMES}
for t in range(T):
    frame = t + 1
    scene.frame_set(frame)
    for name in ALL_NAMES:
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
        pb.keyframe_insert(data_path="location", frame=frame, group=name)
        prev_q[name] = q.copy()

OUT = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/isolate_test.fbx"
bpy.ops.object.select_all(action="DESELECT")
armature.select_set(True)
bpy.context.view_layer.objects.active = armature
bpy.ops.export_scene.fbx(
    filepath=OUT, use_selection=True, add_leaf_bones=False, bake_anim=True,
    bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
    bake_anim_step=1.0, bake_anim_force_startend_keying=True,
    bake_anim_simplify_factor=0.0,
)
print("exported isolate_test.fbx")

# 재-import 후 델타 측정
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
        q = pb.rotation_quaternion.copy()
        if history[name] and q.dot(history[name][-1]) < 0:
            q = -q
        history[name].append(q)

print("=== FBX export -> re-import 후 (진짜 왕복 거침) ===")
for name in CHECK:
    qs = history[name]
    d = [math.degrees(qs[i].rotation_difference(qs[i+1]).angle) for i in range(len(qs)-1)]
    top = sorted(range(len(d)), key=lambda i: -d[i])[:5]
    print(f"  {name:12s} max={max(d):6.1f} mean={sum(d)/len(d):5.2f} top_frames={[(i+fs, round(d[i],1)) for i in top]}")
