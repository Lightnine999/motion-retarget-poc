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

num_frames = unreal.AnimationLibrary.get_num_frames(anim)

transforms = []
for frame in range(num_frames):
    t = unreal.AnimationLibrary.get_bone_poses_for_frame(anim, ["Hips"], frame, False, target_mesh)[0]
    transforms.append(t)

rot = [t.rotation for t in transforms]
scale = [t.scale3d for t in transforms]
pos_before = [t.translation for t in transforms]

SCALE_FACTOR = 100.0
pos_after = [unreal.Vector(p.x * SCALE_FACTOR, p.y * SCALE_FACTOR, p.z * SCALE_FACTOR) for p in pos_before]

REPORT["pos_before_sample"] = [[round(p.x, 3), round(p.y, 3), round(p.z, 3)] for p in pos_before[::50]]
REPORT["pos_after_sample"] = [[round(p.x, 1), round(p.y, 1), round(p.z, 1)] for p in pos_after[::50]]

controller = anim.get_editor_property("controller")
safe("open_bracket", lambda: controller.open_bracket("Fix Hips translation scale x100", True))
ok = safe("write_hips", lambda: controller.set_bone_track_keys("hips", pos_after, rot, scale, True))
safe("close_bracket", lambda: controller.close_bracket(True))
safe("save", lambda: unreal.EditorAssetLibrary.save_asset(anim_path))

REPORT["write_ok"] = ok

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/43_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
