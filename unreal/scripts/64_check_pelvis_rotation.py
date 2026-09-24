import unreal
import json
import math

source_anim = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_Anim")
source_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source")
target_anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo_Clean")
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

num_frames = unreal.AnimationLibrary.get_num_frames(source_anim)


def quat_angle_deg(q1, q2):
    dot = abs(q1.x*q2.x+q1.y*q2.y+q1.z*q2.z+q1.w*q2.w)
    dot = min(1.0, max(-1.0, dot))
    return math.degrees(2*math.acos(dot))


source_quats = []
target_quats = []
for f in range(num_frames):
    sp = unreal.AnimationLibrary.get_bone_poses_for_frame(source_anim, ["Pelvis"], f, False, source_mesh)[0]
    tp = unreal.AnimationLibrary.get_bone_poses_for_frame(target_anim, ["Hips"], f, False, target_mesh)[0]
    source_quats.append(sp.rotation)
    target_quats.append(tp.rotation)

source_deltas = [quat_angle_deg(source_quats[i], source_quats[i+1]) for i in range(num_frames-1)]
target_deltas = [quat_angle_deg(target_quats[i], target_quats[i+1]) for i in range(num_frames-1)]

# 절대 회전량 변화폭도 체크 (frame0 대비)
source_vs_first = [quat_angle_deg(source_quats[0], q) for q in source_quats]
target_vs_first = [quat_angle_deg(target_quats[0], q) for q in target_quats]

result = {
    "source_pelvis_delta_max": round(max(source_deltas), 2),
    "source_pelvis_delta_mean": round(sum(source_deltas)/len(source_deltas), 2),
    "source_pelvis_range_from_frame0_max": round(max(source_vs_first), 2),
    "target_hips_delta_max": round(max(target_deltas), 2),
    "target_hips_delta_mean": round(sum(target_deltas)/len(target_deltas), 2),
    "target_hips_range_from_frame0_max": round(max(target_vs_first), 2),
    "source_pelvis_quat_samples": [[round(v, 3) for v in [q.x, q.y, q.z, q.w]] for q in source_quats[::50]],
    "target_hips_quat_samples": [[round(v, 3) for v in [q.x, q.y, q.z, q.w]] for q in target_quats[::50]],
}

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/64_report.json", "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
