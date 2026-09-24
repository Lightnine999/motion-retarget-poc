import bpy, math, os

path = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_character_fk_retarget.fbx"
out_dir = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/frames_fk_retarget"

os.makedirs(out_dir, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=path)

armature = None
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj

mesh_objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]

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

action = armature.animation_data.action
frame_end = int(action.frame_range[1])
scene.frame_end = frame_end

# 전체 시퀀스 바운딩박스를 샘플링해서 카메라가 항상 전신을 담도록 자동으로 맞춘다
depsgraph = bpy.context.evaluated_depsgraph_get()


def world_bbox(frame):
    scene.frame_set(frame)
    depsgraph.update()
    xs, ys, zs = [], [], []
    for mesh_obj in mesh_objs:
        ev = mesh_obj.evaluated_get(depsgraph)
        mat = ev.matrix_world
        for v in ev.data.vertices:
            c = mat @ v.co
            xs.append(c.x); ys.append(c.y); zs.append(c.z)
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


sample_frames = list(range(1, frame_end + 1, max(1, frame_end // 40)))
all_x, all_y, all_z = [], [], []
for f in sample_frames:
    (x0, x1), (y0, y1), (z0, z1) = world_bbox(f)
    all_x += [x0, x1]; all_y += [y0, y1]; all_z += [z0, z1]
cx = (min(all_x) + max(all_x)) / 2
cz = (min(all_z) + max(all_z)) / 2
span = max(max(all_x) - min(all_x), max(all_y) - min(all_y), max(all_z) - min(all_z))
print(f"auto camera fit: cx={cx:.2f} cz={cz:.2f} span={span:.2f}")

cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
dist = span * 2.2 + 2.0
cam.location = (cx, min(all_y) - dist, cz)
cam.rotation_euler = (math.radians(90), 0, 0)
cam_data.type = "ORTHO"
cam_data.ortho_scale = span * 1.5 + 0.5
bpy.context.scene.camera = cam

print("rendering frames_fk_retarget 1..", frame_end)
for f in range(1, frame_end + 1):
    scene.frame_set(f)
    scene.render.filepath = f"{out_dir}/frame_{f:04d}.png"
    bpy.ops.render.render(write_still=True)
print("done")
