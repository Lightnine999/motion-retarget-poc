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


REPORT["help_set_ik_rig"] = getattr(unreal.IKRetargeterController, "set_ik_rig", None).__doc__ if hasattr(unreal.IKRetargeterController, "set_ik_rig") else "NO set_ik_rig"
REPORT["help_auto_map_chains"] = unreal.IKRetargeterController.auto_map_chains.__doc__
REPORT["help_get_controller"] = unreal.IKRetargeterController.get_controller.__doc__
REPORT["help_add_default_ops"] = unreal.IKRetargeterController.add_default_ops.__doc__
REPORT["help_duplicate_and_retarget"] = unreal.IKRetargetBatchOperation.duplicate_and_retarget.__doc__
REPORT["help_get_all_target_ik_rigs"] = unreal.IKRetargeterController.get_all_target_ik_rigs.__doc__
REPORT["retarget_source_or_target_members"] = [a for a in dir(unreal.RetargetSourceOrTarget) if not a.startswith("_")]

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
dest_path = "/Game/Retarget"
dest_name = "SMPL_to_Mixamo_Retargeter"
existing_path = f"{dest_path}/{dest_name}"

if unreal.EditorAssetLibrary.does_asset_exist(existing_path):
    retargeter = unreal.EditorAssetLibrary.load_asset(existing_path)
else:
    factory = unreal.IKRetargetFactory()
    retargeter = asset_tools.create_asset(dest_name, dest_path, unreal.IKRetargeter, factory)

REPORT["retargeter_is_none"] = retargeter is None

controller = safe("get_controller", lambda: unreal.IKRetargeterController.get_controller(retargeter))

source_ikrig = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_IKRig")
target_ikrig = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character_IKRig")

safe("set_ik_rig_source", lambda: controller.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, source_ikrig))
safe("set_ik_rig_target", lambda: controller.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, target_ikrig))
safe("add_default_ops", lambda: controller.add_default_ops())
safe("auto_map_chains", lambda: controller.auto_map_chains(unreal.AutoMapChainType.FUZZY, True))

safe("save", lambda: unreal.EditorAssetLibrary.save_asset(existing_path))

chain_settings = safe("get_all_chain_settings", lambda: controller.get_all_chain_settings())
if chain_settings:
    summaries = []
    for cs in chain_settings:
        target_chain = safe("target_chain_name", lambda cs=cs: str(cs.target_chain))
        source_chain = safe("source_chain_name", lambda cs=cs: str(cs.source_chain))
        summaries.append({"target_chain": target_chain, "source_chain": source_chain})
    REPORT["chain_mappings"] = summaries

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/08_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
