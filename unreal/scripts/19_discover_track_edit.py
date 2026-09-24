import unreal
import json

REPORT = {}
REPORT["help_set_bone_track_keys"] = unreal.AnimDataController.set_bone_track_keys.__doc__
REPORT["help_open_bracket"] = unreal.AnimDataController.open_bracket.__doc__
REPORT["help_close_bracket"] = unreal.AnimDataController.close_bracket.__doc__
REPORT["help_set_model"] = unreal.AnimDataController.set_model.__doc__

anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo")
REPORT["track_names"] = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(anim)]
REPORT["num_frames"] = unreal.AnimationLibrary.get_num_frames(anim)

rot_data = unreal.AnimationLibrary.get_raw_track_rotation_data(anim, "Neck")
pos_data = unreal.AnimationLibrary.get_raw_track_position_data(anim, "Neck")
scale_data = unreal.AnimationLibrary.get_raw_track_scale_data(anim, "Neck")
REPORT["neck_rot_data_len"] = len(rot_data)
REPORT["neck_pos_data_len"] = len(pos_data)
REPORT["neck_scale_data_len"] = len(scale_data)
REPORT["neck_rot_sample0"] = str(rot_data[0]) if rot_data else None
REPORT["neck_pos_sample0"] = str(pos_data[0]) if pos_data else None

controller = anim.get_editor_property("controller")
REPORT["controller_is_none"] = controller is None

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/19_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
