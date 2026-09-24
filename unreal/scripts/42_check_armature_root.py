import unreal
import json

source_anim = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_Anim")
source_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source")

check_frames = [0, 50, 100, 150, 200, 236, 266, 300, 310]
result = {}
for bone in ["SMPL_Armature", "Pelvis"]:
    result[bone] = []
    for f in check_frames:
        t = unreal.AnimationLibrary.get_bone_poses_for_frame(source_anim, [bone], f, False, source_mesh)[0]
        p = t.translation
        result[bone].append({"frame": f, "p": [p.x, p.y, p.z]})

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/42_report.json", "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
