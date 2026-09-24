import unreal
import json

REPORT = {}
subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)


def find_root(mesh, known_bone):
    b = known_bone
    for _ in range(50):
        parent = subsystem.get_bone_parent(mesh, b)
        parent_str = str(parent)
        if parent_str in ("None", ""):
            return b
        b = parent_str
    return b


def walk_tree(mesh, root):
    flat = []

    def recurse(bone, parent):
        flat.append({"name": str(bone), "parent": str(parent) if parent else None})
        children = subsystem.get_bone_children(mesh, bone, False) if False else subsystem.get_bone_children(mesh, bone)
        for c in children:
            recurse(str(c), bone)

    recurse(root, None)
    return flat


source_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source.SMPL_Source")
target_mesh = unreal.EditorAssetLibrary.load_asset("/Game/Target/Mixamo_Character.Mixamo_Character")

source_root = find_root(source_mesh, "Spine1")
target_root = find_root(target_mesh, "Hips")

REPORT["source_root"] = source_root
REPORT["target_root"] = target_root
REPORT["source_tree"] = walk_tree(source_mesh, source_root)
REPORT["target_tree"] = walk_tree(target_mesh, target_root)
REPORT["source_bone_count"] = len(REPORT["source_tree"])
REPORT["target_bone_count"] = len(REPORT["target_tree"])

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/06_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
