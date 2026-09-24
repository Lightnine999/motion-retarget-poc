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


REPORT["help_set_source_chain"] = unreal.IKRetargeterController.set_source_chain.__doc__

retargeter = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")
controller = unreal.IKRetargeterController.get_controller(retargeter)

FINGER_CHAINS = [
    "LeftThumb", "LeftIndex", "LeftMiddle", "LeftRing", "LeftPinky",
    "RightThumb", "RightIndex", "RightMiddle", "RightRing", "RightPinky",
]

for name in FINGER_CHAINS:
    safe(f"clear_{name}", lambda name=name: controller.set_source_chain("None", name))

safe("save", lambda: unreal.EditorAssetLibrary.save_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter"))

target_ikrig = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character_IKRig")
target_controller = unreal.IKRigController.get_controller(target_ikrig)
target_chains = safe("target_chains_for_check", lambda: target_controller.get_retarget_chains())

mappings = []
if target_chains:
    for c in target_chains:
        tname = str(c.chain_name)
        src = safe(f"source_for_{tname}", lambda tname=tname: str(controller.get_source_chain(tname)))
        mappings.append({"target_chain": tname, "source_chain": src})
REPORT["mappings_after_fix"] = mappings

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/10_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
