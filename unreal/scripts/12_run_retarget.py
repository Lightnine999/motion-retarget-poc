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


anim_asset_data = unreal.EditorAssetLibrary.find_asset_data("/Game/Source/SMPL_Source_Anim")
retargeter = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")
source_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source")
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character")

REPORT["anim_asset_data_valid"] = anim_asset_data.is_valid() if anim_asset_data else False

inputs = unreal.IKRetargetBatchOperationInputs()
inputs.set_editor_property("assets_to_retarget", [anim_asset_data])
inputs.set_editor_property("ik_retarget_asset", retargeter)
inputs.set_editor_property("source_mesh", source_mesh)
inputs.set_editor_property("target_mesh", target_mesh)
inputs.set_editor_property("target_path", "/Game/Retarget/Animations")
inputs.set_editor_property("suffix", "_OnMixamo")
inputs.set_editor_property("overwrite_existing_files", True)

result = safe("run_batch_retarget", lambda: unreal.IKRetargetBatchOperation.run_batch_retarget(inputs))

result_paths = []
if result:
    for ad in result:
        entry = {"str": str(ad)}
        for prop in ["package_name", "asset_name", "object_path", "package_path"]:
            try:
                entry[prop] = str(ad.get_editor_property(prop))
            except Exception:
                pass
        pkg_name = entry.get("package_name")
        if pkg_name:
            saved = safe(f"save_{pkg_name}", lambda p=pkg_name: unreal.EditorAssetLibrary.save_asset(p))
            entry["saved"] = saved
        result_paths.append(entry)
REPORT["result_paths"] = result_paths
REPORT["result_count"] = len(result) if result else 0

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/12_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
