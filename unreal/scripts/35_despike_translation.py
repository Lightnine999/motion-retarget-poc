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


def vec_sub(a, b):
    return (a.x - b.x, a.y - b.y, a.z - b.z)


def vec_len(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def vec_lerp(a, b, t):
    return unreal.Vector(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.z + (b.z - a.z) * t)


anim_path = "/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo"
anim = unreal.EditorAssetLibrary.load_asset(anim_path)
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")
subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)


def find_root(mesh, known_bone):
    b = known_bone
    for _ in range(50):
        parent = str(subsystem.get_bone_parent(mesh, b))
        if parent in ("None", ""):
            return b
        b = parent
    return b


def walk_tree(mesh, root):
    order = []

    def recurse(bone):
        order.append(bone)
        for c in subsystem.get_bone_children(mesh, bone):
            recurse(str(c))

    recurse(root)
    return order


root = find_root(target_mesh, "Neck")
bone_order = walk_tree(target_mesh, root)
num_frames = unreal.AnimationLibrary.get_num_frames(anim)

# 프레임당 한번씩 전체 본 포즈 수집
per_bone_transforms = {b: [] for b in bone_order}
for frame in range(num_frames):
    poses = unreal.AnimationLibrary.get_bone_poses_for_frame(anim, bone_order, frame, False, target_mesh)
    for b, t in zip(bone_order, poses):
        per_bone_transforms[b].append(t)

track_names_lower = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(anim)]
lower_to_proper = {b.lower(): b for b in bone_order}

POS_THRESH = 100.0  # cm, 한 프레임 사이 100cm(1m) 이상 순간이동하면 의심

controller = anim.get_editor_property("controller")
safe("open_bracket", lambda: controller.open_bracket("Despike translation", True))

fixed_summary = {}

for track in track_names_lower:
    proper_name = lower_to_proper.get(track)
    if not proper_name:
        continue
    transforms = per_bone_transforms[proper_name]
    rot = [t.rotation for t in transforms]
    pos = [t.translation for t in transforms]
    scale = [t.scale3d for t in transforms]

    deltas = [vec_len(vec_sub(pos[i + 1], pos[i])) for i in range(len(pos) - 1)]
    bad_frames = set()
    for i, d in enumerate(deltas):
        if d > POS_THRESH:
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

    new_pos = list(pos)
    for start, end in runs:
        before_ok = start > 0
        after_ok = end < num_frames - 1
        if before_ok and after_ok:
            anchor_before = pos[start - 1]
            anchor_after = pos[end + 1]
            span = (end + 1) - (start - 1)
            for f in range(start, end + 1):
                t = (f - (start - 1)) / span
                new_pos[f] = vec_lerp(anchor_before, anchor_after, t)
        elif after_ok:
            for f in range(start, end + 1):
                new_pos[f] = pos[end + 1]
        elif before_ok:
            for f in range(start, end + 1):
                new_pos[f] = pos[start - 1]

    ok = safe(f"write_{track}", lambda track=track, new_pos=new_pos, rot=rot, scale=scale:
              controller.set_bone_track_keys(track, new_pos, rot, scale, True))
    fixed_summary[track] = {"runs": runs, "write_ok": ok, "max_delta": max(deltas)}

safe("close_bracket", lambda: controller.close_bracket(True))
safe("save", lambda: unreal.EditorAssetLibrary.save_asset(anim_path))

REPORT["fixed_summary"] = fixed_summary
REPORT["num_tracks_fixed"] = len(fixed_summary)

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/35_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
