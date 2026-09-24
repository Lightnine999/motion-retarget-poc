import unreal
import json

REPORT = {}
REPORT["help_run_batch_retarget"] = unreal.IKRetargetBatchOperation.run_batch_retarget.__doc__
REPORT["ik_retarget_batch_operation_inputs_dir"] = [a for a in dir(unreal.IKRetargetBatchOperationInputs) if not a.startswith("_")]

# 기본 인스턴스를 만들어서 존재하는 필드 확인
inst = unreal.IKRetargetBatchOperationInputs()
props = {}
for name in REPORT["ik_retarget_batch_operation_inputs_dir"]:
    try:
        v = inst.get_editor_property(name)
        props[name] = str(v)
    except Exception as e:
        pass
REPORT["default_instance_props"] = props

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/11_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
