import bpy
import json

FBX_PATH = "/Users/kwonkwanggoo/motion-retarget-poc/blender/assets/mixamo_character.fbx"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=FBX_PATH)

armature = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj

names = [b.name for b in armature.pose.bones]
with open("/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/30_blender_bones.json", "w") as f:
    json.dump(names, f, indent=2)
print("bone count:", len(names))
print(names[:10])
