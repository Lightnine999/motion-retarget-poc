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


anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo")
source_anim = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_Anim")

REPORT["retargeted_seq_length"] = safe("seq_len", lambda: unreal.AnimationLibrary.get_sequence_length(anim))
REPORT["source_seq_length"] = safe("src_seq_len", lambda: unreal.AnimationLibrary.get_sequence_length(source_anim))
REPORT["retargeted_num_frames_prop"] = safe("frames_prop", lambda: anim.get_editor_property("number_of_sampled_frames"))
REPORT["retargeted_num_frames_lib"] = safe("frames_lib", lambda: unreal.AnimationLibrary.get_num_frames(anim))
REPORT["retargeted_target_skeleton"] = safe("skel", lambda: str(anim.get_editor_property("skeleton").get_name()))

# 본 포즈 직접 샘플링 시도 (Neck, LeftArm 기준)
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")
for bone in ["Neck", "LeftArm", "Hips"]:
    pose = safe(f"pose_{bone}_t0", lambda bone=bone: unreal.AnimationLibrary.get_bone_poses_for_time(
        anim, [bone], 0.0, False, target_mesh))
    if pose:
        t = pose[0]
        REPORT[f"pose_{bone}_t0"] = {
            "translation": str(t.translation),
            "rotation": str(t.rotation),
        }

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/15_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
