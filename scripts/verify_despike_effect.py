import bpy

for path, label in [
    ("/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_retargeted.fbx", "디스파이크 전"),
    ("/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_despiked4.fbx", "디스파이크 후"),
]:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=path)
    armature = bpy.data.objects.get("Armature")
    pb = armature.pose.bones["mixamorig10:Neck"]
    print(f"=== {label} ===")
    print("  rotation_mode:", pb.rotation_mode)
    action = armature.animation_data.action
    def iter_fcurves(action):
        legacy = getattr(action, "fcurves", None)
        if legacy is not None:
            yield from legacy
            return
        for layer in getattr(action, "layers", ()):
            for strip in getattr(layer, "strips", ()):
                for cb in getattr(strip, "channelbags", ()):
                    yield from cb.fcurves
    paths_seen = set()
    for fc in iter_fcurves(action):
        if "Neck" in fc.data_path:
            paths_seen.add(fc.data_path.split(".")[-1] if '"' not in fc.data_path.split(".")[-1] else fc.data_path)
    neck_paths = set(fc.data_path for fc in iter_fcurves(action) if "Neck" in fc.data_path)
    print("  Neck 관련 fcurve data_path 종류:", neck_paths)

    # Hips 높이(Z) 몇 프레임 확인
    hips = armature.pose.bones.get("mixamorig10:Hips")
    scene = bpy.context.scene
    for f in [1, 100, 200, 300]:
        scene.frame_set(f)
        world = armature.matrix_world @ hips.head
        print(f"  frame {f}: Hips world z = {world.z:.4f}")
