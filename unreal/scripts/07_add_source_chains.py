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


REPORT["help_add_retarget_chain"] = unreal.IKRigController.add_retarget_chain.__doc__
REPORT["help_set_retarget_root"] = unreal.IKRigController.set_retarget_root.__doc__

ikrig = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_IKRig")
controller = unreal.IKRigController.get_controller(ikrig)

safe("set_retarget_root", lambda: controller.set_retarget_root("Pelvis"))

NEW_CHAINS = [
    ("LeftLeg", "L_Hip", "L_Ankle"),
    ("LeftFoot", "L_Foot", "L_Foot"),
    ("LeftClavicle", "L_Collar", "L_Collar"),
    ("LeftArm", "L_Shoulder", "L_Hand"),
    ("RightLeg", "R_Hip", "R_Ankle"),
    ("RightFoot", "R_Foot", "R_Foot"),
    ("RightClavicle", "R_Collar", "R_Collar"),
    ("RightArm", "R_Shoulder", "R_Hand"),
]

for name, start, end in NEW_CHAINS:
    safe(f"add_chain_{name}", lambda name=name, start=start, end=end:
         controller.add_retarget_chain(name, start, end, "None"))

safe("save", lambda: unreal.EditorAssetLibrary.save_asset("/Game/Source/SMPL_Source_IKRig"))

# 최종 확인
final_chains = safe("final_chains", lambda: controller.get_retarget_chains())
if final_chains:
    summaries = []
    for c in final_chains:
        name = str(c.chain_name)
        start = str(controller.get_retarget_chain_start_bone(c.chain_name))
        end = str(controller.get_retarget_chain_end_bone(c.chain_name))
        summaries.append({"chain_name": name, "start_bone": start, "end_bone": end})
    REPORT["final_chain_summaries"] = summaries

REPORT["final_retarget_root"] = safe("final_root", lambda: str(controller.get_retarget_root()))

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/07_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
