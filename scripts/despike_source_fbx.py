import bpy
import math
import mathutils

IN_PATH = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_clean.fbx"
OUT_PATH = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_clean_despiked.fbx"
THRESH_DEG = 60.0  # SMPL 원본 axis-angle 기준 최대치가 32도 수준이었으므로 여유있게 60도로 설정

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=IN_PATH)

armature = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj

action = armature.animation_data.action
frame_end = int(action.frame_range[1])
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = frame_end

pose_bones = armature.pose.bones
bone_names = [b.name for b in pose_bones]
print(f"bones: {len(bone_names)}, frames: {frame_end}")

for pb in pose_bones:
    pb.rotation_mode = "QUATERNION"

# 프레임별로 전체 본의 로컬 회전 쿼터니언 수집
history = {name: [] for name in bone_names}
for f in range(1, frame_end + 1):
    scene.frame_set(f)
    for name in bone_names:
        history[name].append(pose_bones[name].rotation_quaternion.copy())


def quat_angle_deg(q1, q2):
    dot = abs(q1.dot(q2))
    dot = min(1.0, max(-1.0, dot))
    return math.degrees(2 * math.acos(dot))


def slerp(q0, q1, t):
    return q0.slerp(q1, t) if q0.dot(q1) >= 0 else q0.slerp(-q1, t)


def iter_fcurves(action):
    # Blender >=4.4 moved fcurves under layers/strips/channelbags.
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        yield from legacy
        return
    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            for channelbag in getattr(strip, "channelbags", ()):
                yield from channelbag.fcurves


fixed_summary = {}
for name in bone_names:
    qs = history[name]
    deltas = [quat_angle_deg(qs[i], qs[i + 1]) for i in range(len(qs) - 1)]
    bad = set()
    for i, d in enumerate(deltas):
        if d > THRESH_DEG:
            bad.add(i)
            bad.add(i + 1)

    new_qs = list(qs)
    if bad:
        sorted_bad = sorted(bad)
        runs = []
        start = prev = sorted_bad[0]
        for f in sorted_bad[1:]:
            if f == prev + 1:
                prev = f
            else:
                runs.append((start, prev))
                start = prev = f
        runs.append((start, prev))

        for s, e in runs:
            before_ok = s > 0
            after_ok = e < len(qs) - 1
            if before_ok and after_ok:
                anchor_a = qs[s - 1]
                anchor_b = qs[e + 1]
                span = (e + 1) - (s - 1)
                for f in range(s, e + 1):
                    t = (f - (s - 1)) / span
                    new_qs[f] = slerp(anchor_a, anchor_b, t)
            elif after_ok:
                for f in range(s, e + 1):
                    new_qs[f] = qs[e + 1]
            elif before_ok:
                for f in range(s, e + 1):
                    new_qs[f] = qs[s - 1]
        fixed_summary[name] = runs

    # 조사 문서 §3.3 검증된 방법: 쿼터니언을 "이전 프레임과 연속적인" 오일러로 직접 변환해서 키프레임.
    # Blender 기본 FBX exporter의 자체 쿼터니언->오일러 변환(비연속)을 우회하기 위해
    # 오일러를 미리 계산해서 넣어둔다.
    pb = pose_bones[name]
    pb.rotation_mode = "XYZ"
    prev_euler = None
    for i, f in enumerate(range(1, frame_end + 1)):
        scene.frame_set(f)
        euler = new_qs[i].to_euler("XYZ", prev_euler) if prev_euler is not None else new_qs[i].to_euler("XYZ")
        pb.rotation_euler = euler
        pb.keyframe_insert(data_path="rotation_euler", frame=f)
        prev_euler = euler

print("fixed bones (despiked):", len(fixed_summary))
for name, runs in fixed_summary.items():
    print(f"  {name}: {runs}")

# 키프레임 보간을 LINEAR로 고정 (패치의 _linearize_action과 동일) — 베지어 보간이
# 프레임 사이에서 오버슈트를 만들어 bake_anim 재계산 시 다시 튈 수 있음을 방지.
if armature.animation_data and armature.animation_data.action:
    for curve in iter_fcurves(armature.animation_data.action):
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"

# bake_anim=False: 이미 찍어둔 연속-오일러 키프레임을 그대로 FBX 커브로 쓰도록 강제.
# bake_anim=True는 매 프레임 pose를 재평가해서 exporter 자체 쿼터니언->오일러 변환을
# 다시 거치는 것으로 보이며, 이게 despike/패치 결과가 export 후에도 깨지는 원인으로 의심됨.
bpy.ops.export_scene.fbx(
    filepath=OUT_PATH,
    use_selection=False,
    bake_anim=False,
    add_leaf_bones=False,
)
print("exported:", OUT_PATH)
