import unreal
import json
import math

REPORT = {}


def quat_angle_deg(q1, q2):
    dot = abs(q1[0] * q2[0] + q1[1] * q2[1] + q1[2] * q2[2] + q1[3] * q2[3])
    dot = min(1.0, max(-1.0, dot))
    return math.degrees(2 * math.acos(dot))


def collect(anim, mesh, bones, num_frames):
    per_bone = {b: [] for b in bones}
    for frame in range(num_frames):
        poses = unreal.AnimationLibrary.get_bone_poses_for_frame(anim, bones, frame, False, mesh)
        for b, t in zip(bones, poses):
            q = t.rotation
            per_bone[b].append((q.x, q.y, q.z, q.w))
    return per_bone


def analyze(per_bone):
    out = {}
    for b, quats in per_bone.items():
        deltas = [quat_angle_deg(quats[i], quats[i + 1]) for i in range(len(quats) - 1)]
        spikes = [(i, round(d, 1)) for i, d in enumerate(deltas) if d > 90.0]
        out[b] = {
            "max": round(max(deltas), 1) if deltas else None,
            "mean": round(sum(deltas) / len(deltas), 1) if deltas else None,
            "all_spikes": spikes,
        }
    return out


# 리타겟 결과: 전체 스파이크 목록
target_anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo")
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")
TARGET_BONES = ["Neck", "LeftShoulder", "LeftArm", "LeftForeArm", "RightForeArm", "Spine2"]
n_target = unreal.AnimationLibrary.get_num_frames(target_anim)
REPORT["target_full"] = analyze(collect(target_anim, target_mesh, TARGET_BONES, n_target))

# 소스(SMPL) 원본: 같은 구간에 노이즈가 이미 있는지 확인
source_anim = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_Anim")
source_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source")
SOURCE_BONES = ["Neck", "L_Shoulder", "L_Elbow", "R_Elbow", "Spine3"]
n_source = unreal.AnimationLibrary.get_num_frames(source_anim)
REPORT["source_full"] = analyze(collect(source_anim, source_mesh, SOURCE_BONES, n_source))

REPORT["n_target_frames"] = n_target
REPORT["n_source_frames"] = n_source

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/17_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
