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


source_anim = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_Anim")
source_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source")

target_anim_path = "/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo"
target_anim = unreal.EditorAssetLibrary.load_asset(target_anim_path)
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

num_frames = unreal.AnimationLibrary.get_num_frames(target_anim)
SCALE_FACTOR = 100.0

source_pelvis_pos = []
for frame in range(num_frames):
    t = unreal.AnimationLibrary.get_bone_poses_for_frame(source_anim, ["Pelvis"], frame, False, source_mesh)[0]
    p = t.translation
    source_pelvis_pos.append(unreal.Vector(p.x * SCALE_FACTOR, p.y * SCALE_FACTOR, p.z * SCALE_FACTOR))

target_hips_current = []
for frame in range(num_frames):
    t = unreal.AnimationLibrary.get_bone_poses_for_frame(target_anim, ["Hips"], frame, False, target_mesh)[0]
    target_hips_current.append(t)

rot = [t.rotation for t in target_hips_current]
scale = [t.scale3d for t in target_hips_current]

REPORT["source_pelvis_scaled_sample"] = [[round(v.x, 1), round(v.y, 1), round(v.z, 1)] for v in source_pelvis_pos[::50]]

controller = target_anim.get_editor_property("controller")
safe("open_bracket", lambda: controller.open_bracket("Transfer root motion from source Pelvis", True))
ok = safe("write_hips", lambda: controller.set_bone_track_keys("hips", source_pelvis_pos, rot, scale, True))
safe("close_bracket", lambda: controller.close_bracket(True))
safe("save", lambda: unreal.EditorAssetLibrary.save_asset(target_anim_path))

REPORT["write_ok"] = ok

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/44_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
