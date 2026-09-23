import bpy, math, sys

path = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_rokoko_retargeted.fbx"
out_dir = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/frames_rokoko"

import os
os.makedirs(out_dir, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=path)

armature = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj

# 카메라: 캐릭터 정면에서 살짝 위, 전신이 보이도록
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

# 바닥 그리드(참고용 평면)
bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 640
scene.render.resolution_y = 480
scene.render.film_transparent = False

action = armature.animation_data.action
frame_end = int(action.frame_range[1])
scene.frame_end = frame_end
print("rendering frames_rokoko 1..", frame_end)
for f in range(1, frame_end + 1):
    scene.frame_set(f)
    scene.render.filepath = f"{out_dir}/frame_{f:04d}.png"
    bpy.ops.render.render(write_still=True)
print("done")
