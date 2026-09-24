import unreal
import json
import math

REPORT = {}

retargeter = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")
controller = unreal.IKRetargeterController.get_controller(retargeter)

# FK Chains op 찾기
num_ops = controller.get_num_retarget_ops()
op_names = [str(controller.get_op_name(i)) for i in range(num_ops)]
REPORT["op_names"] = op_names

fk_op_index = op_names.index("FK Chains") if "FK Chains" in op_names else None
REPORT["fk_op_index"] = fk_op_index

if fk_op_index is not None:
    op_controller = controller.get_op_controller(fk_op_index)
    REPORT["fk_op_controller_dir"] = [a for a in dir(op_controller) if not a.startswith("_")]

# 소스/타겟 Spine 계열 본 정적 정렬 비교 (프레임 0 vs 프레임 150에서 로컬 회전 크기)
source_anim = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_Anim")
source_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source")
target_anim = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo_Clean")
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

for f in [0, 50, 150, 250]:
    for name, anim, mesh, bones in [
        ("source", source_anim, source_mesh, ["Spine1", "Spine2", "Spine3"]),
        ("target", target_anim, target_mesh, ["Spine", "Spine1", "Spine2"]),
    ]:
        poses = unreal.AnimationLibrary.get_bone_poses_for_frame(anim, bones, f, False, mesh)
        for b, t in zip(bones, poses):
            q = t.rotation
            # 회전축(로컬) 정보: quaternion에서 회전각과 축 추출
            angle = 2 * math.acos(min(1.0, max(-1.0, q.w)))
            s = math.sqrt(max(0.0, 1 - q.w * q.w))
            axis = (q.x / s, q.y / s, q.z / s) if s > 1e-6 else (0, 0, 0)
            REPORT.setdefault(f"frame_{f}", {})[f"{name}_{b}"] = {
                "quat": [round(q.x, 3), round(q.y, 3), round(q.z, 3), round(q.w, 3)],
                "angle_deg": round(math.degrees(angle), 1),
                "axis": [round(a, 3) for a in axis],
            }

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/62_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
