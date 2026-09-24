import unreal
import json
import math

anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo_Clean")
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

BONES = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head"]
num_frames = unreal.AnimationLibrary.get_num_frames(anim)

per_bone_quats = {b: [] for b in BONES}
for frame in range(num_frames):
    poses = unreal.AnimationLibrary.get_bone_poses_for_frame(anim, BONES, frame, False, target_mesh)
    for b, t in zip(BONES, poses):
        q = t.rotation
        per_bone_quats[b].append((q.x, q.y, q.z, q.w))


def quat_angle_deg(q1, q2):
    dot = abs(q1[0]*q2[0]+q1[1]*q2[1]+q1[2]*q2[2]+q1[3]*q2[3])
    dot = min(1.0, max(-1.0, dot))
    return math.degrees(2*math.acos(dot))


results = {}
for b in BONES:
    quats = per_bone_quats[b]
    deltas = [quat_angle_deg(quats[i], quats[i+1]) for i in range(len(quats)-1)]
    spikes = [(i, round(d, 1)) for i, d in enumerate(deltas) if d > 60.0]
    results[b] = {
        "max": round(max(deltas), 1),
        "mean": round(sum(deltas)/len(deltas), 2),
        "num_spikes_over_60": len(spikes),
        "spikes": spikes[:20],
    }

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/63_report.json", "w") as f:
    json.dump({"num_frames": num_frames, "results": results}, f, ensure_ascii=False, indent=2)
