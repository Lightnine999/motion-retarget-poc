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


REPORT["help_get_source_chain"] = unreal.IKRetargeterController.get_source_chain.__doc__
REPORT["help_get_num_retarget_ops"] = unreal.IKRetargeterController.get_num_retarget_ops.__doc__
REPORT["help_get_op_name"] = unreal.IKRetargeterController.get_op_name.__doc__
REPORT["help_get_retarget_op_enabled"] = unreal.IKRetargeterController.get_retarget_op_enabled.__doc__

retargeter = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")
controller = unreal.IKRetargeterController.get_controller(retargeter)

num_ops = safe("num_ops", lambda: controller.get_num_retarget_ops())
REPORT["num_ops"] = num_ops

op_names = []
if num_ops:
    for i in range(num_ops):
        n = safe(f"op_name_{i}", lambda i=i: str(controller.get_op_name(i)))
        op_names.append(n)
REPORT["op_names"] = op_names

target_ikrig = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character_IKRig")
target_controller = unreal.IKRigController.get_controller(target_ikrig)
target_chains = safe("target_chains_for_check", lambda: target_controller.get_retarget_chains())

mappings = []
if target_chains:
    for c in target_chains:
        tname = str(c.chain_name)
        src = safe(f"source_for_{tname}", lambda tname=tname: str(controller.get_source_chain(tname)))
        mappings.append({"target_chain": tname, "source_chain": src})
REPORT["mappings"] = mappings

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/09_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
