import unreal
import json

retargeter = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")
controller = unreal.IKRetargeterController.get_controller(retargeter)

result = {}
for chain in ["Spine", "LeftLeg", "RightLeg", "Neck", "Head"]:
    settings = controller.get_retarget_chain_settings(chain)
    d = {}
    for prop in ["translation_mode", "rotation_mode", "static_offset", "static_local_offset",
                 "static_rotation_offset", "extension", "translation_alpha", "rotation_alpha", "source_chain"]:
        try:
            v = settings.get_editor_property(prop)
            d[prop] = str(v)
        except Exception as e:
            d[prop] = f"ERR: {e}"
    result[chain] = d

REPORT = {"chain_settings": result}

REPORT["global_settings"] = str(controller.get_global_settings())
REPORT["root_settings"] = str(controller.get_root_settings())

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/39_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
