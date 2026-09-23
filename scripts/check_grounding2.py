import bpy

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
for f in [1, 125, 250]:
    scene.frame_set(f)
    bpy.context.view_layer.update()
    print(f"--- frame {f} ---")
    for bone_name in ["mixamorig10:Hips", "mixamorig10:LeftUpLeg", "mixamorig10:LeftLeg", "mixamorig10:LeftFoot", "mixamorig10:LeftToeBase"]:
        pb = armature.pose.bones.get(bone_name)
        world = armature.matrix_world @ pb.head
        print(f"  {bone_name}: head_world_z={world.z:.4f}")
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for m in meshes:
        eval_obj = m.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()
        min_z = min((eval_obj.matrix_world @ v.co).z for v in mesh.vertices)
        eval_obj.to_mesh_clear()
        print(f"  mesh {m.name}: min_z={min_z:.4f}")
