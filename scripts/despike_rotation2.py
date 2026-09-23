import bpy
import math
from mathutils import Quaternion

SRC = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_retargeted.fbx"
OUT = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_despiked.fbx"
SPIKE_DEG = 35.0
MIN_BONES_AGREE = 3  # 이 개수 이상의 본이 "동시에" 튀어야 진짜 이상치로 간주

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=SRC)

armature = bpy.data.objects.get("Armature")
action = armature.animation_data.action
frame_start, frame_end = int(action.frame_range[0]), int(action.frame_range[1])
n_frames = frame_end - frame_start + 1
scene = bpy.context.scene

CHECK_BONES = [
    "mixamorig10:Neck", "mixamorig10:Head",
    "mixamorig10:LeftShoulder", "mixamorig10:RightShoulder",
    "mixamorig10:LeftArm", "mixamorig10:RightArm",
    "mixamorig10:LeftForeArm", "mixamorig10:RightForeArm",
]
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

# 전환(프레임 i -> i+1) 단위로 "동시에 튀는 본 개수" 집계
n_trans = n_frames - 1
agree_count = [0] * n_trans
for b in CHECK_BONES:
    qs = quat_seq[b]
    for i in range(n_trans):
        d = math.degrees(qs[i].rotation_difference(qs[i+1]).angle)
        if d > SPIKE_DEG:
            agree_count[i] += 1

bad_transitions = [i for i, c in enumerate(agree_count) if c >= MIN_BONES_AGREE]
print(f"전역 이상치로 판정된 전환 수: {len(bad_transitions)} / {n_trans}")

# 전환 i가 나쁘면 프레임 i, i+1 둘 다 의심
frame_is_bad = [False] * n_frames
for i in bad_transitions:
    frame_is_bad[i] = True
    frame_is_bad[i + 1] = True
bad_indices = [i for i, v in enumerate(frame_is_bad) if v]
print(f"이상치 프레임 수: {len(bad_indices)} / {n_frames}")
print("이상치 프레임(1-indexed):", [i + frame_start for i in bad_indices])

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
print("이상치 구간(run, 0-indexed):", runs)

for (a, b) in runs:
    good_before = a - 1
    good_after = b + 1
    for b_name in all_bones:
        qs = quat_seq[b_name]
        if good_before < 0 and good_after < n_frames:
            # 시작 경계: 뒤쪽 첫 정상 프레임 값으로 고정
            for i in range(a, b + 1):
                qs[i] = qs[good_after].copy()
        elif good_after >= n_frames and good_before >= 0:
            # 끝 경계: 앞쪽 마지막 정상 프레임 값으로 고정
            for i in range(a, b + 1):
                qs[i] = qs[good_before].copy()
        elif good_before >= 0 and good_after < n_frames:
            span = good_after - good_before
            q0, q1 = qs[good_before], qs[good_after]
            for i in range(a, b + 1):
                t = (i - good_before) / span
                qs[i] = q0.slerp(q1, t)
        else:
            print(f"전체가 이상치 구간이라 처리 불가: run=({a},{b})")

for b_name in all_bones:
    pb = armature.pose.bones[b_name]
    qs = quat_seq[b_name]
    for i, f in enumerate(range(frame_start, frame_end + 1)):
        scene.frame_set(f)
        pb.rotation_quaternion = qs[i]
        pb.keyframe_insert(data_path="rotation_quaternion", frame=f, group=b_name)

print("--- 보정 후 델타(최대/평균) ---")
for b_name in CHECK_BONES:
    qs = quat_seq[b_name]
    deltas = [math.degrees(qs[i].rotation_difference(qs[i+1]).angle) for i in range(len(qs)-1)]
    print(f"{b_name:25s} max={max(deltas):6.1f} mean={sum(deltas)/len(deltas):5.2f}")

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
