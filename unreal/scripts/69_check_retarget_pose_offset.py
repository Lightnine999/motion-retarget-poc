import unreal
import json

retargeter = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")
controller = unreal.IKRetargeterController.get_controller(retargeter)

REPORT = {}
REPORT["help_get_rotation_offset"] = unreal.IKRetargeterController.get_rotation_offset_for_retarget_pose_bone.__doc__
REPORT["help_get_current_pose_name"] = unreal.IKRetargeterController.get_current_retarget_pose_name.__doc__
REPORT["current_pose_name_target"] = str(controller.get_current_retarget_pose_name(unreal.RetargetSourceOrTarget.TARGET))
REPORT["current_pose_name_source"] = str(controller.get_current_retarget_pose_name(unreal.RetargetSourceOrTarget.SOURCE))

TARGET_BONES = ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head", "LeftShoulder", "RightShoulder", "LeftArm", "RightArm"]
SOURCE_BONES = ["Pelvis", "Spine1", "Spine2", "Spine3", "Neck", "Head", "L_Collar", "R_Collar", "L_Shoulder", "R_Shoulder"]

for label, bones, sot in [("target", TARGET_BONES, unreal.RetargetSourceOrTarget.TARGET),
                          ("source", SOURCE_BONES, unreal.RetargetSourceOrTarget.SOURCE)]:
    offsets = {}
    for b in bones:
        try:
            q = controller.get_rotation_offset_for_retarget_pose_bone(b, sot)
            offsets[b] = [round(q.x, 3), round(q.y, 3), round(q.z, 3), round(q.w, 3)]
        except Exception as e:
            offsets[b] = f"ERR: {e}"
    REPORT[f"{label}_pose_rotation_offsets"] = offsets

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/69_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
