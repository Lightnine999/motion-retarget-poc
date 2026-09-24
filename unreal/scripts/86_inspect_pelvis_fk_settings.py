import unreal
import json

REPORT = {}

retargeter = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")
controller = unreal.IKRetargeterController.get_controller(retargeter)

pelvis_op = controller.get_op_controller(0)
fk_op = controller.get_op_controller(1)
ikrig_op = controller.get_op_controller(2)
rootmotion_op = controller.get_op_controller(3)


def dump_settings(op, label):
    try:
        settings = op.get_settings()
        REPORT[f"{label}_settings_class"] = str(type(settings))
        props = {}
        for name in dir(settings):
            if name.startswith("_"):
                continue
            try:
                val = settings.get_editor_property(name)
                props[name] = str(val)
            except Exception:
                pass
        REPORT[f"{label}_settings_props"] = props
    except Exception as e:
        REPORT[f"{label}_settings_err"] = str(e)


dump_settings(pelvis_op, "pelvis")
dump_settings(fk_op, "fk")
dump_settings(ikrig_op, "ikrig")
dump_settings(rootmotion_op, "rootmotion")

REPORT["pelvis_source_bone"] = str(pelvis_op.get_source_pelvis_bone())
REPORT["pelvis_target_bone"] = str(pelvis_op.get_target_pelvis_bone())
REPORT["rootmotion_source_root_bone"] = str(rootmotion_op.get_source_root_bone())
REPORT["rootmotion_target_root_bone"] = str(rootmotion_op.get_target_root_bone())
REPORT["rootmotion_target_pelvis_bone"] = str(rootmotion_op.get_target_pelvis_bone())

# FK 체인 설정이 fk_op의 settings 안에 배열로 들어있는지 확인 (chain_settings 등 키)
with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/86_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)

print(json.dumps(REPORT, ensure_ascii=False, indent=2, default=str))
