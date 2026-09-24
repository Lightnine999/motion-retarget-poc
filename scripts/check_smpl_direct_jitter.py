import bpy
import math

path = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_source_direct.fbx"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=path)

armature = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj

action = armature.animation_data.action
frame_end = int(action.frame_range[1])
scene = bpy.context.scene
print("frame_end:", frame_end)

bones_to_check = ["Neck", "Head", "L_Shoulder", "R_Shoulder", "L_Elbow", "R_Elbow"]
history = {b: [] for b in bones_to_check}
for f in range(1, frame_end + 1):
    scene.frame_set(f)
    for b in bones_to_check:
        pb = armature.pose.bones.get(b)
        q = pb.matrix.to_quaternion()
        history[b].append(q)

for b in bones_to_check:
    qs = history[b]
    deltas_raw = [math.degrees(qs[i].rotation_difference(qs[i+1]).angle) for i in range(len(qs)-1)]
    # 이중피복 보정
    fixed = [qs[0].copy()]
    for i in range(1, len(qs)):
        q = qs[i].copy()
        if q.dot(fixed[-1]) < 0:
            q = -q
        fixed.append(q)
    deltas_fixed = [math.degrees(fixed[i].rotation_difference(fixed[i+1]).angle) for i in range(len(fixed)-1)]
    top = sorted(range(len(deltas_fixed)), key=lambda i: -deltas_fixed[i])[:5]
    print(f"{b:12s} raw_max={max(deltas_raw):6.1f} fixed_max={max(deltas_fixed):6.1f} fixed_mean={sum(deltas_fixed)/len(deltas_fixed):5.2f} top={[(i+1, round(deltas_fixed[i],1)) for i in top]}")
