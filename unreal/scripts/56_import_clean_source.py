import unreal
import json
import traceback

REPORT = {}


def safe(label, fn):
    try:
        return fn()
    except Exception as e:
        REPORT[f"error_{label}"] = str(e)
        REPORT[f"traceback_{label}"] = traceback.format_exc()
        return None


existing_skeleton = unreal.EditorAssetLibrary.load_asset("/Game/Source/SMPL_Source_Skeleton")
REPORT["existing_skeleton_is_none"] = existing_skeleton is None


def import_anim_only(filename, dest_path, dest_name, skeleton):
    task = unreal.AssetImportTask()
    task.filename = filename
    task.destination_path = dest_path
    task.destination_name = dest_name
    task.automated = True
    task.save = True
    task.replace_existing = True

    options = unreal.FbxImportUI()
    options.import_mesh = False
    options.import_as_skeletal = True
    options.import_animations = True
    options.create_physics_asset = False
    options.skeleton = skeleton

    anim_data = unreal.FbxAnimSequenceImportData()
    try:
        anim_data.import_bone_tracks = True
    except AttributeError:
        pass
    options.anim_sequence_import_data = anim_data

    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return list(task.imported_object_paths)


paths = safe("import", lambda: import_anim_only(
    "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_clean_unreal_despiked.fbx",
    "/Game/SourceClean",
    "SMPL_Clean_Anim",
    existing_skeleton,
))
REPORT["imported_paths"] = paths

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/56_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
