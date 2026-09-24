"""
87번에서 rotate_with_pelvis를 True로 바꿔도 Hips 본 트랙 자체의 회전은 여전히
0.0도로 얼어있었다. 이게 버그가 아니라 '루트모션이 Hips 트랙에서 추출되어
별도 트랙으로 빠지는' 정상 동작일 가능성을 확인한다 (그렇다면 Persona 뷰포트에서는
루트모션이 합산되어 정상적으로 보일 수 있음).
"""
import unreal
import json

REPORT = {}

for path in [
    "/Game/Source/SMPL_Source_Anim",
    "/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo_FK",
    "/Game/Retarget/Animations/SMPL_Source_Anim_OnMixamo_FK_PelvisFix",
]:
    anim = unreal.EditorAssetLibrary.load_asset(path)
    entry = {}
    for prop in ["enable_root_motion", "root_motion_root_lock", "force_root_lock"]:
        try:
            entry[prop] = str(anim.get_editor_property(prop))
        except Exception as e:
            entry[prop] = f"ERR: {e}"
    REPORT[path] = entry

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/88_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)

print(json.dumps(REPORT, ensure_ascii=False, indent=2, default=str))
