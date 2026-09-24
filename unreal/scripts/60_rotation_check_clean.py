import unreal
import json
import math

REPORT = {}

anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo_Clean")
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

BONES = ["Neck", "LeftShoulder", "LeftArm", "LeftForeArm", "RightShoulder", "RightArm", "RightForeArm", "Spine2"]
num_frames = unreal.AnimationLibrary.get_num_frames(anim)

# frame별 각 본의 쿼터니언 수집 (component space)
per_bone_quats = {b: [] for b in BONES}
for frame in range(num_frames):
    poses = unreal.AnimationLibrary.get_bone_poses_for_frame(anim, BONES, frame, False, target_mesh)
    for b, t in zip(BONES, poses):
        q = t.rotation
        per_bone_quats[b].append((q.x, q.y, q.z, q.w))


def quat_angle_deg(q1, q2):
    dot = abs(q1[0] * q2[0] + q1[1] * q2[1] + q1[2] * q2[2] + q1[3] * q2[3])
    dot = min(1.0, max(-1.0, dot))
    return math.degrees(2 * math.acos(dot))


results = {}
for b in BONES:
    quats = per_bone_quats[b]
    deltas = [quat_angle_deg(quats[i], quats[i + 1]) for i in range(len(quats) - 1)]
    spikes = [(i, d) for i, d in enumerate(deltas) if d > 90.0]
    results[b] = {
        "max_delta_deg": max(deltas) if deltas else None,
        "mean_delta_deg": sum(deltas) / len(deltas) if deltas else None,
        "num_frames_over_90deg": len(spikes),
        "first_5_spikes": spikes[:5],
    }

REPORT["num_frames"] = num_frames
REPORT["per_bone_jitter"] = results

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/60_rotation_check.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
