import bpy, math
path = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_retargeted.fbx"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=path)
armature = bpy.data.objects.get("Armature")
action = armature.animation_data.action
frame_start, frame_end = int(action.frame_range[0]), int(action.frame_range[1])
scene = bpy.context.scene
for b in ["mixamorig10:LeftHand", "mixamorig10:RightHand", "mixamorig10:Head", "mixamorig10:Neck", "mixamorig10:LeftShoulder", "mixamorig10:RightShoulder"]:
    qs = []
    for f in range(frame_start, frame_end + 1):
        scene.frame_set(f)
        pb = armature.pose.bones[b]
        q = pb.rotation_quaternion.copy()
        if qs and q.dot(qs[-1]) < 0:
            q = -q
        qs.append(q)
    d = [math.degrees(qs[i].rotation_difference(qs[i+1]).angle) for i in range(len(qs)-1)]
    d_sorted = sorted(d)
    p50 = d_sorted[len(d)//2]
    p90 = d_sorted[int(len(d)*0.9)]
    print(f"{b:22s} max={max(d):6.1f} mean={sum(d)/len(d):5.2f} p50={p50:5.2f} p90={p90:5.2f}")
