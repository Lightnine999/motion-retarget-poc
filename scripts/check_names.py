import bpy
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath="/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_retargeted.fbx")
for obj in bpy.context.scene.objects:
    print(obj.name, obj.type)
    if obj.type == "ARMATURE":
        names = [b.name for b in obj.data.bones]
        print("  bones:", names)
