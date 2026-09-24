import unreal
import json

retargeter = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")
controller = unreal.IKRetargeterController.get_controller(retargeter)

REPORT = {}

settings = controller.get_retarget_chain_settings("Spine")
REPORT["spine_settings_class"] = settings.get_class().get_name() if hasattr(settings, "get_class") else str(type(settings))
REPORT["spine_settings_dir"] = [a for a in dir(settings) if not a.startswith("_")]
try:
    REPORT["spine_settings_dict"] = settings.to_dict()
except Exception as e:
    REPORT["spine_settings_dict_err"] = str(e)

root_settings = controller.get_root_settings()
REPORT["root_settings_dir"] = [a for a in dir(root_settings) if not a.startswith("_")]
try:
    REPORT["root_settings_dict"] = root_settings.to_dict()
except Exception as e:
    REPORT["root_settings_dict_err"] = str(e)

global_settings = controller.get_global_settings()
REPORT["global_settings_dir"] = [a for a in dir(global_settings) if not a.startswith("_")]
try:
    REPORT["global_settings_dict"] = global_settings.to_dict()
except Exception as e:
    REPORT["global_settings_dict_err"] = str(e)

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/40_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
