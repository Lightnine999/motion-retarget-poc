import unreal
import json

REPORT = {}


def list_methods(cls_name):
    try:
        cls = getattr(unreal, cls_name)
        return [a for a in dir(cls) if not a.startswith("_")]
    except Exception as e:
        return f"ERROR: {e}"


for cls_name in [
    "EditorSkeletalMeshLibrary",
    "SkeletalMeshEditorSubsystem",
    "IKRigController",
    "IKRigDefinition",
    "IKRetargeterController",
    "IKRetargeter",
    "IKRetargetBatchOperation",
    "IKRigEffectorGoal",
    "RetargetChainSettings",
    "BoneChain",
]:
    REPORT[cls_name] = list_methods(cls_name)

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/04_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2)
