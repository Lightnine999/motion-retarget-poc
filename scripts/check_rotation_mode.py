import bpy

path = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_retargeted.fbx"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=path)

armature = bpy.data.objects.get("Armature")
action = armature.animation_data.action

for b in ["mixamorig10:Neck", "mixamorig10:RightForeArm", "mixamorig10:RightArm", "mixamorig10:LeftForeArm"]:
    pb = armature.pose.bones[b]
    print(b, "rotation_mode:", pb.rotation_mode)

print("--- fcurve data_paths (Neck 관련) ---")
def iter_fcurves(action):
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        yield from legacy
        return
    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            for cb in getattr(strip, "channelbags", ()):
                yield from cb.fcurves

for fc in iter_fcurves(action):
    if "Neck" in fc.data_path or "RightForeArm" in fc.data_path:
        print(fc.data_path, fc.array_index, "keys:", len(fc.keyframe_points))
