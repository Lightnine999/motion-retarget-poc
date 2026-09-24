import unreal
import json
import traceback

REPORT = {}


def safe(label, fn):
    try:
        return fn()
    except Exception as e:
        REPORT[f"error_{label}"] = str(e)
        REPORT[f"traceback_{label}"] = traceback.format_exc()
        return None


def get_help(obj_or_func):
    try:
        return obj_or_func.__doc__
    except Exception as e:
        return f"ERROR: {e}"


# 주요 함수 시그니처(docstring) 확보
REPORT["help_apply_auto"] = get_help(unreal.IKRigController.apply_auto_generated_retarget_definition)
REPORT["help_set_skeletal_mesh"] = get_help(unreal.IKRigController.set_skeletal_mesh)
REPORT["help_get_root_bone"] = get_help(unreal.IKRigController.get_root_bone)
REPORT["help_get_retarget_chains"] = get_help(unreal.IKRigController.get_retarget_chains)
REPORT["help_get_controller"] = get_help(unreal.IKRigController.get_controller)
REPORT["help_bonechain_to_dict"] = get_help(unreal.BoneChain.to_dict)
REPORT["help_get_bone_children"] = get_help(unreal.SkeletalMeshEditorSubsystem.get_bone_children)
REPORT["help_get_bone_parent"] = get_help(unreal.SkeletalMeshEditorSubsystem.get_bone_parent)
REPORT["help_create_asset"] = get_help(unreal.AssetTools.create_asset)


def build_ikrig(mesh_path, dest_path, dest_name, key):
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)

    factory = unreal.IKRigDefinitionFactory()
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    existing_path = f"{dest_path}/{dest_name}"
    if unreal.EditorAssetLibrary.does_asset_exist(existing_path):
        ikrig_asset = unreal.EditorAssetLibrary.load_asset(existing_path)
    else:
        ikrig_asset = asset_tools.create_asset(dest_name, dest_path, unreal.IKRigDefinition, factory)
    REPORT[f"{key}_ikrig_asset_is_none"] = ikrig_asset is None

    controller = unreal.IKRigController.get_controller(ikrig_asset)
    controller.set_skeletal_mesh(mesh)

    root_bone = safe(f"{key}_get_retarget_root_before", lambda: str(controller.get_retarget_root()))
    REPORT[f"{key}_retarget_root_before_auto"] = root_bone

    auto_result = safe(f"{key}_apply_auto", lambda: controller.apply_auto_generated_retarget_definition())
    REPORT[f"{key}_apply_auto_result"] = str(auto_result)

    root_bone_after = safe(f"{key}_get_retarget_root_after", lambda: str(controller.get_retarget_root()))
    REPORT[f"{key}_retarget_root_after_auto"] = root_bone_after

    chains = safe(f"{key}_get_chains", lambda: controller.get_retarget_chains())
    if chains:
        chain_summaries = []
        for c in chains:
            name = safe(f"{key}_chain_name", lambda c=c: str(c.chain_name))
            start = safe(f"{key}_chain_start", lambda c=c: str(controller.get_retarget_chain_start_bone(c.chain_name)))
            end = safe(f"{key}_chain_end", lambda c=c: str(controller.get_retarget_chain_end_bone(c.chain_name)))
            goal = safe(f"{key}_chain_goal", lambda c=c: str(controller.get_retarget_chain_goal(c.chain_name)))
            chain_summaries.append({"chain_name": name, "start_bone": start, "end_bone": end, "ik_goal": goal})
        REPORT[f"{key}_chains"] = chain_summaries

    unreal.EditorAssetLibrary.save_asset(f"{dest_path}/{dest_name}")
    return ikrig_asset


safe("build_source_ikrig", lambda: build_ikrig(
    "/Game/Source/SMPL_Source.SMPL_Source", "/Game/Source", "SMPL_Source_IKRig", "source"))
safe("build_target_ikrig", lambda: build_ikrig(
    "/Game/Target/Mixamo_Character.Mixamo_Character", "/Game/Target", "Mixamo_Character_IKRig", "target"))

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/05_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
