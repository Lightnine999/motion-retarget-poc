"""
82/83에서 발견: 리타겟된 Mixamo 애니메이션에서 Hips 본의 프레임간 회전 변화가
정확히 0.0도 (완전히 고정)인데, Spine/Spine1/Spine2/Neck은 정상적으로 회전한다.
즉 골반(Hips)만 회전을 안 받고 그 위 척추는 회전하니 "허리가 뒤틀려 보이는" 것.
이게 블렌더-언리얼 축 문제가 아니라 IK Retargeter의 펠비스/루트 처리 설정 문제라는
가설을 검증하기 위해 현재 리타겟터의 체인/루트 설정을 들여다본다.
"""
import unreal
import json

REPORT = {}

retargeter = unreal.EditorAssetLibrary.load_asset("/Game/Retarget/SMPL_to_Mixamo_Retargeter")
controller = unreal.IKRetargeterController.get_controller(retargeter)

# 체인 매핑
chain_settings = controller.get_all_chain_settings()
REPORT["chain_mappings"] = [
    {"target_chain": str(cs.target_chain), "source_chain": str(cs.source_chain)}
    for cs in chain_settings
]

# 루트/펠비스 관련 API 탐색
REPORT["controller_root_related_methods"] = sorted([a for a in dir(controller) if "root" in a.lower() or "pelvis" in a.lower()])

for name in REPORT["controller_root_related_methods"]:
    fn = getattr(controller, name, None)
    if fn and callable(fn):
        REPORT[f"help_{name}"] = fn.__doc__

# 소스/타겟 IK Rig 에서 Root 본 지정 확인
source_ikrig = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_IKRig")
target_ikrig = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character_IKRig")
source_ikrig_ctrl = unreal.IKRigController.get_controller(source_ikrig)
target_ikrig_ctrl = unreal.IKRigController.get_controller(target_ikrig)

REPORT["ikrig_root_related_methods"] = sorted([a for a in dir(source_ikrig_ctrl) if "root" in a.lower()])
for name in REPORT["ikrig_root_related_methods"]:
    fn = getattr(source_ikrig_ctrl, name, None)
    if fn and callable(fn):
        try:
            REPORT[f"source_{name}_result"] = str(fn())
        except Exception as e:
            REPORT[f"source_{name}_result"] = f"ERR(no-arg call): {e}"
        try:
            REPORT[f"target_{name}_result"] = str(getattr(target_ikrig_ctrl, name)())
        except Exception as e:
            REPORT[f"target_{name}_result"] = f"ERR(no-arg call): {e}"

# Retargeter Ops 스택 확인 (있다면)
REPORT["controller_ops_related_methods"] = sorted([a for a in dir(controller) if "op" in a.lower()])

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/84_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)

print(json.dumps(REPORT, ensure_ascii=False, indent=2, default=str)[:4000])
