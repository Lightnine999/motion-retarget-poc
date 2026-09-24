import unreal
import json

REPORT = {}

REPORT["animation_library_full_dir"] = [a for a in dir(unreal.AnimationLibrary) if not a.startswith("_")]
REPORT["anim_data_controller_dir"] = [a for a in dir(unreal.AnimDataController) if not a.startswith("_")]

anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo")
try:
    model = anim.get_editor_property("data_model")
    REPORT["data_model_is_none"] = model is None
    if model:
        REPORT["data_model_dir"] = [a for a in dir(model) if not a.startswith("_")]
except Exception as e:
    REPORT["data_model_error"] = str(e)

REPORT["anim_top_level_dir"] = [a for a in dir(anim) if not a.startswith("_")]

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/18_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
