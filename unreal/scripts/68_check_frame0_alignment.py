import unreal
import json
import math

target_anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo_Clean")
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")
target_ikrig = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character_IKRig")
target_ikrig_controller = unreal.IKRigController.get_controller(target_ikrig)

BONES = ["Hips", "Spine", "Spine1", "Spine2", "LeftShoulder", "RightShoulder"]

# 프레임0 실제 값 (글로벌/컴포넌트 스페이스)
poses_f0 = unreal.AnimationLibrary.get_bone_poses_for_frame(target_anim, BONES, 0, False, target_mesh)

result = {}
for b, t in zip(BONES, poses_f0):
    q = t.rotation
    result[f"frame0_{b}"] = {"quat": [round(q.x,3), round(q.y,3), round(q.z,3), round(q.w,3)]}

# 레퍼런스(bind) 포즈 값
for b in BONES:
    t = target_ikrig_controller.get_ref_pose_transform_of_bone(b)
    q = t.rotation
    result[f"ref_{b}"] = {"quat": [round(q.x,3), round(q.y,3), round(q.z,3), round(q.w,3)]}


def quat_angle_deg(q1, q2):
    dot = abs(q1.x*q2.x+q1.y*q2.y+q1.z*q2.z+q1.w*q2.w)
    dot = min(1.0, max(-1.0, dot))
    return math.degrees(2*math.acos(dot))


# 프레임0 실제값 vs 레퍼런스값 차이(각도)
for b, t in zip(BONES, poses_f0):
    ref_t = target_ikrig_controller.get_ref_pose_transform_of_bone(b)
    diff = quat_angle_deg(t.rotation, ref_t.rotation)
    result[f"diff_from_ref_{b}"] = round(diff, 1)

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/68_report.json", "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
