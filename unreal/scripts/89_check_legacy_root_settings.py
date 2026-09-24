import unreal
import json

REPORT = {}
retargeter = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")
controller = unreal.IKRetargeterController.get_controller(retargeter)

try:
    rs = controller.get_root_settings()
    props = {}
    for name in dir(rs):
        if name.startswith("_"):
            continue
        try:
            props[name] = str(rs.get_editor_property(name))
        except Exception:
            pass
    REPORT["legacy_root_settings"] = props
except Exception as e:
    REPORT["legacy_root_settings_err"] = str(e)

# Pelvis Motion op의 컨트롤러 자체(클래스) 프로퍼티도 settings 구조체 밖에 있는지 확인
pelvis_op = controller.get_op_controller(0)
REPORT["pelvis_op_direct_props"] = {}
for name in ["get_source_pelvis_bone", "get_target_pelvis_bone"]:
    fn = getattr(pelvis_op, name, None)
    if fn:
        try:
            REPORT["pelvis_op_direct_props"][name] = str(fn())
        except Exception as e:
            REPORT["pelvis_op_direct_props"][name] = f"ERR: {e}"

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/89_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
print(json.dumps(REPORT, ensure_ascii=False, indent=2, default=str))
