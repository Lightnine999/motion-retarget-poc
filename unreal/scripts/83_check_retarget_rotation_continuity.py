"""
위치(translation) 변환은 완벽했다(81번 스크립트, Blender(X,-Y,Z)*100 == Unreal, sub-mm 오차).
이제 회전이 프레임마다 연속적인지(뒤틀림/불연속 없는지) 소스 애니메이션(SMPL_Source_Anim,
리타겟 이전)에서 전 프레임에 걸쳐 확인한다. 여기서 이미 불연속이 보이면 Blender->Unreal FBX
회전 변환 자체의 문제, 여기선 멀쩡한데 리타겟 결과(Mixamo)에서만 틀어지면 IK Retargeter
체인/포즈 설정 문제로 원인을 좁힐 수 있다.
"""
import unreal
import json
import math

REPORT = {}

source_anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo_FK")
source_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

BONES = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "LeftShoulder", "RightShoulder"]

num_frames = unreal.AnimationLibrary.get_num_frames(source_anim)
REPORT["num_frames"] = num_frames


def quat_dot(a, b):
    return a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w


series = {b: [] for b in BONES}
for f in range(num_frames):
    poses = unreal.AnimationLibrary.get_bone_poses_for_frame(source_anim, BONES, f, False, source_mesh)
    for b, t in zip(BONES, poses):
        series[b].append(t.rotation)

discontinuities = {}
max_frame_to_frame_angle = {}
for b in BONES:
    rots = series[b]
    issues = []
    max_angle = 0.0
    for i in range(1, len(rots)):
        d = quat_dot(rots[i - 1], rots[i])
        d = max(-1.0, min(1.0, abs(d)))
        angle_deg = math.degrees(2 * math.acos(d))
        max_angle = max(max_angle, angle_deg)
        if angle_deg > 25.0:  # 30fps에서 한 프레임에 25도 이상 튀면 이상 신호
            issues.append({"frame": i, "jump_deg": round(angle_deg, 1)})
    discontinuities[b] = issues[:10]
    max_frame_to_frame_angle[b] = round(max_angle, 1)

REPORT["discontinuities_over_25deg"] = discontinuities
REPORT["max_frame_to_frame_angle_deg"] = max_frame_to_frame_angle

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/83_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)

print(json.dumps(REPORT, ensure_ascii=False, indent=2, default=str))
