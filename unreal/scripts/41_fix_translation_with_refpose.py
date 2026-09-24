import unreal
import json
import traceback

REPORT = {}


def safe(label, fn):
    try:
        return fn()
    except Exception as e:
        REPORT[f"error_{label}"] = str(e)
        REPORT[f"traceback_{label}"] = traceback.format_exc()
        return None


def quat_conj(q):
    return (-q[0], -q[1], -q[2], q[3])


def rotate_vec_by_quat(q, v):
    qx, qy, qz, qw = q
    vx, vy, vz = v
    uvx = qy * vz - qz * vy
    uvy = qz * vx - qx * vz
    uvz = qx * vy - qy * vx
    uuvx = qy * uvz - qz * uvy
    uuvy = qz * uvx - qx * uvz
    uuvz = qx * uvy - qy * uvx
    return (
        vx + 2.0 * (qw * uvx + uuvx),
        vy + 2.0 * (qw * uvy + uuvy),
        vz + 2.0 * (qw * uvz + uuvz),
    )


anim_path = "/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo"
anim = unreal.EditorAssetLibrary.load_asset(anim_path)
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")
subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/despiked_anim_dump.json") as f:
    dump = json.load(f)
with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/ref_pose_dump.json") as f:
    ref_pose = json.load(f)

bone_order = dump["bone_order"]
bone_parents = dump["bone_parents"]
root_bone = bone_order[0]

# 레퍼런스 포즈 로컬 트랜슬레이션 계산 (컴포넌트 스페이스 -> 로컬)
ref_local_pos = {}
for b in bone_order:
    parent = bone_parents.get(b)
    if parent is None or parent not in ref_pose:
        ref_local_pos[b] = tuple(ref_pose[b]["p"])
        continue
    pq = ref_pose[parent]["q"]
    pp = ref_pose[parent]["p"]
    cp = ref_pose[b]["p"]
    delta = (cp[0] - pp[0], cp[1] - pp[1], cp[2] - pp[2])
    local = rotate_vec_by_quat(quat_conj(tuple(pq)), delta)
    ref_local_pos[b] = local

REPORT["ref_local_pos_sample"] = {b: ref_local_pos[b] for b in ["Hips", "Spine", "LeftUpLeg", "RightUpLeg", "Neck"]}

num_frames = unreal.AnimationLibrary.get_num_frames(anim)
track_names_lower = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(anim)]
lower_to_proper = {b.lower(): b for b in bone_order}

controller = anim.get_editor_property("controller")
safe("open_bracket", lambda: controller.open_bracket("Fix translation with ref pose", True))

valid_tracks = [t for t in track_names_lower if t in lower_to_proper]
proper_names_ordered = [lower_to_proper[t] for t in valid_tracks]

per_bone_current = {t: [] for t in valid_tracks}
for frame in range(num_frames):
    poses = unreal.AnimationLibrary.get_bone_poses_for_frame(anim, proper_names_ordered, frame, False, target_mesh)
    for track, t in zip(valid_tracks, poses):
        per_bone_current[track].append(t)

fixed = []
for track in valid_tracks:
    proper_name = lower_to_proper[track]
    if proper_name == root_bone:
        continue  # 루트(Hips)는 건드리지 않음
    current_full = per_bone_current[track]
    rot = [t.rotation for t in current_full]
    scale = [t.scale3d for t in current_full]
    lp = ref_local_pos[proper_name]
    new_pos = [unreal.Vector(lp[0], lp[1], lp[2])] * num_frames

    ok = safe(f"fix_{track}", lambda track=track, new_pos=new_pos, rot=rot, scale=scale:
              controller.set_bone_track_keys(track, new_pos, rot, scale, True))
    fixed.append({"track": track, "ok": ok, "local_pos": lp})

safe("close_bracket", lambda: controller.close_bracket(True))
safe("save", lambda: unreal.EditorAssetLibrary.save_asset(anim_path))

REPORT["fixed_count"] = len(fixed)
REPORT["fixed"] = fixed

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/41_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
