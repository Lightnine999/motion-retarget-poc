import bpy
import math

path = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_retargeted.fbx"
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

bones_to_check = [
    "mixamorig10:Neck", "mixamorig10:Head",
    "mixamorig10:LeftShoulder", "mixamorig10:RightShoulder",
    "mixamorig10:LeftArm", "mixamorig10:RightArm",
    "mixamorig10:LeftForeArm", "mixamorig10:RightForeArm",
]

history = {b: [] for b in bones_to_check}
for f in range(1, frame_end + 1):
    scene.frame_set(f)
    for b in bones_to_check:
        pb = armature.pose.bones.get(b)
        q = pb.matrix.to_quaternion()
        history[b].append(q.copy())

for b in bones_to_check:
    qs = history[b]
    deltas = []
    for i in range(len(qs) - 1):
        ang = math.degrees(qs[i].rotation_difference(qs[i+1]).angle)
        deltas.append(ang)
    top = sorted(range(len(deltas)), key=lambda i: -deltas[i])[:5]
    mean_d = sum(deltas) / len(deltas)
    max_d = max(deltas)
    print(f"{b:30s} mean={mean_d:6.2f} max={max_d:6.2f} top_frames={[(i+1, round(deltas[i],1)) for i in top]}")
