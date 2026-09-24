import unreal
import json

REPORT = {"steps": []}


def log(msg):
    REPORT["steps"].append(msg)
    unreal.log(msg)


def import_fbx(filename, dest_path, dest_name, import_anim, existing_skeleton=None):
    task = unreal.AssetImportTask()
    task.filename = filename
    task.destination_path = dest_path
    task.destination_name = dest_name
    task.automated = True
    task.save = True
    task.replace_existing = True

    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = True
    options.import_animations = import_anim
    options.create_physics_asset = False
    if existing_skeleton is not None:
        options.skeleton = existing_skeleton

    def try_set(obj, prop, value):
        try:
            setattr(obj, prop, value)
        except AttributeError:
            pass

    skel_data = unreal.FbxSkeletalMeshImportData()
    try_set(skel_data, "update_skeleton_reference_pose", False)
    try_set(skel_data, "use_t0_as_ref_pose", False)
    options.skeletal_mesh_import_data = skel_data

    if import_anim:
        anim_data = unreal.FbxAnimSequenceImportData()
        try_set(anim_data, "import_bone_tracks", True)
        try_set(anim_data, "remove_redundant_keys", False)
        options.anim_sequence_import_data = anim_data

    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return list(task.imported_object_paths)


def get_bone_names(skeletal_mesh_or_skeleton):
    candidates = [
        lambda o: unreal.SkeletalMeshLibrary.get_bone_names(o, False),
        lambda o: unreal.SkeletalMeshLibrary.get_bone_names(o),
        lambda o: o.get_editor_property("skeleton").get_editor_property("bone_tree"),
    ]
    for fn in candidates:
        try:
            result = fn(skeletal_mesh_or_skeleton)
            return [str(n) for n in result]
        except Exception as e:
            last_err = str(e)
    return {"error": last_err}


import traceback


def safe(label, fn):
    try:
        fn()
    except Exception as e:
        REPORT[f"error_{label}"] = str(e)
        REPORT[f"traceback_{label}"] = traceback.format_exc()
        log(f"ERROR in {label}: {e}")


source_paths = []
target_paths = []


def do_import_source():
    global source_paths
    log("=== SMPL 소스 임포트 ===")
    source_paths = import_fbx(
        "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_clean.fbx",
        "/Game/Source",
        "SMPL_Source",
        import_anim=True,
    )
    log(f"source imported: {source_paths}")
    REPORT["source_imported_paths"] = source_paths


def do_import_target():
    global target_paths
    log("=== Mixamo 타겟 임포트 ===")
    target_paths = import_fbx(
        "/Users/kwonkwanggoo/motion-retarget-poc/blender/assets/mixamo_character.fbx",
        "/Game/Target",
        "Mixamo_Character",
        import_anim=False,
    )
    log(f"target imported: {target_paths}")
    REPORT["target_imported_paths"] = target_paths


def do_inspect_source():
    for p in source_paths:
        obj = unreal.EditorAssetLibrary.load_asset(p)
        cls = obj.get_class().get_name()
        log(f"SOURCE asset {p} -> class={cls}")
        if cls == "SkeletalMesh":
            REPORT["source_skeletal_mesh_path"] = p
            REPORT["source_bone_names"] = get_bone_names(obj)
        elif cls == "AnimSequence":
            REPORT["source_anim_sequence_path"] = p


def do_inspect_target():
    for p in target_paths:
        obj = unreal.EditorAssetLibrary.load_asset(p)
        cls = obj.get_class().get_name()
        log(f"TARGET asset {p} -> class={cls}")
        if cls == "SkeletalMesh":
            REPORT["target_skeletal_mesh_path"] = p
            REPORT["target_bone_names"] = get_bone_names(obj)


safe("import_source", do_import_source)
safe("import_target", do_import_target)
safe("inspect_source", do_inspect_source)
safe("inspect_target", do_inspect_target)
REPORT["status"] = "done"

with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/01_report.json", "w") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2)

log("=== 리포트 저장 완료 ===")
