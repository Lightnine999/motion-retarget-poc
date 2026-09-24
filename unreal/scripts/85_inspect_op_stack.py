import unreal
import json

REPORT = {}

retargeter = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")
controller = unreal.IKRetargeterController.get_controller(retargeter)

num_ops = controller.get_num_retarget_ops()
REPORT["num_ops"] = num_ops

ops = []
for i in range(num_ops):
    entry = {"index": i}
    try:
        entry["name"] = str(controller.get_op_name(i))
    except Exception as e:
        entry["name_err"] = str(e)
    try:
        entry["enabled"] = controller.get_retarget_op_enabled(i)
    except Exception as e:
        entry["enabled_err"] = str(e)
    try:
        op_ctrl = controller.get_op_controller(i)
        entry["op_controller_class"] = str(type(op_ctrl))
        entry["op_controller_dir"] = sorted([a for a in dir(op_ctrl) if not a.startswith("_")])
    except Exception as e:
        entry["op_controller_err"] = str(e)
    ops.append(entry)

REPORT["ops"] = ops

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/85_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)

print(json.dumps(REPORT, ensure_ascii=False, indent=2, default=str)[:6000])
