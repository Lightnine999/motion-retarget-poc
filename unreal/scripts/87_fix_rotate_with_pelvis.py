"""
82/83/84/86 조사로 확정된 원인: Root Motion op의 rotate_with_pelvis=False 때문에
루트(=Hips, Mixamo는 별도 루트 본 없이 Hips가 곧 루트)가 실제 골반 회전을 따라가지
못하고 고정된 채로, 그 위의 Spine/Neck만 회전 -> 허리가 뒤틀려 보이는 시각 증상.
rotate_with_pelvis=True 로 바꾸고 재리타겟 + 회전 연속성 재검증한다.
"""
import unreal
import json

REPORT = {}

retargeter = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")
controller = unreal.IKRetargeterController.get_controller(retargeter)

rootmotion_op = controller.get_op_controller(3)
settings = rootmotion_op.get_settings()
REPORT["before_rotate_with_pelvis"] = str(settings.get_editor_property("rotate_with_pelvis"))

settings.set_editor_property("rotate_with_pelvis", True)
rootmotion_op.set_settings(settings)

settings_after = rootmotion_op.get_settings()
REPORT["after_rotate_with_pelvis"] = str(settings_after.get_editor_property("rotate_with_pelvis"))

unreal.EditorAssetLibrary.save_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")

# 재리타겟 (75번과 동일 패턴, 새 이름으로 저장해서 비교 가능하게)
anim_asset_data = unreal.EditorAssetLibrary.find_asset_data("/Game/Source/SMPL_Source_Anim")
source_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source")
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

inputs = unreal.IKRetargetBatchOperationInputs()
inputs.set_editor_property("assets_to_retarget", [anim_asset_data])
inputs.set_editor_property("ik_retarget_asset", retargeter)
inputs.set_editor_property("source_mesh", source_mesh)
inputs.set_editor_property("target_mesh", target_mesh)
inputs.set_editor_property("target_path", "/Game/Retarget/Animations")
inputs.set_editor_property("suffix", "_OnMixamo_FK_PelvisFix")
inputs.set_editor_property("overwrite_existing_files", True)

result = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
result_paths = []
target_anim_path = None
for ad in result or []:
    pkg = str(ad.get_editor_property("package_name"))
    unreal.EditorAssetLibrary.save_asset(pkg)
    result_paths.append(pkg)
    target_anim_path = pkg
REPORT["result_paths"] = result_paths

# 회전 연속성 재검증 (Hips 포함)
target_anim = unreal.EditorAssetLibrary.load_asset(target_anim_path)
BONES = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "LeftShoulder", "RightShoulder"]
num_frames = unreal.AnimationLibrary.get_num_frames(target_anim)


def quat_dot(a, b):
    return a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w


import math
series = {b: [] for b in BONES}
for f in range(num_frames):
    poses = unreal.AnimationLibrary.get_bone_poses_for_frame(target_anim, BONES, f, False, target_mesh)
    for b, t in zip(BONES, poses):
        series[b].append(t.rotation)

max_angle = {}
for b in BONES:
    rots = series[b]
    m = 0.0
    for i in range(1, len(rots)):
        d = max(-1.0, min(1.0, abs(quat_dot(rots[i - 1], rots[i]))))
        m = max(m, math.degrees(2 * math.acos(d)))
    max_angle[b] = round(m, 1)

REPORT["max_frame_to_frame_angle_deg_after_fix"] = max_angle

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/87_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)

print(json.dumps(REPORT, ensure_ascii=False, indent=2, default=str))
