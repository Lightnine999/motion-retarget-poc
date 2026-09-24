import unreal
import json

REPORT = {}
REPORT["help_get_bone_poses_for_time"] = unreal.AnimationLibrary.get_bone_poses_for_time.__doc__
REPORT["help_get_bone_poses_for_frame"] = unreal.AnimationLibrary.get_bone_poses_for_frame.__doc__
REPORT["help_get_raw_track_rotation_data"] = unreal.AnimationLibrary.get_raw_track_rotation_data.__doc__
REPORT["help_get_animation_track_names"] = unreal.AnimationLibrary.get_animation_track_names.__doc__
REPORT["help_get_num_frames"] = unreal.AnimationLibrary.get_num_frames.__doc__

anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo")
REPORT["num_frames"] = unreal.AnimationLibrary.get_num_frames(anim)
REPORT["track_names"] = [str(n) for n in unreal.AnimationLibrary.get_animation_track_names(anim)]

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/14_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
