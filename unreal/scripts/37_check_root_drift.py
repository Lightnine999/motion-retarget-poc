import unreal
import json
import math

source_anim = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_Anim")
source_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source")
target_anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo")
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

check_frames = [0, 50, 100, 150, 200, 236, 266, 300, 310]

result = {"source_pelvis": [], "target_hips": []}
for f in check_frames:
    sp = unreal.AnimationLibrary.get_bone_poses_for_frame(source_anim, ["Pelvis"], f, False, source_mesh)[0]
    tp = unreal.AnimationLibrary.get_bone_poses_for_frame(target_anim, ["Hips"], f, False, target_mesh)[0]
    sp_t = sp.translation
    tp_t = tp.translation
    result["source_pelvis"].append({
        "frame": f,
        "p": [sp_t.x, sp_t.y, sp_t.z],
        "len": math.sqrt(sp_t.x**2 + sp_t.y**2 + sp_t.z**2),
    })
    result["target_hips"].append({
        "frame": f,
        "p": [tp_t.x, tp_t.y, tp_t.z],
        "len": math.sqrt(tp_t.x**2 + tp_t.y**2 + tp_t.z**2),
    })

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/37_report.json", "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
