import bpy
import math
from mathutils import Quaternion

SRC = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_retargeted.fbx"
OUT = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_despiked4.fbx"

HARD_CEILING_DEG = {
    "mixamorig10:Hips": 12.0,
    "mixamorig10:Spine": 10.0,
    "mixamorig10:Spine1": 10.0,
    "mixamorig10:Spine2": 10.0,
    "mixamorig10:Neck": 11.0,
    "mixamorig10:Head": 12.0,
    "mixamorig10:LeftShoulder": 11.0,
    "mixamorig10:RightShoulder": 11.0,
    "mixamorig10:LeftArm": 24.0,
    "mixamorig10:RightArm": 24.0,
    "mixamorig10:LeftForeArm": 34.0,
    "mixamorig10:RightForeArm": 34.0,
    "mixamorig10:LeftHand": 80.0,   # 손목(SMPL L_Wrist) — 정상 최대치가 커서(스윙 스냅) 높게 잡음
    "mixamorig10:RightHand": 80.0,
    "mixamorig10:LeftUpLeg": 20.0,
    "mixamorig10:RightUpLeg": 20.0,
    "mixamorig10:LeftLeg": 26.0,
    "mixamorig10:RightLeg": 26.0,
    "mixamorig10:LeftFoot": 26.0,
    "mixamorig10:RightFoot": 26.0,
    "mixamorig10:LeftToeBase": 26.0,
    "mixamorig10:RightToeBase": 26.0,
}
DEFAULT_CEILING = 45.0

SPIKE_RETURN_MIN_DEFAULT = 10.0
SPIKE_RETURN_MIN = {
    "mixamorig10:LeftHand": 35.0,   # 손목은 원래 빨라서 "돌아옴" 판정 민감도를 낮춤(오탐 방지)
    "mixamorig10:RightHand": 35.0,
    "mixamorig10:LeftForeArm": 18.0,
    "mixamorig10:RightForeArm": 18.0,
}
SPIKE_RETURN_RATIO = 0.45

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=SRC)

armature = bpy.data.objects.get("Armature")
action = armature.animation_data.action
frame_start, frame_end = int(action.frame_range[0]), int(action.frame_range[1])
n_frames = frame_end - frame_start + 1
scene = bpy.context.scene

all_bones = [pb.name for pb in armature.pose.bones if pb.rotation_mode == "QUATERNION"]

quat_seq = {b: [] for b in all_bones}
for f in range(frame_start, frame_end + 1):
    scene.frame_set(f)
    for b in all_bones:
        pb = armature.pose.bones[b]
        q = pb.rotation_quaternion.copy()
        if quat_seq[b] and q.dot(quat_seq[b][-1]) < 0:
            q = -q
        quat_seq[b].append(q)

def deltas_of(qs):
    return [math.degrees(qs[i].rotation_difference(qs[i+1]).angle) for i in range(len(qs)-1)]

total_bad = 0
for b in all_bones:
    qs = quat_seq[b]
    d = deltas_of(qs)
    ceiling = HARD_CEILING_DEG.get(b, DEFAULT_CEILING)
    return_min = SPIKE_RETURN_MIN.get(b, SPIKE_RETURN_MIN_DEFAULT)

    bad_frame = [False] * n_frames
    for i in range(len(d)):
        if d[i] > ceiling:
            bad_frame[i] = True
            bad_frame[i + 1] = True
    for i in range(1, len(d)):
        d_prev, d_next = d[i - 1], d[i]
        if d_prev > return_min and d_next > return_min:
            skip = math.degrees(qs[i - 1].rotation_difference(qs[i + 1]).angle)
            if skip < min(d_prev, d_next) * SPIKE_RETURN_RATIO:
                bad_frame[i] = True

    bad_indices = [i for i, v in enumerate(bad_frame) if v]
    if bad_indices:
        total_bad += len(bad_indices)
        print(f"[{b}] 이상치 {len(bad_indices)}프레임")

    runs = []
    if bad_indices:
        run_start = bad_indices[0]
        prev = bad_indices[0]
        for i in bad_indices[1:]:
            if i == prev + 1:
                prev = i
            else:
                runs.append((run_start, prev))
                run_start = i
                prev = i
        runs.append((run_start, prev))

    for (a, bb) in runs:
        good_before = a - 1
        good_after = bb + 1
        if good_before < 0 and good_after < n_frames:
            for i in range(a, bb + 1):
                qs[i] = qs[good_after].copy()
        elif good_after >= n_frames and good_before >= 0:
            for i in range(a, bb + 1):
                qs[i] = qs[good_before].copy()
        elif good_before >= 0 and good_after < n_frames:
            span = good_after - good_before
            q0, q1 = qs[good_before], qs[good_after]
            for i in range(a, bb + 1):
                t = (i - good_before) / span
                qs[i] = q0.slerp(q1, t)

print(f"\n총 (본, 프레임) 보정 건수: {total_bad}")

for b_name in all_bones:
    pb = armature.pose.bones[b_name]
    qs = quat_seq[b_name]
    for i, f in enumerate(range(frame_start, frame_end + 1)):
        scene.frame_set(f)
        pb.rotation_quaternion = qs[i]
        pb.keyframe_insert(data_path="rotation_quaternion", frame=f, group=b_name)

print("--- 보정 후 델타(최대/평균) ---")
for b in ["mixamorig10:Spine", "mixamorig10:Spine1", "mixamorig10:Spine2",
          "mixamorig10:Neck", "mixamorig10:Head", "mixamorig10:LeftShoulder", "mixamorig10:RightShoulder",
          "mixamorig10:LeftArm", "mixamorig10:RightArm", "mixamorig10:LeftForeArm", "mixamorig10:RightForeArm",
          "mixamorig10:LeftHand", "mixamorig10:RightHand"]:
    d = deltas_of(quat_seq[b])
    print(f"{b:25s} max={max(d):6.1f} mean={sum(d)/len(d):5.2f}")

scene.frame_start = frame_start
scene.frame_end = frame_end

bpy.ops.object.select_all(action="DESELECT")
armature.select_set(True)
for obj in bpy.context.scene.objects:
    if obj.type == "MESH":
        obj.select_set(True)
bpy.context.view_layer.objects.active = armature

bpy.ops.export_scene.fbx(
    filepath=OUT,
    use_selection=True,
    add_leaf_bones=False,
    bake_anim=True,
    bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,
    bake_anim_step=1.0,
    bake_anim_force_startend_keying=True,
)
print("exported:", OUT)
