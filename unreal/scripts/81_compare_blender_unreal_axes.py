"""
사용자 가설(블렌더-언리얼 글로벌 축 불일치)을 추측이 아니라 증거로 확인한다.
이미 확보해둔 블렌더 레스트포즈(armature.data.bones[*].head_local, 미터 단위,
Blender Z-up 좌표계) 값과, 언리얼에 임포트된 SMPL_Source 스켈레톤의 레스트포즈
본 위치(센티미터 단위, 언리얼 좌표계)를 같은 본들에 대해 나란히 출력해서
축 매핑(순서/부호)이 일관된 배율의 순열인지, 아니면 뒤틀려 있는지 판정한다.
"""
import unreal
import json

REPORT = {}

skeleton = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_Skeleton")
mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source")
ikrig = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_IKRig")

BONES = ["Pelvis", "L_Hip", "R_Hip", "Spine1", "Neck", "Head", "L_Shoulder", "R_Shoulder", "L_Wrist", "R_Wrist"]

# 언리얼 IKRig 컨트롤러의 레퍼런스 포즈 API 사용 (컴포넌트 스페이스, 절대 위치가 보장됨 - 70번 스크립트에서 검증된 API)
ikrig_controller = unreal.IKRigController.get_controller(ikrig)

result = {}
for b in BONES:
    try:
        t = ikrig_controller.get_ref_pose_transform_of_bone(b)
        result[b] = {
            "loc_cm": [round(t.translation.x, 2), round(t.translation.y, 2), round(t.translation.z, 2)],
        }
    except Exception as e:
        result[b] = {"error": str(e)}

REPORT["unreal_refpose_component_space_cm"] = result

# 참고용: 이번 세션에서 Blender preview_rest_pose.py로 이미 확보한 값 (미터, Blender armature 공간)
REPORT["blender_refpose_meters_for_comparison"] = {
    "Pelvis": [-0.002, -0.032, -0.226],
    "L_Hip": [0.07, -0.028, -0.319],
    "R_Hip": [-0.072, -0.03, -0.318],
    "Spine1": [-0.004, -0.001, -0.113],
    "Neck": [-0.0, 0.015, 0.297],
    "Head": [0.006, -0.037, 0.361],
    "L_Shoulder": [0.182, 0.017, 0.234],
    "R_Shoulder": [-0.185, 0.021, 0.234],
    "L_Wrist": [0.716, 0.047, 0.23],
    "R_Wrist": [-0.719, 0.05, 0.227],
}

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/81_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)

print(json.dumps(REPORT, ensure_ascii=False, indent=2, default=str))
