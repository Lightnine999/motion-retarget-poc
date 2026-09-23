import bpy

path = "/Users/kwonkwanggoo/motion-retarget-poc/blender/assets/mixamo_character.fbx"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=path)

armature = None
meshes = []
for obj in bpy.context.scene.objects:
    print("obj:", obj.name, obj.type, "loc:", tuple(obj.location), "scale:", tuple(obj.scale))
    if obj.type == "ARMATURE":
        armature = obj
    elif obj.type == "MESH":
        meshes.append(obj)

hips = armature.data.bones.get("mixamorig10:Hips")
print("armature world matrix:\n", armature.matrix_world)
print("Hips head_local:", tuple(hips.head_local), "tail_local:", tuple(hips.tail_local))

min_z = None
max_z = None
for m in meshes:
    for v in m.data.vertices:
        wz = (m.matrix_world @ v.co).z
        if min_z is None or wz < min_z:
            min_z = wz
        if max_z is None or wz > max_z:
            max_z = wz
print("REST POSE mesh min_z (feet):", min_z, "max_z (head/hair top):", max_z, "height:", max_z - min_z)
