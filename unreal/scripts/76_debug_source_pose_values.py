import unreal
import json

REPORT = {}
source_anim = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_Anim")
source_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source")

bones = ["Pelvis", "L_Shoulder", "R_Shoulder", "L_Wrist", "R_Wrist", "Neck", "Head"]

out = []
for f in [0, 50, 100, 150, 200, 250, 300]:
    poses = unreal.AnimationLibrary.get_bone_poses_for_frame(source_anim, bones, f, False, source_mesh)
    entry = {"frame": f}
    for b, t in zip(bones, poses):
        entry[b] = {
            "loc": [t.translation.x, t.translation.y, t.translation.z],
            "rot": [t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w],
        }
    out.append(entry)

REPORT["full_precision"] = out
REPORT["help_get_bone_poses_for_frame"] = unreal.AnimationLibrary.get_bone_poses_for_frame.__doc__

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/76_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)

print("done")
