import bpy
import math
from mathutils import Quaternion

SRC = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_retargeted.fbx"
OUT = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_despiked.fbx"
SPIKE_DEG = 35.0  # 이 각도(도) 이상 튀면 이상치로 간주

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=SRC)

armature = bpy.data.objects.get("Armature")
action = armature.animation_data.action
frame_start, frame_end = int(action.frame_range[0]), int(action.frame_range[1])
n_frames = frame_end - frame_start + 1
scene = bpy.context.scene

bone_names = [pb.name for pb in armature.pose.bones if pb.rotation_mode == "QUATERNION"]

# 1) 전 본의 연속성-보정 quaternion 시퀀스 추출
quat_seq = {}
for b in bone_names:
    quat_seq[b] = []

for i, f in enumerate(range(frame_start, frame_end + 1)):
    scene.frame_set(f)
    for b in bone_names:
        pb = armature.pose.bones[b]
        q = pb.rotation_quaternion.copy()
        if quat_seq[b] and q.dot(quat_seq[b][-1]) < 0:
            q = -q
        quat_seq[b].append(q)

# 2) 프레임별 "이 프레임에서 걸리는 본이 있는지" 전역 플래그 계산
frame_is_bad = [False] * n_frames
for b in bone_names:
    qs = quat_seq[b]
    for i in range(len(qs) - 1):
        d = math.degrees(qs[i].rotation_difference(qs[i+1]).angle)
        if d > SPIKE_DEG:
            frame_is_bad[i] = True
            frame_is_bad[i + 1] = True

bad_indices = [i for i, v in enumerate(frame_is_bad) if v]
print(f"이상치로 판정된 프레임 수: {len(bad_indices)} / {n_frames}")
print("이상치 프레임(1-indexed):", [i + frame_start for i in bad_indices])

# 3) 연속 구간(run)으로 묶기
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

# 4) 각 run을 앞뒤 정상 프레임 사이 SLERP로 대체
for (a, b) in runs:
    good_before = a - 1
    good_after = b + 1
    if good_before < 0 or good_after >= n_frames:
        print(f"경계 구간이라 스킵: run=({a},{b})")
        continue
    span = good_after - good_before
    for b_name in bone_names:
        qs = quat_seq[b_name]
        q0 = qs[good_before]
        q1 = qs[good_after]
        for i in range(a, b + 1):
            t = (i - good_before) / span
            qs[i] = q0.slerp(q1, t)

# 5) 보정된 quaternion을 keyframe에 다시 기록
for b_name in bone_names:
    pb = armature.pose.bones[b_name]
    qs = quat_seq[b_name]
    for i, f in enumerate(range(frame_start, frame_end + 1)):
        scene.frame_set(f)
        pb.rotation_quaternion = qs[i]
        pb.keyframe_insert(data_path="rotation_quaternion", frame=f, group=b_name)

# 검증: 다시 델타 계산
print("--- 보정 후 델타(최대) ---")
for b_name in ["mixamorig10:Neck", "mixamorig10:RightForeArm", "mixamorig10:LeftForeArm", "mixamorig10:RightArm"]:
    qs = quat_seq[b_name]
    deltas = [math.degrees(qs[i].rotation_difference(qs[i+1]).angle) for i in range(len(qs)-1)]
    print(f"{b_name:25s} max={max(deltas):6.1f} mean={sum(deltas)/len(deltas):5.2f}")

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
