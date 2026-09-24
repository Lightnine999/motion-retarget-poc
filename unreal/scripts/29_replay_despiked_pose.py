import bpy
import math
import json
import os
import mathutils

FBX_PATH = "/Users/kwonkwanggoo/motion-retarget-poc/blender/assets/mixamo_character.fbx"
DUMP_PATH = "/Users/kwonkwanggoo/motion-retarget-poc/unreal/scripts/despiked_anim_dump_local.json"
OUT_DIR = "/Users/kwonkwanggoo/motion-retarget-poc/unreal/renders/frames_despiked_unreal"

os.makedirs(OUT_DIR, exist_ok=True)

with open(DUMP_PATH) as f:
    dump = json.load(f)

bone_order = dump["bone_order"]
frames = dump["frames"]
num_frames = dump["num_frames"]
root_bone = bone_order[0]

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=FBX_PATH)

armature = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj

assert armature is not None, "임포트한 FBX에서 아마추어를 찾지 못함"

pose_bones = armature.pose.bones
PREFIX = "mixamorig10:"


def resolve(name):
    if name in pose_bones:
        return name
    prefixed = PREFIX + name
    if prefixed in pose_bones:
        return prefixed
    return None


name_map = {b: resolve(b) for b in bone_order}
missing = [b for b, r in name_map.items() if r is None]
print("missing bones in blender armature:", missing)

for b, r in name_map.items():
    if r:
        pose_bones[r].rotation_mode = "QUATERNION"

bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = num_frames

for i, frame_data in enumerate(frames):
    f = i + 1
    for bone_name in bone_order:
        r = name_map.get(bone_name)
        if not r:
            continue
        pb = pose_bones[r]
        qd = frame_data[bone_name]["q"]  # [x,y,z,w] (Unreal 컨벤션)
        # Blender Quaternion 생성자는 (w,x,y,z) 순서
        pb.rotation_quaternion = mathutils.Quaternion((qd[3], qd[0], qd[1], qd[2]))
        pb.keyframe_insert(data_path="rotation_quaternion", frame=f)
        if bone_name == root_bone:
            pd = frame_data[bone_name]["p"]
            pb.location = mathutils.Vector(pd)
            pb.keyframe_insert(data_path="location", frame=f)

# 카메라
cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = (0.0, -3.5, 1.0)
cam.rotation_euler = (math.radians(90), 0, 0)
bpy.context.scene.camera = cam

# 라이트
light_data = bpy.data.lights.new("Sun", type="SUN")
light_data.energy = 3.0
light = bpy.data.objects.new("Sun", light_data)
bpy.context.scene.collection.objects.link(light)
light.rotation_euler = (math.radians(45), 0, math.radians(45))

bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 640
scene.render.resolution_y = 480
scene.render.film_transparent = False

print(f"rendering {num_frames} frames to {OUT_DIR}")
for f in range(1, num_frames + 1):
    scene.frame_set(f)
    scene.render.filepath = f"{OUT_DIR}/frame_{f:04d}.png"
    bpy.ops.render.render(write_still=True)

print("done")
