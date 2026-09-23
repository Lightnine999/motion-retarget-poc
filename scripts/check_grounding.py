import bpy, sys

path = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_retargeted.fbx"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=path)

armature = None
meshes = []
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj
    elif obj.type == "MESH":
        meshes.append(obj)

scene = bpy.context.scene
frames_to_check = [1, scene.frame_end // 2, scene.frame_end]
print("frame_start/end:", scene.frame_start, scene.frame_end)
print("armature:", armature.name if armature else None, "meshes:", [m.name for m in meshes])

hips = armature.pose.bones.get("mixamorig10:Hips")
for f in frames_to_check:
    scene.frame_set(f)
    bpy.context.view_layer.update()
    hips_world = armature.matrix_world @ hips.head
    min_z = None
    for m in meshes:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = m.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()
        for v in mesh.vertices:
            wz = (eval_obj.matrix_world @ v.co).z
            if min_z is None or wz < min_z:
                min_z = wz
        eval_obj.to_mesh_clear()
    print(f"frame={f} hips_world_z={hips_world.z:.4f} lowest_vertex_z={min_z:.4f}")
