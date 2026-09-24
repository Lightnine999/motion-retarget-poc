import unreal
import json

REPORT = {}

anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo")
controller = anim.get_editor_property("controller")

model = controller.get_model_interface()
REPORT["model_is_none"] = model is None
if model:
    REPORT["model_dir"] = [a for a in dir(model) if not a.startswith("_")]

    for method_name in ["get_bone_animation_tracks", "get_bone_animation_track", "get_number_of_keys", "get_number_of_frames"]:
        if hasattr(model, method_name):
            REPORT[f"help_{method_name}"] = getattr(model, method_name).__doc__

    tracks = None
    if hasattr(model, "get_bone_animation_tracks"):
        tracks = model.get_bone_animation_tracks()
        REPORT["num_bone_tracks_from_model"] = len(tracks) if tracks else 0
        if tracks:
            t0 = tracks[0]
            REPORT["track0_dir"] = [a for a in dir(t0) if not a.startswith("_")]
            REPORT["track0_dict"] = t0.to_dict() if hasattr(t0, "to_dict") else None

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/22_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
