"""
오늘 검증 완료한 순수 FK(스무딩 없음) SMPL 모션(smpl_params_fk_zup.npz, Z-up 미터)을
blender/assets/mixamo_character.fbx 의 믹사모 스켈레톤에 직접 얹는다.

SMPL 22관절과 믹사모 22개 대응 본이 부모-자식 구조까지 1:1로 정확히 일치한다는 걸
먼저 확인했으므로(Pelvis-Hips, L_Hip-LeftUpLeg, ... 등), 오늘 SMPL 아마추어에 썼던
바로 그 방식(global_rotation @ rest_basis, FK 위치 전파, 그리고 결정적으로
view_layer.update() 픽스)을 믹사모 본 이름으로 그대로 재적용한다.

믹사모 캐릭터 FBX는 Y-up, 센티미터 단위로 임포트되므로(SMPL 원본과 동일한 컨벤션),
오늘 썼던 것과 동일한 Y-up -> Z-up 변환(Rconv)을 레스트 데이터에 적용해서
우리가 이미 갖고 있는 Z-up 모션 데이터와 좌표계를 맞춘다.
"""
import bpy
import mathutils
import numpy as np
import math
import os

FK_PATH = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/smpl_params_fk.npz"
CHAR_FBX = "/Users/kwonkwanggoo/motion-retarget-poc/blender/assets/mixamo_character.fbx"
OUT_FBX = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_character_fk_retarget.fbx"
SHOT_DIR = "/Users/kwonkwanggoo/motion-retarget-poc/outputs/kaggle_tennis/mixamo_fk_preview"

PREFIX = "mixamorig10:"

# SMPL22_NAMES 순서와 1:1 대응하는 믹사모 본 이름 (부모-자식 구조까지 확인 완료)
MIXAMO_NAMES = [
    "Hips", "LeftUpLeg", "RightUpLeg", "Spine", "LeftLeg", "RightLeg", "Spine1",
    "LeftFoot", "RightFoot", "Spine2", "LeftToeBase", "RightToeBase", "Neck",
    "LeftShoulder", "RightShoulder", "Head", "LeftArm", "RightArm",
    "LeftForeArm", "RightForeArm", "LeftHand", "RightHand",
]
PARENTS = [-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19]

npz = np.load(FK_PATH)
global_mat = npz["global_mat"]  # [T,22,3,3], Z-up
transl = npz["transl"]          # [T,3], Z-up meters
num_frames = global_mat.shape[0]
print(f"frames: {num_frames}")

# pose_bone.matrix는 "월드 공간"이 아니라 "아마추어 오브젝트 로컬 공간"이다.
# 믹사모 아마추어 오브젝트 자체에 90도 회전 + 0.01 스케일 보정이 걸려있어서(FBX 임포트가
# Y-up/cm 원본을 Z-up/m으로 보이게 만드는 보정), 본 데이터(head_local/matrix_local)는
# 여전히 원본 그대로 Y-up/cm 공간에 있다. 그러니 우리 모션 데이터도 변환하지 말고
# SMPL 원본 그대로의 Y-up/미터 값을 그대로 쓰고, 위치만 cm로 스케일(*100)하면 된다.
M_TO_CM = 100.0


def np_to_matrix(m3):
    return mathutils.Matrix(m3.tolist())


os.makedirs(SHOT_DIR, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=CHAR_FBX)

armature = None
mesh_objs = []
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE":
        armature = obj
    elif obj.type == "MESH":
        mesh_objs.append(obj)
assert armature is not None
print("mesh objects:", [m.name for m in mesh_objs])

armature.animation_data_clear()
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = num_frames
scene.render.fps = 30

pose_bones = armature.pose.bones
for pb in pose_bones:
    pb.rotation_mode = "QUATERNION"

full_names = [PREFIX + n for n in MIXAMO_NAMES]
missing = [n for n in full_names if n not in pose_bones]
print("missing bones:", missing)

rest_basis = {}
rest_head = {}
for name in full_names:
    b = armature.data.bones[name]
    # 아마추어 로컬 공간(원본 Y-up, cm) 그대로 사용 - 변환 없음
    rest_basis[name] = b.matrix_local.to_3x3()
    rest_head[name] = b.head_local.copy()

hips_rest_head = rest_head[full_names[0]]

for index in range(num_frames):
    frame = index + 1
    scene.frame_set(frame)

    pos = {}
    pos[full_names[0]] = hips_rest_head + mathutils.Vector(tuple(transl[index])) * M_TO_CM
    for j, name in enumerate(full_names):
        if j == 0:
            continue
        parent_idx = PARENTS[j]
        parent_name = full_names[parent_idx]
        offset = rest_head[name] - rest_head[parent_name]
        parent_global_rot = np_to_matrix(global_mat[index, parent_idx])
        pos[name] = pos[parent_name] + parent_global_rot @ offset

    for j, name in enumerate(full_names):
        if name not in pose_bones:
            continue
        pb = pose_bones[name]
        rotation = np_to_matrix(global_mat[index, j]) @ rest_basis[name]
        m = rotation.to_4x4()
        m.translation = pos[name]
        pb.matrix = m
        bpy.context.view_layer.update()
        pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        pb.keyframe_insert(data_path="location", frame=frame)

scene.frame_set(1)

if armature.animation_data and armature.animation_data.action:
    action = armature.animation_data.action
    legacy = getattr(action, "fcurves", None)
    if legacy is not None:
        curves = legacy
    else:
        curves = []
        for layer in getattr(action, "layers", ()):
            for strip in getattr(layer, "strips", ()):
                for channelbag in getattr(strip, "channelbags", ()):
                    curves.extend(channelbag.fcurves)
    for curve in curves:
        for kp in curve.keyframe_points:
            kp.interpolation = "LINEAR"

# --- 육안 검증용 뷰포트 스크린샷 ---
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
            xs.append(c.x)
            ys.append(c.y)
            zs.append(c.z)
    return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))


preview_frames = sorted(set([1, num_frames // 6, num_frames // 3, num_frames // 2,
                              2 * num_frames // 3, 5 * num_frames // 6, num_frames]))
print("preview frames:", preview_frames)

all_x, all_y, all_z = [], [], []
for f in preview_frames:
    (x0, x1), (y0, y1), (z0, z1) = world_bbox(f)
    all_x += [x0, x1]
    all_y += [y0, y1]
    all_z += [z0, z1]
cx = (min(all_x) + max(all_x)) / 2
cy = (min(all_y) + max(all_y)) / 2
cz = (min(all_z) + max(all_z)) / 2
span = max(max(all_x) - min(all_x), max(all_y) - min(all_y), max(all_z) - min(all_z))
scale = span * 1.4 + 0.5
print(f"bbox center=({cx:.2f},{cy:.2f},{cz:.2f}) span={span:.2f} ortho_scale={scale:.2f}")

dist = span * 3 + 3
bpy.ops.object.camera_add(location=(cx, cy - dist, cz), rotation=(math.radians(90), 0, 0))
cam_front = bpy.context.object
cam_front.name = "Cam_Front"
cam_front.data.type = "ORTHO"
cam_front.data.ortho_scale = scale

bpy.ops.object.camera_add(location=(cx + dist, cy, cz), rotation=(math.radians(90), 0, math.radians(90)))
cam_side = bpy.context.object
cam_side.name = "Cam_Side"
cam_side.data.type = "ORTHO"
cam_side.data.ortho_scale = scale

scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 480
scene.render.resolution_y = 640
scene.display_settings.display_device = "sRGB"
scene.render.image_settings.file_format = "PNG"

for cam, tag in [(cam_front, "front"), (cam_side, "side")]:
    scene.camera = cam
    for f in preview_frames:
        scene.frame_set(f)
        scene.render.filepath = os.path.join(SHOT_DIR, f"{tag}_frame{f:04d}.png")
        bpy.ops.render.render(write_still=True)

print("preview screenshots saved to:", SHOT_DIR)

bpy.data.objects.remove(cam_front, do_unlink=True)
bpy.data.objects.remove(cam_side, do_unlink=True)

bpy.ops.object.select_all(action="DESELECT")
armature.select_set(True)
for m in mesh_objs:
    m.select_set(True)

bpy.ops.export_scene.fbx(
    filepath=OUT_FBX,
    use_selection=True,
    bake_anim=True,
    bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False,
    bake_anim_use_all_actions=False,
    bake_anim_force_startend_keying=True,
    bake_anim_simplify_factor=0.0,
    add_leaf_bones=False,
)
print("exported:", OUT_FBX)
