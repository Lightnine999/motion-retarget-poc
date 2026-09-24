import unreal
import json

REPORT = {}

anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo")
controller = anim.get_editor_property("controller")
model = controller.get_model_interface()

REPORT["get_num_bone_tracks"] = model.get_num_bone_tracks()
REPORT["get_bone_track_names"] = [str(n) for n in model.get_bone_track_names()]
REPORT["get_number_of_frames"] = model.get_number_of_frames()
REPORT["get_number_of_keys"] = model.get_number_of_keys()

REPORT["help_get_bone_track_by_name"] = model.get_bone_track_by_name.__doc__

try:
    t = model.get_bone_track_by_name("neck")
    REPORT["neck_track_str"] = str(t)
    REPORT["neck_track_dir"] = [a for a in dir(t) if not a.startswith("_")]
    REPORT["neck_track_dict"] = t.to_dict() if hasattr(t, "to_dict") else None
except Exception as e:
    REPORT["neck_track_error"] = str(e)

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/23_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
