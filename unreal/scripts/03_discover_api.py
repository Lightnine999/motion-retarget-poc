import unreal
import json

REPORT = {}

# unreal 모듈에서 스켈레톤/본 관련 이름 검색
names = [n for n in dir(unreal) if "Skelet" in n or "Bone" in n or "IKRig" in n or "Retarget" in n]
REPORT["unreal_module_matches"] = sorted(names)

mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source.SMPL_Source")
skeleton = mesh.get_editor_property("skeleton")
bone_tree = skeleton.get_editor_property("bone_tree")
node = bone_tree[0]

# BoneNode 구조체의 dir() 목록
node_attrs = [a for a in dir(node) if not a.startswith("_")]
REPORT["bone_node_dir"] = node_attrs

# get_editor_property로 시도해볼 후보 프로퍼티명들
candidates = ["name", "bone_name", "Name", "parent_name", "translation_retargeting_mode",
              "TranslationRetargetingMode"]
tried = {}
for c in candidates:
    try:
        v = node.get_editor_property(c)
        tried[c] = str(v)
    except Exception as e:
        tried[c] = f"ERROR: {e}"
REPORT["bone_node_property_probe"] = tried

# static_struct 필드 나열 시도
try:
    ss = unreal.BoneNode.static_struct()
    REPORT["bone_node_static_struct_props"] = [p.get_name() for p in ss.properties()]
except Exception as e:
    REPORT["bone_node_static_struct_error"] = str(e)

# skeleton 객체 자체의 유용한 메서드들
skel_methods = [a for a in dir(skeleton) if not a.startswith("_") and ("bone" in a.lower() or "name" in a.lower())]
REPORT["skeleton_dir_bone_name_methods"] = skel_methods

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/03_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2)
