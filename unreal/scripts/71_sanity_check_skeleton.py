import unreal
import json
import math

target_anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo_Clean")
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

# 컴포넌트 스페이스 위치를 직접 확보 (회전이 아니라 실제 3D 위치로 본 길이/방향 검증)
CHAIN = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head", "HeadTop_End"]
LR_CHECK = [("LeftShoulder", "RightShoulder"), ("LeftHand", "RightHand"), ("LeftFoot", "RightFoot")]


def vec_len(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


def analyze_frame(frame):
    all_bones = CHAIN + [b for pair in LR_CHECK for b in pair]
    poses = unreal.AnimationLibrary.get_bone_poses_for_frame(target_anim, all_bones, frame, False, target_mesh)
    pos = {b: t.translation for b, t in zip(all_bones, poses)}

    result = {"frame": frame}
    # 척추 체인 세그먼트 길이 (인접 관절 간 거리, cm)
    seg_lengths = {}
    for i in range(len(CHAIN) - 1):
        a, b = CHAIN[i], CHAIN[i + 1]
        seg_lengths[f"{a}-{b}"] = round(vec_len(pos[a], pos[b]), 1)
    result["segment_lengths_cm"] = seg_lengths

    # Hips -> Head 전체 수직 상승량 (Z 증가폭). 정상 서있는/움직이는 사람이면 대체로 양수여야 함
    result["hips_to_head_z_diff"] = round(pos["Head"].z - pos["Hips"].z, 1)
    result["hips_z"] = round(pos["Hips"].z, 1)
    result["head_z"] = round(pos["Head"].z, 1)

    # 좌우 대칭 체크 (완전히 겹치거나 반대로 뒤집히면 이상 신호)
    for left, right in LR_CHECK:
        result[f"{left}_to_{right}_dist"] = round(vec_len(pos[left], pos[right]), 1)

    return result


REPORT = {}
for f in [0, 7, 59, 88, 150, 230, 310]:
    REPORT[f"frame_{f}"] = analyze_frame(f)

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/71_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2)
