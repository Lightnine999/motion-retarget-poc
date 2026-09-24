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


anim_path = "/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo"
anim = unreal.EditorAssetLibrary.load_asset(anim_path)
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/despiked_anim_dump.json") as f:
    dump = json.load(f)

bone_order = dump["bone_order"]
num_frames = unreal.AnimationLibrary.get_num_frames(anim)
track_names_lower = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(anim)]
lower_to_proper = {b.lower(): b for b in bone_order}

controller = anim.get_editor_property("controller")
safe("open_bracket", lambda: controller.open_bracket("Restore original translation", True))

valid_tracks = [t for t in track_names_lower if t in lower_to_proper]
proper_names_ordered = [lower_to_proper[t] for t in valid_tracks]

# 프레임당 한 번씩만 호출 (현재 상태 = 회전은 despike 적용됨, 위치는 방금 잘못 덮어쓴 상태)
per_bone_current = {t: [] for t in valid_tracks}
for frame in range(num_frames):
    poses = unreal.AnimationLibrary.get_bone_poses_for_frame(anim, proper_names_ordered, frame, False, target_mesh)
    for track, t in zip(valid_tracks, poses):
        per_bone_current[track].append(t)

restored = []
for track in valid_tracks:
    proper_name = lower_to_proper[track]
    current_full = per_bone_current[track]
    rot = [t.rotation for t in current_full]
    scale = [t.scale3d for t in current_full]
    orig_pos = [unreal.Vector(*dump["frames"][f][proper_name]["p"]) for f in range(num_frames)]

    ok = safe(f"restore_{track}", lambda track=track, orig_pos=orig_pos, rot=rot, scale=scale:
              controller.set_bone_track_keys(track, orig_pos, rot, scale, True))
    restored.append({"track": track, "ok": ok})

safe("close_bracket", lambda: controller.close_bracket(True))
safe("save", lambda: unreal.EditorAssetLibrary.save_asset(anim_path))

REPORT["restored_count"] = len(restored)
REPORT["restored"] = restored

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/36_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
