import bpy
import math
from mathutils import Quaternion

SRC = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_retargeted.fbx"
OUT = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_final2.fbx"

HARD_CEILING_DEG = {
    "mixamorig10:Hips": 12.0,
    "mixamorig10:Spine": 10.0,
    "mixamorig10:Spine1": 10.0,
    "mixamorig10:Spine2": 10.0,
    "mixamorig10:Neck": 11.0,
    "mixamorig10:Head": 12.0,
    "mixamorig10:LeftShoulder": 11.0,
    "mixamorig10:RightShoulder": 11.0,
    "mixamorig10:LeftArm": 26.0,
    "mixamorig10:RightArm": 26.0,
    "mixamorig10:LeftForeArm": 38.0,
    "mixamorig10:RightForeArm": 38.0,
    "mixamorig10:LeftHand": 80.0,
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
    "mixamorig10:LeftHand": 35.0,
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

# 위치(location)는 절대 건드리지 않는다 — 회전만 다룬다.
all_bones = [pb.name for pb in armature.pose.bones]

# 1) 실제 pose를 mode-무관하게 읽는다 (matrix_basis 기준 — export 필드와 무관하게 항상 정확)
quat_seq = {b: [] for b in all_bones}
loc_seq = {b: [] for b in all_bones}
for f in range(frame_start, frame_end + 1):
    scene.frame_set(f)
    for b in all_bones:
        pb = armature.pose.bones[b]
        q = pb.matrix_basis.to_quaternion()
        if quat_seq[b] and q.dot(quat_seq[b][-1]) < 0:
            q = -q
        quat_seq[b].append(q)
        loc_seq[b].append(pb.matrix_basis.translation.copy())

def deltas_of(qs):
    return [math.degrees(qs[i].rotation_difference(qs[i+1]).angle) for i in range(len(qs)-1)]

# 2) 이상치 탐지 + SLERP 보정 (쿼터니언 공간에서, 검증된 로직)
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

print(f"총 (본, 프레임) 보정 건수: {total_bad}")

# 3) 보정된 쿼터니언을 "연속적인 오일러"로 변환해서 기록 (근본 수정과 동일한 방식)
for pb in armature.pose.bones:
    pb.rotation_mode = "XYZ"

for b_name in all_bones:
    pb = armature.pose.bones[b_name]
    qs = quat_seq[b_name]
    locs = loc_seq[b_name]
    prev_euler = None
    for i, f in enumerate(range(frame_start, frame_end + 1)):
        scene.frame_set(f)
        euler = qs[i].to_matrix().to_euler("XYZ", prev_euler) if prev_euler is not None else qs[i].to_matrix().to_euler("XYZ")
        pb.rotation_euler = euler
        pb.location = locs[i]
        prev_euler = euler
        pb.keyframe_insert(data_path="location", frame=f, group=b_name)
        pb.keyframe_insert(data_path="rotation_euler", frame=f, group=b_name)
        pb.keyframe_insert(data_path="scale", frame=f, group=b_name)

# 4) 검증 (matrix_basis 재확인, mode 무관)
print("--- 최종 델타(최대/평균), matrix_basis 기준 ---")
for b in ["mixamorig10:Neck", "mixamorig10:Head", "mixamorig10:LeftShoulder", "mixamorig10:RightShoulder",
          "mixamorig10:LeftArm", "mixamorig10:RightArm", "mixamorig10:LeftForeArm", "mixamorig10:RightForeArm"]:
    pb = armature.pose.bones[b]
    qs2 = []
    for f in range(frame_start, frame_end + 1):
        scene.frame_set(f)
        q = pb.matrix_basis.to_quaternion()
        if qs2 and q.dot(qs2[-1]) < 0:
            q = -q
        qs2.append(q)
    d = deltas_of(qs2)
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
    bake_anim_simplify_factor=0.0,
)
print("exported:", OUT)
