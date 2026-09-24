import unreal
import json

REPORT = {}

names = [n for n in dir(unreal) if "AnimData" in n or n == "AnimationLibrary"]
REPORT["candidate_classes"] = names

anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo")
REPORT["anim_dir_pose_related"] = [a for a in dir(anim) if not a.startswith("_") and
                                    any(k in a.lower() for k in ["pose", "bone", "frame", "model", "data"])]

try:
    model = anim.get_editor_property("data_model")
    REPORT["data_model_dir"] = [a for a in dir(model) if not a.startswith("_")]
except Exception as e:
    REPORT["data_model_error"] = str(e)

REPORT["animation_library_dir"] = [a for a in dir(unreal.AnimationLibrary) if not a.startswith("_")] if hasattr(unreal, "AnimationLibrary") else "NO AnimationLibrary"

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/13_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
