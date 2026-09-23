import bpy, math

path = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_despiked2.fbx"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=path)
armature = bpy.data.objects.get("Armature")
action = armature.animation_data.action
frame_start, frame_end = int(action.frame_range[0]), int(action.frame_range[1])
scene = bpy.context.scene

for b in ["mixamorig10:Spine", "mixamorig10:Spine1", "mixamorig10:Spine2", "mixamorig10:Hips"]:
    qs = []
    for f in range(frame_start, frame_end + 1):
        scene.frame_set(f)
        pb = armature.pose.bones[b]
        q = pb.rotation_quaternion.copy()
        if qs and q.dot(qs[-1]) < 0:
            q = -q
        qs.append(q)
    d = [math.degrees(qs[i].rotation_difference(qs[i+1]).angle) for i in range(len(qs)-1)]
    top = sorted(range(len(d)), key=lambda i: -d[i])[:8]
    print(f"{b:20s} max={max(d):6.1f} mean={sum(d)/len(d):5.2f} top_frames={[(i+frame_start, round(d[i],1)) for i in top]}")
