import unreal
import json
import math

source_anim = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_Anim")
source_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source")
target_anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo")
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

check_frames = [0, 50, 100, 150, 200, 230, 233, 234, 235, 236, 237, 238, 240, 266, 300, 310]

SOURCE_BONES = ["Spine1", "L_Hip", "R_Hip"]
TARGET_BONES = ["Spine", "LeftUpLeg", "RightUpLeg"]

result = {"source": {}, "target": {}}
for b in SOURCE_BONES:
    result["source"][b] = []
    for f in check_frames:
        t = unreal.AnimationLibrary.get_bone_poses_for_frame(source_anim, [b], f, False, source_mesh)[0]
        p = t.translation
        result["source"][b].append({"frame": f, "len": math.sqrt(p.x**2 + p.y**2 + p.z**2)})

for b in TARGET_BONES:
    result["target"][b] = []
    for f in check_frames:
        t = unreal.AnimationLibrary.get_bone_poses_for_frame(target_anim, [b], f, False, target_mesh)[0]
        p = t.translation
        result["target"][b].append({"frame": f, "len": math.sqrt(p.x**2 + p.y**2 + p.z**2)})

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/38_report.json", "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
