import unreal
import json

REPORT = {}
REPORT["help_get_ref_pose_transform_of_bone"] = unreal.IKRigController.get_ref_pose_transform_of_bone.__doc__

ikrig = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character_IKRig")
controller = unreal.IKRigController.get_controller(ikrig)

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/despiked_anim_dump.json") as f:
    dump = json.load(f)
bone_order = dump["bone_order"]

ref_pose = {}
for b in bone_order:
    t = controller.get_ref_pose_transform_of_bone(b)
    ref_pose[b] = {
        "q": [t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w],
        "p": [t.translation.x, t.translation.y, t.translation.z],
    }

REPORT["sample_hips"] = ref_pose.get(bone_order[0])
REPORT["sample_leftupleg"] = ref_pose.get("LeftUpLeg")
REPORT["sample_spine"] = ref_pose.get("Spine")

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/ref_pose_dump.json", "w") as f:
    json.dump(ref_pose, f)

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/32_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
