import unreal
import json
import math
import traceback

REPORT = {}


def safe(label, fn):
    try:
        return fn()
    except Exception as e:
        REPORT[f"error_{label}"] = str(e)
        REPORT[f"traceback_{label}"] = traceback.format_exc()
        return None


def quat_angle_deg(q1, q2):
    dot = abs(q1.x * q2.x + q1.y * q2.y + q1.z * q2.z + q1.w * q2.w)
    dot = min(1.0, max(-1.0, dot))
    return math.degrees(2 * math.acos(dot))


def slerp(q0, q1, t):
    dot = q0.x * q1.x + q0.y * q1.y + q0.z * q1.z + q0.w * q1.w
    sign = 1.0
    if dot < 0:
        sign = -1.0
        dot = -dot
    dot = min(1.0, max(-1.0, dot))
    if dot > 0.9995:
        x = q0.x + t * (sign * q1.x - q0.x)
        y = q0.y + t * (sign * q1.y - q0.y)
        z = q0.z + t * (sign * q1.z - q0.z)
        w = q0.w + t * (sign * q1.w - q0.w)
    else:
        theta_0 = math.acos(dot)
        theta = theta_0 * t
        sin_theta = math.sin(theta)
        sin_theta_0 = math.sin(theta_0)
        s0 = math.cos(theta) - dot * sin_theta / sin_theta_0
        s1 = sin_theta / sin_theta_0
        x = s0 * q0.x + s1 * (sign * q1.x)
        y = s0 * q0.y + s1 * (sign * q1.y)
        z = s0 * q0.z + s1 * (sign * q1.z)
        w = s0 * q0.w + s1 * (sign * q1.w)
    n = math.sqrt(x * x + y * y + z * z + w * w)
    return unreal.Quat(x / n, y / n, z / n, w / n)


anim_path = "/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo"
anim = unreal.EditorAssetLibrary.load_asset(anim_path)
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")
subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)

# 실제 스켈레톤 본 이름(제대로 된 케이스) 전체 목록 확보
track_names_lower = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(anim)]


def find_root(mesh, known_bone):
    b = known_bone
    for _ in range(50):
        parent = str(subsystem.get_bone_parent(mesh, b))
        if parent in ("None", ""):
            return b
        b = parent
    return b


def walk_tree(mesh, root):
    flat = []

    def recurse(bone):
        flat.append(bone)
        for c in subsystem.get_bone_children(mesh, bone):
            recurse(str(c))

    recurse(root)
    return flat


root = find_root(target_mesh, "Neck")
proper_bones = walk_tree(target_mesh, root)
REPORT["proper_bone_count"] = len(proper_bones)

lower_to_proper = {b.lower(): b for b in proper_bones}
num_frames = unreal.AnimationLibrary.get_num_frames(anim)
THRESH_DEG = 90.0

controller = anim.get_editor_property("controller")
safe("open_bracket", lambda: controller.open_bracket("Despike jitter", True))

fixed_summary = {}

# 프레임당 한 번씩만 호출해서 전체 본 포즈를 한꺼번에 수집 (65 x 311 개별 호출 대신 311번)
valid_tracks = [t for t in track_names_lower if t in lower_to_proper]
REPORT["unmatched_tracks"] = [t for t in track_names_lower if t not in lower_to_proper]
proper_names_ordered = [lower_to_proper[t] for t in valid_tracks]

per_bone_transforms = {t: [] for t in valid_tracks}
for frame in range(num_frames):
    poses = unreal.AnimationLibrary.get_bone_poses_for_frame(anim, proper_names_ordered, frame, False, target_mesh)
    for track, t in zip(valid_tracks, poses):
        per_bone_transforms[track].append(t)

for track in valid_tracks:
    transforms = per_bone_transforms[track]
    rot = [t.rotation for t in transforms]
    pos = [t.translation for t in transforms]
    scale = [t.scale3d for t in transforms]

    deltas = [quat_angle_deg(rot[i], rot[i + 1]) for i in range(len(rot) - 1)]
    bad_frames = set()
    for i, d in enumerate(deltas):
        if d > THRESH_DEG:
            bad_frames.add(i)
            bad_frames.add(i + 1)
    if not bad_frames:
        continue

    sorted_bad = sorted(bad_frames)
    runs = []
    run_start = sorted_bad[0]
    prev = sorted_bad[0]
    for f in sorted_bad[1:]:
        if f == prev + 1:
            prev = f
        else:
            runs.append((run_start, prev))
            run_start = f
            prev = f
    runs.append((run_start, prev))

    new_rot = list(rot)
    for start, end in runs:
        before_ok = start > 0
        after_ok = end < num_frames - 1
        if before_ok and after_ok:
            anchor_before = rot[start - 1]
            anchor_after = rot[end + 1]
            span = (end + 1) - (start - 1)
            for f in range(start, end + 1):
                t = (f - (start - 1)) / span
                new_rot[f] = slerp(anchor_before, anchor_after, t)
        elif after_ok:
            anchor_after = rot[end + 1]
            for f in range(start, end + 1):
                new_rot[f] = anchor_after
        elif before_ok:
            anchor_before = rot[start - 1]
            for f in range(start, end + 1):
                new_rot[f] = anchor_before

    ok = safe(f"write_{track}", lambda track=track, pos=pos, new_rot=new_rot, scale=scale:
              controller.set_bone_track_keys(track, pos, new_rot, scale, True))
    fixed_summary[track] = {"runs": runs, "write_ok": ok}

safe("close_bracket", lambda: controller.close_bracket(True))
safe("save", lambda: unreal.EditorAssetLibrary.save_asset(anim_path))

REPORT["fixed_summary"] = fixed_summary
REPORT["num_tracks_fixed"] = len(fixed_summary)

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/24_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
