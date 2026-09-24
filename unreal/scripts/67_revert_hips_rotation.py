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


target_anim_path = "/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo_Clean"
target_anim = unreal.EditorAssetLibrary.load_asset(target_anim_path)
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

num_frames = unreal.AnimationLibrary.get_num_frames(target_anim)

target_hips_current = []
for f in range(num_frames):
    t = unreal.AnimationLibrary.get_bone_poses_for_frame(target_anim, ["Hips"], f, False, target_mesh)[0]
    target_hips_current.append(t)

pos = [t.translation for t in target_hips_current]
scale = [t.scale3d for t in target_hips_current]
ref_rot = unreal.Quat(-0.7071067811518649, 0.0, 0.0, 0.707106781151865)
new_rot = [ref_rot] * num_frames

controller = target_anim.get_editor_property("controller")
safe("open_bracket", lambda: controller.open_bracket("Revert Hips rotation to reference", True))
ok = safe("write_hips_rot", lambda: controller.set_bone_track_keys("hips", pos, new_rot, scale, True))
safe("close_bracket", lambda: controller.close_bracket(True))
safe("save", lambda: unreal.EditorAssetLibrary.save_asset(target_anim_path))

REPORT["write_ok"] = ok

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/67_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
