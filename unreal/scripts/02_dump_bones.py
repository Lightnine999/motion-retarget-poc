import unreal
import json

REPORT = {}


def dump_skeleton(mesh_path, key):
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
    skeleton = mesh.get_editor_property("skeleton")
    bone_tree = skeleton.get_editor_property("bone_tree")
    ref_skeleton_names = None
    try:
        ref_skeleton_names = [str(n) for n in unreal.SkeletalMeshLibrary.get_bone_names(mesh, False)]
    except Exception as e:
        REPORT[f"{key}_get_bone_names_error"] = str(e)

    bones = []
    for i, node in enumerate(bone_tree):
        entry = {"index": i}
        for prop in ["name", "parent_name", "translation_retargeting_mode"]:
            try:
                v = node.get_editor_property(prop)
                entry[prop] = str(v)
            except Exception:
                pass
        bones.append(entry)

    REPORT[f"{key}_bone_tree"] = bones
    REPORT[f"{key}_ref_skeleton_names"] = ref_skeleton_names
    REPORT[f"{key}_bone_count"] = len(bones)


try:
    dump_skeleton("/Game/Source/SMPL_Source.SMPL_Source", "source")
    dump_skeleton("/Game/Target/Mixamo_Character.Mixamo_Character", "target")
    REPORT["status"] = "ok"
except Exception as e:
    import traceback
    REPORT["status"] = "error"
    REPORT["error"] = str(e)
    REPORT["traceback"] = traceback.format_exc()

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/02_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2)
